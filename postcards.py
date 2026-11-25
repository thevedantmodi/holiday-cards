#!/usr/bin/env python3
"""Generate printable photo holiday postcards from a CSV of friends.

Each friend gets two pages in the output PDF:
  1. the front: three of your photos, a signature and a greeting
  2. the back: a small photo, a short note, your return address,
     a stamp box and their address

Pages are 6 x 4 in (USPS postcard size), ordered front/back/front/back so the
PDF can be printed double-sided ("flip on short edge") on 4x6 card stock.

Usage:
    python3 postcards.py friends.csv
    python3 postcards.py friends.csv -o out/cards.pdf
"""

import argparse
import csv
import io
import sys
import tomllib
from pathlib import Path

from PIL import Image, ImageFilter, ImageOps
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas

HERE = Path(__file__).resolve().parent
W, H = 6 * inch, 4 * inch  # landscape postcard
DPI = 300                  # resolution photos are resampled to

INK = HexColor("#1c1c1c")
SOFT = HexColor("#6f6a62")
RULE = HexColor("#d9d3c7")
RED = HexColor("#9e1b2b")      # cranberry
GREEN = HexColor("#1f4a33")    # pine
LEAF = HexColor("#2e6b47")
PAPER = (247, 245, 240)

DEFAULT_CONFIG = {
    "signoff": "WITH LOVE,",
    "signature": "the Browns",
    "headline": "MERRY CHRISTMAS",
    "dateline": "DECEMBER 2026",
    "sender": "The Browns",
    "return_address": [],
    "note": "Wishing you a merry little Christmas, {first_name}!",
    "photos": {
        "main": "photos/main.jpg",
        "top": "photos/top.jpg",
        "bottom": "photos/bottom.jpg",
        "back": "photos/back.jpg",
    },
    "focus": {},
}

FONTS = {
    "serif": "CormorantGaramond-Light.ttf",
    "script": "HerrVonMuellerhoff-Regular.ttf",
    "sans": "Montserrat-Regular.ttf",
    "sans-medium": "Montserrat-Medium.ttf",
}


def register_fonts():
    for name, file in FONTS.items():
        pdfmetrics.registerFont(TTFont(name, str(HERE / "fonts" / file)))


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------

def load_config(path):
    cfg = {k: (dict(v) if isinstance(v, dict) else v) for k, v in DEFAULT_CONFIG.items()}
    if path and Path(path).exists():
        with open(path, "rb") as f:
            user = tomllib.load(f)
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k].update(v)
            else:
                cfg[k] = v
    return cfg


def load_friends(path):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = [
            {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
            for row in csv.DictReader(f)
        ]
    friends = [r for r in rows if r.get("name")]
    for r in friends:
        missing = [k for k in ("address1", "city", "state", "zip") if not r.get(k)]
        if missing:
            print(f"warning: {r['name']} is missing {', '.join(missing)}", file=sys.stderr)
    return friends


def address_lines(friend):
    lines = [friend["name"], friend.get("address1", ""), friend.get("address2", "")]
    state_zip = " ".join(p for p in (friend.get("state", ""), friend.get("zip", "")) if p)
    lines.append(", ".join(p for p in (friend.get("city", ""), state_zip) if p))
    country = friend.get("country", "")
    if country and country.upper() not in ("US", "USA", "UNITED STATES"):
        lines.append(country.upper())
    return [l for l in lines if l]


# --------------------------------------------------------------------------
# Images
# --------------------------------------------------------------------------

_photo_cache = {}


def photo(path, w, h, focus=(0.5, 0.5)):
    """Crop a photo to fill a w x h (points) box, like CSS object-fit: cover.

    focus is the point (0-1 from left, 0-1 from top) that should stay in view.
    Returns an ImageReader, or None if the file doesn't exist.
    """
    p = Path(path)
    if not p.is_absolute():
        p = HERE / p
    key = (str(p), round(w), round(h), tuple(focus))
    if key in _photo_cache:
        return _photo_cache[key]
    if not p.exists():
        _photo_cache[key] = None
        return None
    im = ImageOps.exif_transpose(Image.open(p)).convert("RGB")
    target = w / h
    iw, ih = im.size
    if iw / ih > target:            # too wide: trim the sides
        cw, ch = round(ih * target), ih
    else:                           # too tall: trim top/bottom
        cw, ch = iw, round(iw / target)
    fx, fy = focus
    left = min(max(round(fx * iw - cw / 2), 0), iw - cw)
    top = min(max(round(fy * ih - ch / 2), 0), ih - ch)
    im = im.crop((left, top, left + cw, top + ch))
    px = (round(w / 72 * DPI), round(h / 72 * DPI))
    if im.width > px[0]:
        im = im.resize(px, Image.LANCZOS)
    elif im.width < px[0] * 0.5:
        print(f"warning: {p.name} is low resolution and may print blurry", file=sys.stderr)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=92)
    buf.seek(0)
    _photo_cache[key] = ImageReader(buf)
    return _photo_cache[key]


_paper = None


def paper():
    """A subtle cotton-paper texture, generated once."""
    global _paper
    if _paper is None:
        size = (900, 600)
        noise = Image.effect_noise(size, 40).filter(ImageFilter.GaussianBlur(0.7))
        base = Image.new("RGB", size, PAPER)
        shade = Image.new("RGB", size, (226, 222, 214))
        mask = noise.point(lambda v: max(0, v - 120) // 2)
        tex = Image.composite(shade, base, mask)
        buf = io.BytesIO()
        tex.save(buf, "JPEG", quality=88)
        buf.seek(0)
        _paper = ImageReader(buf)
    return _paper


# --------------------------------------------------------------------------
# Drawing helpers
# --------------------------------------------------------------------------

def tracked(c, x, y, text, font, size, spacing, color=INK, align="left"):
    width = c.stringWidth(text, font, size) + spacing * (len(text) - 1)
    if align == "right":
        x -= width
    elif align == "center":
        x -= width / 2
    c.setFillColor(color)
    c.setFont(font, size)
    c.drawString(x, y, text, charSpace=spacing)
    return width


def fit_size(c, text, font, size, max_w, min_size=6):
    while c.stringWidth(text, font, size) > max_w and size > min_size:
        size -= 0.5
    return size


def holly_leaf(c, x, y, length, angle, color):
    """A spiky holly leaf starting at (x, y), pointing at `angle` degrees."""
    import math
    w = length * 0.32
    tips = [0, 0.22, 0.42, 0.62, 0.8, 1.0]
    c.saveState()
    c.translate(x, y)
    c.rotate(angle)
    p = c.beginPath()
    p.moveTo(0, 0)
    for side in (1, -1):
        pts = tips if side == 1 else tips[::-1]
        for a, b in zip(pts, pts[1:]):
            ya = side * w * math.sin(math.pi * b) ** 0.8
            mid = (a + b) / 2 * length
            ym = side * w * 0.55 * math.sin(math.pi * (a + b) / 2) ** 0.8
            p.curveTo(mid, ym, mid, ym, b * length, ya)
    p.close()
    c.setFillColor(color)
    c.drawPath(p, stroke=0, fill=1)
    c.setStrokeColor(HexColor("#ffffff"))
    c.setStrokeAlpha(0.35)
    c.setLineWidth(length * 0.02)
    c.line(length * 0.05, 0, length * 0.9, 0)
    c.restoreState()


def holly(c, x, y, size=1.0, angle=0):
    """A sprig of two holly leaves and three berries centred on (x, y)."""
    c.saveState()
    c.translate(x, y)
    c.rotate(angle)
    L = 26 * size
    holly_leaf(c, 0, 0, L, 160, GREEN)
    holly_leaf(c, 0, 0, L, 20, LEAF)
    for bx, by in [(-3.2, 2.2), (3.0, 2.6), (0, -2.4)]:
        bx, by = bx * size, by * size
        c.setFillColor(RED)
        c.circle(bx, by, 3.3 * size, stroke=0, fill=1)
        c.setFillColor(HexColor("#ffffff"))
        c.setFillAlpha(0.45)
        c.circle(bx - 1.0 * size, by + 1.1 * size, 0.9 * size, stroke=0, fill=1)
        c.setFillAlpha(1)
    c.restoreState()


def place_photo(c, cfg, slot, x, y, w, h):
    focus = cfg.get("focus", {}).get(slot, (0.5, 0.5))
    img = photo(cfg["photos"][slot], w, h, focus)
    if img:
        c.drawImage(img, x, y, w, h)
        return
    # placeholder so it's obvious where a photo goes
    c.setFillColor(HexColor("#e8e3d9"))
    c.rect(x, y, w, h, stroke=0, fill=1)
    tracked(c, x + w / 2, y + h / 2 + 2, "ADD PHOTO", "sans-medium", 6, 1.5, SOFT, "center")
    tracked(c, x + w / 2, y + h / 2 - 8, cfg["photos"][slot], "sans", 5.5, 0.3, SOFT, "center")


def background(c):
    c.drawImage(paper(), 0, 0, W, H)


# --------------------------------------------------------------------------
# Front
# --------------------------------------------------------------------------

def draw_front(c, cfg):
    background(c)

    # photo grid: one large photo, two stacked on the right
    gx, gy, gw, gh = 0.55 * inch, 0.74 * inch, 4.9 * inch, 2.48 * inch
    gap = 0.09 * inch
    big_w = (gw - gap) * 0.625
    small_w = gw - gap - big_w
    small_h = (gh - gap) / 2
    place_photo(c, cfg, "main", gx, gy, big_w, gh)
    place_photo(c, cfg, "top", gx + big_w + gap, gy + small_h + gap, small_w, small_h)
    place_photo(c, cfg, "bottom", gx + big_w + gap, gy, small_w, small_h)

    # "WITH LOVE," + script signature that dips over the photos
    top_y = gy + gh + 0.2 * inch
    sw = tracked(c, gx + 0.05 * inch, top_y, cfg["signoff"], "sans", 9, 3.2, GREEN)
    sig_x = gx + 0.05 * inch + sw + 6
    sig_size = fit_size(c, cfg["signature"], "script", 32, gx + gw - sig_x - 0.6 * inch)
    c.setFillColor(INK)
    c.setFont("script", sig_size)
    c.drawString(sig_x, top_y - 0.08 * inch, cfg["signature"])

    # headline + date under the photos
    base_y = 0.3 * inch
    date_w = c.stringWidth(cfg["dateline"], "sans", 8.5) + 2.6 * (len(cfg["dateline"]) - 1)
    tracked(c, gx + gw, base_y + 2, cfg["dateline"], "sans", 8.5, 2.6, GREEN, align="right")
    head_size = fit_size(c, cfg["headline"], "serif", 38, gw - date_w - 0.25 * inch)
    c.setFillColor(RED)
    c.setFont("serif", head_size)
    c.drawString(gx - 0.04 * inch, base_y, cfg["headline"])

    # holly sprig in the empty top-right corner
    holly(c, gx + gw - 0.22 * inch, top_y + 0.02 * inch, 0.95, -12)

    if cfg.get("border", True):
        border(c)


def border(c):
    """A classic double rule in red: a bold outer line and a fine inner one."""
    c.setStrokeColor(RED)
    c.setLineWidth(2.2)
    o = 0.11 * inch
    c.rect(o, o, W - 2 * o, H - 2 * o, stroke=1, fill=0)
    c.setLineWidth(0.5)
    i = 0.165 * inch
    c.rect(i, i, W - 2 * i, H - 2 * i, stroke=1, fill=0)


# --------------------------------------------------------------------------
# Back
# --------------------------------------------------------------------------

def draw_back(c, friend, cfg):
    background(c)
    m = 0.3 * inch
    divider_x = 3.0 * inch

    # return address, top-left (where USPS expects it)
    ret = [cfg["sender"], *cfg.get("return_address", [])]
    y = H - m - 5
    for i, line in enumerate(ret):
        tracked(c, m, y, line.upper(), "sans-medium" if i == 0 else "sans", 5.8, 0.9,
                RED if i == 0 else SOFT)
        y -= 8.5

    # small photo
    px, pw = m, divider_x - m - 0.25 * inch
    ptop = y - 0.08 * inch
    pbottom = 1.0 * inch
    place_photo(c, cfg, "back", px, pbottom, pw, ptop - pbottom)

    # short note under the photo
    first = friend["name"].split()[0]
    note = (friend.get("message") or cfg["note"]).replace("\\n", " ")
    note = note.format(first_name=first, name=friend["name"], sender=cfg["sender"])
    lines = simpleSplit(note, "serif", 12, pw)
    if len(lines) > 3:
        print(f"warning: note for {friend['name']} is too long and was cut off", file=sys.stderr)
        lines = lines[:3]
    c.setFillColor(INK)
    c.setFont("serif", 11)
    for i, line in enumerate(lines):
        c.drawString(px, pbottom - 0.22 * inch - i * 14, line)

    # divider
    c.setStrokeColor(RULE)
    c.setLineWidth(0.6)
    c.line(divider_x, 0.7 * inch, divider_x, H - 0.72 * inch)
    holly(c, divider_x, H - 0.48 * inch, 0.6, 0)

    # stamp box
    sw, sh = 0.8 * inch, 0.95 * inch
    sx, sy = W - m - sw, H - m - sh
    c.setStrokeColor(RED)
    c.setLineWidth(0.5)
    c.setDash(1.5, 2)
    c.rect(sx, sy, sw, sh, stroke=1, fill=0)
    c.setDash()
    tracked(c, sx + sw / 2, sy + sh / 2 - 2, "STAMP", "sans", 5.5, 1.5, RED, "center")

    # recipient address. The bottom 5/8" stays blank for the USPS barcode.
    ax, aw = divider_x + 0.3 * inch, W - m - (divider_x + 0.3 * inch)
    ay, leading = 1.95 * inch, 18
    for i, line in enumerate(address_lines(friend)):
        font = "sans-medium" if i == 0 else "sans"
        size = fit_size(c, line, font, 10.5, aw)
        c.setFillColor(GREEN if i == 0 else INK)
        c.setFont(font, size)
        c.drawString(ax, ay - i * leading, line)
        c.setStrokeColor(RULE)
        c.setLineWidth(0.4)
        c.line(ax, ay - i * leading - 5, W - m, ay - i * leading - 5)


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="CSV of friends (name,address1,address2,city,state,zip[,country,message])")
    ap.add_argument("-o", "--out", default="out/postcards.pdf", help="output PDF path")
    ap.add_argument("-c", "--config", default="config.toml", help="text, photo and return-address settings")
    args = ap.parse_args()

    register_fonts()
    config = Path(args.config)
    if not config.exists() and args.config == "config.toml":
        config = HERE / "config.example.toml"
        print("note: no config.toml found, using config.example.toml. Copy it to "
              "config.toml and add your details (config.toml is not committed).", file=sys.stderr)
    elif not config.exists():
        sys.exit(f"config file not found: {config}")
    cfg = load_config(config)
    friends = load_friends(args.csv)
    if not friends:
        sys.exit("no friends found in CSV (needs a 'name' column)")
    for slot, path in cfg["photos"].items():
        if not (HERE / path).exists() and not Path(path).exists():
            print(f"note: no photo at {path}, a placeholder will be used", file=sys.stderr)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    c = Canvas(str(out), pagesize=(W, H))
    c.setTitle(f"{cfg['headline'].title()} postcards")
    for friend in friends:
        draw_front(c, cfg)
        c.showPage()
        draw_back(c, friend, cfg)
        c.showPage()
    c.save()
    print(f"wrote {len(friends)} postcards ({2 * len(friends)} pages) to {out}")


if __name__ == "__main__":
    main()

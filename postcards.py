#!/usr/bin/env python3
"""Generate printable holiday postcards from a CSV of friends.

Each friend gets two pages in the output PDF:
  1. the front: a holiday illustration
  2. the back: a personal message on the left, their address on the right

Pages are 6 x 4 in (USPS postcard size), ordered front/back/front/back so the
PDF can be printed double-sided ("flip on short edge") on 4x6 card stock.

Usage:
    python3 postcards.py friends.csv
    python3 postcards.py friends.csv --theme snow -o out/cards.pdf
"""

import argparse
import csv
import math
import random
import sys
import tomllib
from pathlib import Path

from reportlab.lib.colors import HexColor, Color
from reportlab.lib.units import inch
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen.canvas import Canvas

W, H = 6 * inch, 4 * inch  # landscape postcard

THEMES = ["snow", "ornaments", "pines"]

DEFAULT_CONFIG = {
    "sender": "Your Name",
    "greeting": "Happy Holidays",
    "year": "2026",
    "return_address": [],
    "message": (
        "Dear {first_name},\n\n"
        "Wishing you a cozy season full of warmth, laughter and good food. "
        "Thanks for being such a great friend this year. Here's to an even "
        "better one ahead!\n\n"
        "With love,\n{sender}"
    ),
}

INK = HexColor("#2b2b2b")
SOFT_INK = HexColor("#6b6b6b")
RED = HexColor("#b3262e")
GREEN = HexColor("#1f5135")
GOLD = HexColor("#c9a227")
CREAM = HexColor("#f7f1e3")
NAVY = HexColor("#13223f")


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------

def load_config(path):
    cfg = dict(DEFAULT_CONFIG)
    if path and Path(path).exists():
        with open(path, "rb") as f:
            cfg.update(tomllib.load(f))
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
    city = friend.get("city", "")
    state_zip = " ".join(p for p in (friend.get("state", ""), friend.get("zip", "")) if p)
    lines.append(", ".join(p for p in (city, state_zip) if p))
    country = friend.get("country", "")
    if country and country.upper() not in ("US", "USA", "UNITED STATES"):
        lines.append(country.upper())
    return [l for l in lines if l]


# --------------------------------------------------------------------------
# Drawing helpers
# --------------------------------------------------------------------------

def snowflake(c, x, y, r, color, width=0.8):
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.setLineCap(1)
    for k in range(6):
        a = k * math.pi / 3
        dx, dy = math.cos(a), math.sin(a)
        c.line(x, y, x + dx * r, y + dy * r)
        for t in (0.45, 0.7):
            bx, by = x + dx * r * t, y + dy * r * t
            b = r * 0.28 * (1.1 - t)
            for s in (-1, 1):
                ba = a + s * math.pi / 4
                c.line(bx, by, bx + math.cos(ba) * b, by + math.sin(ba) * b)
    c.restoreState()


def centered_text(c, text, y, font, size, color, x=W / 2, tracking=0):
    c.setFillColor(color)
    if tracking:
        t = c.beginText()
        t.setFont(font, size)
        t.setCharSpace(tracking)
        width = c.stringWidth(text, font, size) + tracking * (len(text) - 1)
        t.setTextOrigin(x - width / 2, y)
        t.textOut(text)
        c.drawText(t)
    else:
        c.setFont(font, size)
        c.drawCentredString(x, y, text)


def greeting_block(c, cfg, color, accent, y):
    centered_text(c, cfg["greeting"], y, "Times-BoldItalic", 40, color)
    centered_text(c, f"SEASON'S GREETINGS  ·  {cfg['year']}", y - 26, "Helvetica", 8.5, accent, tracking=2.2)


# --------------------------------------------------------------------------
# Fronts
# --------------------------------------------------------------------------

def front_snow(c, cfg, rng):
    c.setFillColor(NAVY)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    # falling snow dots
    for _ in range(140):
        a = rng.uniform(0.25, 0.9)
        c.setFillColor(Color(1, 1, 1, alpha=a))
        c.circle(rng.uniform(0, W), rng.uniform(0, H), rng.uniform(0.5, 1.8), stroke=0, fill=1)
    # big flakes
    for x, y, r in [(0.7, 3.2, 0.42), (5.25, 3.05, 0.5), (0.95, 0.8, 0.3),
                    (5.35, 0.75, 0.36), (4.4, 3.55, 0.2), (1.7, 3.6, 0.16)]:
        snowflake(c, x * inch, y * inch, r * inch, Color(1, 1, 1, alpha=0.85), 1.0)
    # snowy ground
    c.setFillColor(Color(1, 1, 1, alpha=0.95))
    p = c.beginPath()
    p.moveTo(0, 0)
    p.lineTo(0, 0.45 * inch)
    p.curveTo(1.5 * inch, 0.75 * inch, 3.5 * inch, 0.2 * inch, W, 0.55 * inch)
    p.lineTo(W, 0)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    greeting_block(c, cfg, HexColor("#ffffff"), HexColor("#a9c3e8"), 2.05 * inch)


def ornament(c, x, top, string_len, r, color):
    y = top - string_len - r
    c.setStrokeColor(SOFT_INK)
    c.setLineWidth(0.6)
    c.line(x, top, x, y + r + 4)
    c.setFillColor(GOLD)
    c.roundRect(x - r * 0.28, y + r - 1, r * 0.56, 6, 1.2, stroke=0, fill=1)
    c.setFillColor(color)
    c.circle(x, y, r, stroke=0, fill=1)
    # decorative band + highlight
    c.setStrokeColor(Color(1, 1, 1, alpha=0.55))
    c.setLineWidth(1.2)
    c.line(x - r * 0.95, y - r * 0.3, x + r * 0.95, y - r * 0.3)
    c.line(x - r * 0.95, y + r * 0.05, x + r * 0.95, y + r * 0.05)
    c.setFillColor(Color(1, 1, 1, alpha=0.35))
    c.circle(x - r * 0.38, y + r * 0.4, r * 0.18, stroke=0, fill=1)


def front_ornaments(c, cfg, rng):
    c.setFillColor(CREAM)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    colors = [RED, GREEN, GOLD, HexColor("#2f6f8f"), RED, GREEN, HexColor("#8a2f5c")]
    xs = [0.55, 1.25, 2.0, 3.0, 4.0, 4.75, 5.45]
    lens = [0.55, 0.9, 0.35, 0.7, 0.4, 0.95, 0.5]
    rs = [0.26, 0.22, 0.3, 0.24, 0.28, 0.2, 0.25]
    for x, l, r, col in zip(xs, lens, rs, colors):
        ornament(c, x * inch, H, l * inch, r * inch, col)
    # little sparkles
    for k in range(14):
        snowflake(c, (0.45 + k * 0.39 + rng.uniform(-0.08, 0.08)) * inch,
                  (0.62 + (0.2 if k % 2 else -0.12) + rng.uniform(-0.05, 0.05)) * inch,
                  rng.uniform(0.045, 0.075) * inch, GOLD, 0.6)
    greeting_block(c, cfg, RED, GREEN, 1.55 * inch)
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.5)
    c.rect(0.15 * inch, 0.15 * inch, W - 0.3 * inch, H - 0.3 * inch, stroke=1, fill=0)


def pine(c, x, base, h, color):
    w = h * 0.55
    c.setFillColor(HexColor("#5a3b22"))
    c.rect(x - w * 0.07, base, w * 0.14, h * 0.12, stroke=0, fill=1)
    c.setFillColor(color)
    for i in range(3):
        y0 = base + h * (0.1 + i * 0.25)
        ww = w * (1 - i * 0.25)
        p = c.beginPath()
        p.moveTo(x - ww / 2, y0)
        p.lineTo(x + ww / 2, y0)
        p.lineTo(x, y0 + h * 0.45)
        p.close()
        c.drawPath(p, stroke=0, fill=1)


def front_pines(c, cfg, rng):
    c.setFillColor(HexColor("#8f1d24"))
    c.rect(0, 0, W, H, stroke=0, fill=1)
    for _ in range(60):
        c.setFillColor(Color(1, 1, 1, alpha=rng.uniform(0.2, 0.6)))
        c.circle(rng.uniform(0, W), rng.uniform(1.0, H) , rng.uniform(0.4, 1.2), stroke=0, fill=1)
    # back hill + trees
    c.setFillColor(HexColor("#f3e9dc"))
    p = c.beginPath()
    p.moveTo(0, 0)
    p.lineTo(0, 0.9 * inch)
    p.curveTo(2 * inch, 1.25 * inch, 4 * inch, 0.6 * inch, W, 1.0 * inch)
    p.lineTo(W, 0)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    for x, base, h, col in [(0.45, 0.82, 1.1, GREEN), (0.95, 0.85, 0.8, HexColor("#2c6b47")),
                            (5.05, 0.85, 1.15, GREEN), (5.6, 0.92, 0.85, HexColor("#2c6b47")),
                            (4.6, 0.82, 0.6, HexColor("#3c7d56"))]:
        pine(c, x * inch, base * inch, h * inch, col)
    # front hill
    c.setFillColor(HexColor("#ffffff"))
    p = c.beginPath()
    p.moveTo(0, 0)
    p.lineTo(0, 0.5 * inch)
    p.curveTo(2 * inch, 0.2 * inch, 4 * inch, 0.8 * inch, W, 0.45 * inch)
    p.lineTo(W, 0)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    star_x, star_y = W / 2, 3.35 * inch
    c.setFillColor(GOLD)
    p = c.beginPath()
    for k in range(10):
        r = 0.16 * inch if k % 2 == 0 else 0.065 * inch
        a = math.pi / 2 + k * math.pi / 5
        (p.moveTo if k == 0 else p.lineTo)(star_x + r * math.cos(a), star_y + r * math.sin(a))
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    greeting_block(c, cfg, HexColor("#ffffff"), HexColor("#f2c9a0"), 2.35 * inch)


FRONTS = {"snow": front_snow, "ornaments": front_ornaments, "pines": front_pines}


# --------------------------------------------------------------------------
# Back (message + address)
# --------------------------------------------------------------------------

def draw_back(c, friend, cfg):
    c.setFillColor(HexColor("#ffffff"))
    c.rect(0, 0, W, H, stroke=0, fill=1)
    m = 0.25 * inch
    divider_x = 3.0 * inch

    # small holiday accent in the top-left corner
    snowflake(c, m + 6, H - m - 6, 6, RED, 0.7)

    # return address (top-left, small)
    ret = cfg.get("return_address") or []
    c.setFillColor(SOFT_INK)
    c.setFont("Helvetica", 6.5)
    for i, line in enumerate([cfg["sender"], *ret] if ret else []):
        c.drawString(m + 18, H - m - 3 - i * 8, line)

    # message (left half)
    first = friend["name"].split()[0]
    template = friend.get("message") or cfg["message"]
    text = template.format(first_name=first, name=friend["name"], sender=cfg["sender"])
    font, size, leading = "Times-Italic", 11, 14
    box_w = divider_x - m - 0.2 * inch
    lines = []
    for para in text.replace("\\n", "\n").split("\n"):
        lines.extend(simpleSplit(para, font, size, box_w) if para.strip() else [""])
    top = H - m - (0.55 * inch if ret else 0.35 * inch)
    max_lines = int((top - 0.4 * inch) / leading) + 1
    if len(lines) > max_lines:
        print(f"warning: message for {friend['name']} is too long and was cut off", file=sys.stderr)
        lines = lines[:max_lines]
    c.setFillColor(INK)
    c.setFont(font, size)
    for i, line in enumerate(lines):
        c.drawString(m, top - i * leading, line)

    # divider
    c.setStrokeColor(HexColor("#d6d0c4"))
    c.setLineWidth(0.75)
    c.line(divider_x, 0.6 * inch, divider_x, H - 0.45 * inch)

    # stamp box (top-right)
    sw, sh = 0.85 * inch, 1.0 * inch
    sx, sy = W - m - sw, H - m - sh
    c.setStrokeColor(HexColor("#b9b2a5"))
    c.setDash(2, 2)
    c.rect(sx, sy, sw, sh, stroke=1, fill=0)
    c.setDash()
    c.setFillColor(HexColor("#b9b2a5"))
    c.setFont("Helvetica", 6)
    c.drawCentredString(sx + sw / 2, sy + sh / 2 + 2, "PLACE")
    c.drawCentredString(sx + sw / 2, sy + sh / 2 - 6, "STAMP HERE")

    # recipient address (right half). Bottom 5/8" is left blank for the USPS barcode.
    addr = address_lines(friend)
    ax = divider_x + 0.3 * inch
    size, leading = 11.5, 17
    ay = 1.95 * inch
    for i, line in enumerate(addr):
        c.setStrokeColor(HexColor("#e6e1d6"))
        c.setLineWidth(0.5)
        c.line(ax, ay - i * leading - 4, W - m, ay - i * leading - 4)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold" if i == 0 else "Helvetica", size)
        fit = size
        while c.stringWidth(line, c._fontname, fit) > W - m - ax and fit > 7:
            fit -= 0.5
        c.setFont(c._fontname, fit)
        c.drawString(ax, ay - i * leading, line)


# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv", help="CSV of friends (name,address1,address2,city,state,zip[,country,message,theme])")
    ap.add_argument("-o", "--out", default="out/postcards.pdf", help="output PDF path")
    ap.add_argument("-c", "--config", default="config.toml", help="sender/message settings")
    ap.add_argument("--theme", choices=THEMES + ["mix"], default="mix",
                    help="front design for everyone, or 'mix' to rotate (default)")
    ap.add_argument("--seed", type=int, default=2026, help="random seed for snow/sparkle placement")
    args = ap.parse_args()

    cfg = load_config(args.config)
    friends = load_friends(args.csv)
    if not friends:
        sys.exit("no friends found in CSV (needs a 'name' column)")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    c = Canvas(str(out), pagesize=(W, H))
    c.setTitle(f"{cfg['greeting']} postcards")

    for i, friend in enumerate(friends):
        theme = (friend.get("theme") or "").lower()
        if theme not in FRONTS:
            theme = THEMES[i % len(THEMES)] if args.theme == "mix" else args.theme
        FRONTS[theme](c, cfg, random.Random(args.seed + i))
        c.showPage()
        draw_back(c, friend, cfg)
        c.showPage()

    c.save()
    print(f"wrote {len(friends)} postcards ({2 * len(friends)} pages) to {out}")


if __name__ == "__main__":
    main()

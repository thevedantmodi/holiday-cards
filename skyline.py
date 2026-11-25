"""A cartoon of the Midtown Manhattan skyline as seen from Gantry Plaza State
Park in Long Island City, at night across the East River, framed by a wreath.

Everything is drawn in units of the badge radius, so it scales to any size.
"""

import math
import random

from reportlab.lib.colors import Color, HexColor

# palette
SKY_TOP = HexColor("#141a33")
SKY_LOW = HexColor("#3a3352")
FOG = Color(0.75, 0.72, 0.85, alpha=0.035)
FAR = HexColor("#262b3d")       # distant buildings
MID = HexColor("#1c2030")
NEAR = HexColor("#13151f")
WINDOW = HexColor("#ffd36b")
WINDOW_DIM = HexColor("#c9a65a")
GLASS = HexColor("#bcd3e6")
BLUE_LIGHT = HexColor("#3f9cff")
WATER = HexColor("#10131d")
WREATH_DARK = HexColor("#1f5135")
WREATH = HexColor("#2c6b47")
WREATH_LIGHT = HexColor("#4c8a5f")
BERRY = HexColor("#b3202e")
BOW = HexColor("#a3192a")
BOW_DARK = HexColor("#7d1220")


class _Pen:
    """Maps badge units (-1..1, origin at the centre) onto the page."""

    def __init__(self, c, cx, cy, r):
        self.c, self.cx, self.cy, self.r = c, cx, cy, r

    def x(self, u):
        return self.cx + u * self.r

    def y(self, v):
        return self.cy + v * self.r

    def rect(self, x0, y0, x1, y1, color):
        self.c.setFillColor(color)
        self.c.rect(self.x(x0), self.y(y0), (x1 - x0) * self.r, (y1 - y0) * self.r, stroke=0, fill=1)

    def poly(self, pts, color):
        p = self.c.beginPath()
        p.moveTo(self.x(pts[0][0]), self.y(pts[0][1]))
        for u, v in pts[1:]:
            p.lineTo(self.x(u), self.y(v))
        p.close()
        self.c.setFillColor(color)
        self.c.drawPath(p, stroke=0, fill=1)

    def windows(self, x0, y0, x1, y1, rng, cols, rows, lit=0.55, color=WINDOW):
        cw, rh = (x1 - x0) / cols, (y1 - y0) / rows
        for i in range(cols):
            for j in range(rows):
                if rng.random() < lit:
                    wx, wy = x0 + i * cw + cw * 0.25, y0 + j * rh + rh * 0.3
                    self.rect(wx, wy, wx + cw * 0.5, wy + rh * 0.45,
                              color if rng.random() > 0.3 else WINDOW_DIM)


SHORE = -0.30   # where the buildings meet the river


def _scene(pen, rng):
    c = pen.c
    # night sky
    c.linearGradient(pen.x(0), pen.y(1), pen.x(0), pen.y(SHORE),
                     (SKY_TOP, SKY_LOW), extend=True)
    # low clouds lit by the city
    c.setFillColor(FOG)
    for u, v, s in [(-0.4, 0.3, 0.5), (0.35, 0.25, 0.6), (0.0, 0.1, 0.45), (0.7, 0.05, 0.4)]:
        for k in range(6):   # stacked translucent discs give a soft glow
            c.circle(pen.x(u), pen.y(v), s * pen.r * (1 - k * 0.15), stroke=0, fill=1)
    # snow in the air
    for _ in range(45):
        c.setFillColor(Color(1, 1, 1, alpha=rng.uniform(0.35, 0.85)))
        c.circle(pen.x(rng.uniform(-1, 1)), pen.y(rng.uniform(-0.2, 1)),
                 rng.uniform(0.006, 0.016) * pen.r, stroke=0, fill=1)

    # distant filler buildings
    u = -1.0
    while u < 1.0:
        w = rng.uniform(0.06, 0.12)
        h = rng.uniform(0.06, 0.24)
        pen.rect(u, SHORE, u + w + 0.005, SHORE + h, FAR)
        pen.windows(u, SHORE, u + w, SHORE + h, rng, 3, max(2, int(h * 25)), lit=0.25)
        u += w

    # --- landmarks, left to right -------------------------------------
    # One Vanderbilt: tapering tower with a blue-lit spire
    pen.poly([(-0.44, SHORE), (-0.44, 0.28), (-0.41, 0.40), (-0.385, 0.46),
              (-0.36, 0.40), (-0.33, 0.30), (-0.33, SHORE)], MID)
    pen.poly([(-0.41, 0.40), (-0.385, 0.46), (-0.36, 0.40)], BLUE_LIGHT)
    pen.rect(-0.388, 0.46, -0.382, 0.62, BLUE_LIGHT)
    pen.windows(-0.43, SHORE + 0.05, -0.34, 0.27, rng, 3, 16, lit=0.35)

    # UN Secretariat: the wide glass slab
    pen.rect(-0.78, SHORE, -0.46, 0.20, HexColor("#222a3b"))
    pen.windows(-0.77, SHORE + 0.03, -0.47, 0.18, rng, 9, 18, lit=0.6, color=GLASS)
    pen.rect(-0.79, 0.20, -0.45, 0.215, HexColor("#2c3448"))

    # Chrysler Building: stacked arches and a needle spire
    cx, base_top = -0.10, 0.08
    pen.rect(cx - 0.055, SHORE, cx + 0.055, base_top, MID)
    pen.windows(cx - 0.05, SHORE + 0.04, cx + 0.05, base_top - 0.01, rng, 3, 10, lit=0.45)
    crown = HexColor("#d9dde6")
    for k, (half, height) in enumerate([(0.045, 0.05), (0.035, 0.045), (0.025, 0.04), (0.015, 0.035)]):
        y0 = base_top + sum(h for _, h in [(0.045, 0.05), (0.035, 0.045), (0.025, 0.04)][:k])
        pen.c.setFillColor(crown)
        pen.c.wedge(pen.x(cx - half), pen.y(y0 - height * 0.8), pen.x(cx + half),
                    pen.y(y0 + height * 1.2), 0, 180, stroke=0, fill=1)
        # triangular windows in each arch
        for t in (-0.5, 0, 0.5):
            pen.poly([(cx + t * half - 0.004, y0 + 0.005), (cx + t * half + 0.004, y0 + 0.005),
                      (cx + t * half, y0 + 0.02)], WINDOW)
    pen.rect(cx - 0.003, base_top + 0.17, cx + 0.003, base_top + 0.30, crown)

    # a tall tower with a glowing top
    pen.rect(0.03, SHORE, 0.11, 0.33, MID)
    pen.windows(0.035, SHORE + 0.04, 0.105, 0.30, rng, 3, 20, lit=0.5)
    c.setFillColor(Color(1, 0.9, 0.6, alpha=0.25))
    c.circle(pen.x(0.07), pen.y(0.35), 0.07 * pen.r, stroke=0, fill=1)
    pen.rect(0.035, 0.30, 0.105, 0.34, HexColor("#e9d9a8"))

    # Trump World Tower: the tall dark slab
    pen.rect(0.22, SHORE, 0.34, 0.52, NEAR)
    pen.windows(0.225, SHORE + 0.04, 0.335, 0.50, rng, 4, 30, lit=0.35)

    # Citigroup Center: the slanted roof
    pen.poly([(0.50, SHORE), (0.50, 0.14), (0.64, 0.26), (0.64, SHORE)], HexColor("#283043"))
    pen.poly([(0.50, 0.14), (0.64, 0.26), (0.64, 0.22), (0.50, 0.10)], HexColor("#e6edf5"))
    pen.windows(0.505, SHORE + 0.04, 0.635, 0.09, rng, 5, 12, lit=0.55, color=GLASS)

    # 432 Park Avenue: pencil-thin grid tower
    pen.rect(0.74, SHORE, 0.79, 0.44, MID)
    for j in range(22):
        y = SHORE + 0.04 + j * 0.032
        pen.rect(0.745, y, 0.785, y + 0.012, WINDOW if j % 3 else WINDOW_DIM)

    # nearer low-rise row along the FDR
    u = -1.0
    while u < 1.0:
        w = rng.uniform(0.08, 0.16)
        h = rng.uniform(0.03, 0.12)
        pen.rect(u, SHORE, u + w + 0.005, SHORE + h, NEAR)
        pen.windows(u, SHORE, u + w, SHORE + h, rng, 4, max(2, int(h * 30)), lit=0.3)
        u += w

    # East River with light reflections
    pen.rect(-1, -1, 1, SHORE, WATER)
    pen.rect(-1, SHORE - 0.012, 1, SHORE, HexColor("#2a2f40"))
    for _ in range(70):
        u = rng.uniform(-0.95, 0.95)
        v = rng.uniform(-0.9, SHORE - 0.03)
        w = rng.uniform(0.03, 0.10) * (1 + (SHORE - v))
        c.setFillColor(Color(1, 0.83, 0.42, alpha=rng.uniform(0.25, 0.6)))
        c.rect(pen.x(u), pen.y(v), w * pen.r, 0.008 * pen.r, stroke=0, fill=1)

    # Gantry Plaza's gantries in the foreground (right)
    _gantry(pen, 0.42, 0.90, -0.80, -0.06)


def _gantry(pen, x0, x1, y0, top):
    """The park's old railroad transfer-bridge gantries, in silhouette."""
    k = HexColor("#2e3342")     # steel, a shade lighter than the river
    leg = 0.035
    # two towers
    for lx in (x0, x1 - leg * 2):
        pen.rect(lx, y0, lx + 0.012, top, k)
        pen.rect(lx + leg * 2 - 0.012, y0, lx + leg * 2, top, k)
    # top beam and the hanging bridge apron
    pen.rect(x0 - 0.02, top - 0.02, x1 + 0.02, top + 0.06, k)
    pen.poly([(x0 + leg * 2, top - 0.20), (x1 - leg * 2, top - 0.16),
              (x1 - leg * 2, top - 0.20), (x0 + leg * 2, top - 0.24)], k)
    c = pen.c
    c.setStrokeColor(k)
    c.setLineWidth(0.012 * pen.r)
    # cross bracing
    for lx in (x0, x1 - leg * 2):
        steps = 6
        for s in range(steps):
            ya = y0 + (top - y0) * s / steps
            yb = y0 + (top - y0) * (s + 1) / steps
            c.line(pen.x(lx), pen.y(ya), pen.x(lx + leg * 2), pen.y(yb))
            c.line(pen.x(lx + leg * 2), pen.y(ya), pen.x(lx), pen.y(yb))
    # cables down to the apron
    c.setLineWidth(0.006 * pen.r)
    for t in (0.25, 0.5, 0.75):
        u = x0 + (x1 - x0) * t
        c.line(pen.x(u), pen.y(top - 0.02), pen.x(u), pen.y(top - 0.19))
    # the pier
    pen.rect(x0 - 0.1, y0 - 0.06, x1 + 0.2, y0 + 0.02, k)
    # a warm lamp on each tower
    for lx in (x0 + leg, x1 - leg):
        c.setFillColor(Color(1, 0.85, 0.5, alpha=0.9))
        c.circle(pen.x(lx), pen.y(top + 0.09), 0.012 * pen.r, stroke=0, fill=1)


def _leaf(c, x, y, length, width, angle, color):
    c.saveState()
    c.translate(x, y)
    c.rotate(angle)
    c.setFillColor(color)
    p = c.beginPath()
    p.moveTo(0, 0)
    p.curveTo(length * 0.3, width, length * 0.7, width, length, 0)
    p.curveTo(length * 0.7, -width, length * 0.3, -width, 0, 0)
    p.close()
    c.drawPath(p, stroke=0, fill=1)
    c.restoreState()


def _wreath(c, cx, cy, r, rng):
    ring = r * 1.08          # centre line of the wreath
    band = r * 0.16          # thickness
    # base ring so no gaps show
    c.setStrokeColor(WREATH_DARK)
    c.setLineWidth(band * 1.1)
    c.circle(cx, cy, ring, stroke=1, fill=0)
    # layered leaves
    colors = [WREATH_DARK, WREATH, WREATH_LIGHT]
    n = 110
    for layer in range(3):
        for i in range(n):
            a = 2 * math.pi * (i + layer * 0.33 + rng.uniform(-0.2, 0.2)) / n
            off = rng.uniform(-band * 0.55, band * 0.55)
            rr = ring + off
            x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
            tangent = math.degrees(a) + 90
            angle = tangent + rng.uniform(-35, 35) + (180 if i % 2 else 0)
            _leaf(c, x, y, r * rng.uniform(0.09, 0.13), r * rng.uniform(0.025, 0.035),
                  angle, colors[(layer + i) % 3] if layer < 2 else rng.choice(colors[1:]))
    # berry clusters
    for k in range(10):
        a = 2 * math.pi * k / 10 + 0.3
        bx, by = cx + ring * math.cos(a), cy + ring * math.sin(a)
        for dx, dy in [(-0.025, 0.01), (0.022, 0.015), (0, -0.022)]:
            c.setFillColor(BERRY)
            c.circle(bx + dx * r, by + dy * r, 0.028 * r, stroke=0, fill=1)
            c.setFillColor(Color(1, 1, 1, alpha=0.45))
            c.circle(bx + dx * r - 0.008 * r, by + dy * r + 0.009 * r, 0.008 * r, stroke=0, fill=1)
    _bow(c, cx, cy - ring, r)


def _bow(c, x, y, r):
    s = r
    # tails
    for side in (-1, 1):
        p = c.beginPath()
        p.moveTo(x, y)
        p.lineTo(x + side * 0.10 * s, y - 0.30 * s)
        p.lineTo(x + side * 0.04 * s, y - 0.26 * s)
        p.lineTo(x + side * 0.02 * s, y - 0.32 * s)
        p.lineTo(x - side * 0.02 * s, y - 0.02 * s)
        p.close()
        c.setFillColor(BOW_DARK if side < 0 else BOW)
        c.drawPath(p, stroke=0, fill=1)
    # loops
    for side in (-1, 1):
        p = c.beginPath()
        p.moveTo(x, y)
        p.curveTo(x + side * 0.10 * s, y + 0.16 * s, x + side * 0.26 * s, y + 0.12 * s,
                  x + side * 0.22 * s, y)
        p.curveTo(x + side * 0.26 * s, y - 0.10 * s, x + side * 0.10 * s, y - 0.12 * s, x, y)
        p.close()
        c.setFillColor(BOW)
        c.drawPath(p, stroke=0, fill=1)
        c.setFillColor(BOW_DARK)
        c.ellipse(x + side * 0.07 * s - 0.03 * s, y - 0.02 * s,
                  x + side * 0.07 * s + 0.03 * s, y + 0.03 * s, stroke=0, fill=1)
    # knot
    c.setFillColor(BOW_DARK)
    c.roundRect(x - 0.045 * s, y - 0.05 * s, 0.09 * s, 0.10 * s, 0.02 * s, stroke=0, fill=1)


def skyline_badge(c, cx, cy, r, seed=7):
    """Draw the skyline in a circle of radius r centred on (cx, cy), with a
    wreath around it. The wreath and bow extend about 0.3 r beyond the circle."""
    rng = random.Random(seed)
    c.saveState()
    clip = c.beginPath()
    clip.circle(cx, cy, r)
    c.clipPath(clip, stroke=0, fill=0)
    _scene(_Pen(c, cx, cy, r), rng)
    c.restoreState()
    _wreath(c, cx, cy, r, rng)

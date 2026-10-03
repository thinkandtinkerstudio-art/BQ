#!/usr/bin/env python3
"""Grano · Classic Natural Granola 250 g — carton artwork built on the client's dieline.

Outputs (in the project root):
  Grano-Granola-Box.ai / .pdf   layered PDF (Illustrator opens it as editable artwork: paths, live text,
                                 spot-colour dieline with overprint, named layers via PDF OCGs)
  Grano-Granola-Box.svg          same artwork as SVG with one named group per layer (Illustrator / Figma)
  previews/*.png                 renders

Coordinates are PDF points with a top-left origin (y grows downward); the page is the client's
dieline artboard: 1417.32 x 992.126 pt = 500 x 350 mm. Box: 130 x 60 x 200 mm. Bleed: 3 mm.
"""
import json, math, os, random, re, shutil, subprocess, sys

from fontTools.pens.recordingPen import RecordingPen
from fontTools.ttLib import TTFont as FTFont
from reportlab.lib.colors import CMYKColorSep, HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from shapely.geometry import Polygon, box as shapely_box
import pymupdf

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FONT_DIR = os.path.join(ROOT, "fonts")
PREVIEW_DIR = os.path.join(ROOT, "previews")
BASENAME = "Grano-Granola-Box"

W, H = 1417.32, 992.126          # artboard (500 x 350 mm)
MM = 72 / 25.4
BLEED = 3 * MM                   # 8.5 pt

# ----------------------------------------------------------------------------------------------
# Palette
# ----------------------------------------------------------------------------------------------
C = dict(
    cream="#FCEFD6", cream_deep="#F6DFB9", cream_pale="#FFF7E8",
    orange="#F88E51", orange_deep="#DF6A2E", orange_pale="#FCD9BE",
    blue="#8AAEED", blue_mid="#5283D4", blue_dark="#4D70B3", blue_light="#B4C8EE",
    navy="#081D57",
    gold="#F3C978", gold_deep="#D99E4B", amber="#E9A161", honey="#F2A93B", honey_deep="#D97B1F",
    green="#7E9A4B", green_deep="#5C7A3A", green_light="#9DB86A",
    wood="#A15820", wood_light="#C27A3C", wood_dark="#5F290D", brown="#8B4A1C", brown_light="#C98A3E",
    bark="#3A2C24", white="#FFFFFF", grey="#5F5F5F", grey_light="#D5D5D8", grey_note="#9E9EA3",
)
SPOT_CUT = {"spot": "Dieline-Cut", "cmyk": (0, 0.57, 0.98, 0), "rgb": "#F58A1F"}
SPOT_CREASE = {"spot": "Dieline-Crease", "cmyk": (0, 1, 1, 0), "rgb": "#ED1C24"}

# ----------------------------------------------------------------------------------------------
# Fonts
# ----------------------------------------------------------------------------------------------
FONTS = {
    "Fredoka-Bold": "Fredoka-Bold.ttf",
    "Fraunces-Black": "Fraunces-Black.ttf",
    "Poppins-Regular": "Poppins-Regular.ttf",
    "Poppins-Medium": "Poppins-Medium.ttf",
    "Poppins-SemiBold": "Poppins-SemiBold.ttf",
    "Poppins-Bold": "Poppins-Bold.ttf",
    "Poppins-ExtraBold": "Poppins-ExtraBold.ttf",
}
for _name, _file in FONTS.items():
    pdfmetrics.registerFont(TTFont(_name, os.path.join(FONT_DIR, _file)))


def sw(s, font, size, ls=0.0):
    """Visual width of a string with letter-spacing `ls` (em) — spacing after every glyph but the last."""
    return pdfmetrics.stringWidth(s, font, size) + ls * size * max(len(s) - 1, 0)


def wrap(s, font, size, maxw, ls=0.0):
    words, lines, cur = s.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if sw(t, font, size, ls) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


# ----------------------------------------------------------------------------------------------
# Scene primitives (all coordinates absolute, top-left origin)
# ----------------------------------------------------------------------------------------------
def rect(x, y, w, h, fill=None, stroke=None, sw_=1, rx=0, name=None, opacity=1):
    return {"t": "rect", "x": x, "y": y, "w": w, "h": h, "rx": rx, "fill": fill, "stroke": stroke, "sw": sw_,
            "name": name, "opacity": opacity}


def path(d, fill=None, stroke=None, sw_=1, cap="round", join="round", dash=None, name=None, evenodd=False, opacity=1):
    return {"t": "path", "d": d, "fill": fill, "stroke": stroke, "sw": sw_, "cap": cap, "join": join, "dash": dash,
            "name": name, "evenodd": evenodd, "opacity": opacity}


def text(x, y, s, font, size, fill, align="l", ls=0.0, name=None):
    return {"t": "text", "x": x, "y": y, "s": s, "font": font, "size": size, "fill": fill, "align": align, "ls": ls,
            "name": name}


def lines_(x, y, items, font, size, fill, lh, align="l", ls=0.0, name=None):
    return [text(x, y + i * lh, s, font, size, fill, align, ls, name=(f"{name}-{i + 1}" if name else None))
            for i, s in enumerate(items)]


def group(name, children, clip=None, opacity=1):
    return {"t": "group", "name": name, "children": children, "clip": clip, "opacity": opacity}


KAPPA = 0.5522847498


def f(v):
    return f"{v:.3f}".rstrip("0").rstrip(".")


class T:
    """Local → absolute transform: scale, rotate (degrees, clockwise on screen), translate."""

    def __init__(self, tx=0, ty=0, angle=0, scale=1, sx=None, sy=None):
        self.tx, self.ty = tx, ty
        a = math.radians(angle)
        self.cos, self.sin = math.cos(a), math.sin(a)
        self.sx = sx if sx is not None else scale
        self.sy = sy if sy is not None else scale

    def p(self, x, y):
        x, y = x * self.sx, y * self.sy
        return (self.tx + x * self.cos - y * self.sin, self.ty + x * self.sin + y * self.cos)


class PB:
    """Path builder in local coordinates."""

    def __init__(self, t=None):
        self.t = t or T()
        self.parts = []

    def _p(self, x, y):
        X, Y = self.t.p(x, y)
        return f"{f(X)} {f(Y)}"

    def M(self, x, y): self.parts.append("M " + self._p(x, y)); return self
    def L(self, x, y): self.parts.append("L " + self._p(x, y)); return self
    def C(self, x1, y1, x2, y2, x, y):
        self.parts.append("C " + self._p(x1, y1) + " " + self._p(x2, y2) + " " + self._p(x, y)); return self
    def Q(self, qx, qy, x, y):
        # convert a quadratic to a cubic using the current point
        raise NotImplementedError
    def Z(self): self.parts.append("Z"); return self

    def circle(self, cx, cy, r):
        k = KAPPA * r
        self.M(cx + r, cy).C(cx + r, cy + k, cx + k, cy + r, cx, cy + r).C(cx - k, cy + r, cx - r, cy + k, cx - r, cy)
        self.C(cx - r, cy - k, cx - k, cy - r, cx, cy - r).C(cx + k, cy - r, cx + r, cy - k, cx + r, cy).Z()
        return self

    def ellipse(self, cx, cy, rx, ry):
        kx, ky = KAPPA * rx, KAPPA * ry
        self.M(cx + rx, cy).C(cx + rx, cy + ky, cx + kx, cy + ry, cx, cy + ry).C(cx - kx, cy + ry, cx - rx, cy + ky, cx - rx, cy)
        self.C(cx - rx, cy - ky, cx - kx, cy - ry, cx, cy - ry).C(cx + kx, cy - ry, cx + rx, cy - ky, cx + rx, cy).Z()
        return self

    def rrect(self, x, y, w, h, r, corners=(1, 1, 1, 1)):
        """corners: (top-left, top-right, bottom-right, bottom-left) radii multipliers."""
        r = min(r, w / 2, h / 2)
        tl, tr, br, bl = [r * c for c in corners]
        k = KAPPA
        self.M(x + tl, y)
        self.L(x + w - tr, y)
        if tr: self.C(x + w - tr + k * tr, y, x + w, y + tr - k * tr, x + w, y + tr)
        self.L(x + w, y + h - br)
        if br: self.C(x + w, y + h - br + k * br, x + w - br + k * br, y + h, x + w - br, y + h)
        self.L(x + bl, y + h)
        if bl: self.C(x + bl - k * bl, y + h, x, y + h - bl + k * bl, x, y + h - bl)
        self.L(x, y + tl)
        if tl: self.C(x, y + tl - k * tl, x + tl - k * tl, y, x + tl, y)
        self.Z()
        return self

    def arc(self, cx, cy, r, a0, a1, move=True):
        """Arc in degrees (screen orientation: 0 = +x, 90 = +y/down)."""
        a0r, a1r = math.radians(a0), math.radians(a1)
        n = max(1, int(math.ceil(abs(a1r - a0r) / (math.pi / 2) - 1e-9)))
        da = (a1r - a0r) / n
        k = 4 / 3 * math.tan(da / 4)
        for i in range(n):
            s, e = a0r + i * da, a0r + (i + 1) * da
            p0 = (cx + r * math.cos(s), cy + r * math.sin(s))
            p3 = (cx + r * math.cos(e), cy + r * math.sin(e))
            p1 = (p0[0] - k * r * math.sin(s), p0[1] + k * r * math.cos(s))
            p2 = (p3[0] + k * r * math.sin(e), p3[1] - k * r * math.cos(e))
            if i == 0 and move: self.M(*p0)
            elif i == 0: self.L(*p0)
            self.C(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1])
        return self

    def leaf(self, L, Wd, base=(0, 0)):
        """Leaf with its base at `base` and tip at base+(L,0)."""
        bx, by = base
        self.M(bx, by).C(bx + L * 0.30, by - Wd / 2, bx + L * 0.78, by - Wd / 2, bx + L, by)
        self.C(bx + L * 0.78, by + Wd / 2, bx + L * 0.30, by + Wd / 2, bx, by).Z()
        return self

    def d(self):
        return " ".join(self.parts)


def circle_d(cx, cy, r): return PB().circle(cx, cy, r).d()
def ellipse_d(cx, cy, rx, ry): return PB().ellipse(cx, cy, rx, ry).d()
def rrect_d(x, y, w, h, r, corners=(1, 1, 1, 1)): return PB().rrect(x, y, w, h, r, corners).d()
def poly_d(pts, close=True):
    b = PB(); b.M(*pts[0])
    for p in pts[1:]: b.L(*p)
    if close: b.Z()
    return b.d()


def bez(p0, p1, p2, p3, t):
    mt = 1 - t
    return (mt ** 3 * p0[0] + 3 * mt * mt * t * p1[0] + 3 * mt * t * t * p2[0] + t ** 3 * p3[0],
            mt ** 3 * p0[1] + 3 * mt * mt * t * p1[1] + 3 * mt * t * t * p2[1] + t ** 3 * p3[1])


def bez_tangent(p0, p1, p2, p3, t):
    mt = 1 - t
    dx = 3 * mt * mt * (p1[0] - p0[0]) + 6 * mt * t * (p2[0] - p1[0]) + 3 * t * t * (p3[0] - p2[0])
    dy = 3 * mt * mt * (p1[1] - p0[1]) + 6 * mt * t * (p2[1] - p1[1]) + 3 * t * t * (p3[1] - p2[1])
    return math.degrees(math.atan2(dy, dx))


def sample_d(d, n=10):
    """Flatten an M/L/C/Z path (single subpath) into a point list for shapely."""
    toks = d.split(); pts = []; i = 0; cur = None
    while i < len(toks):
        t = toks[i]
        if t == "M" or t == "L":
            cur = (float(toks[i + 1]), float(toks[i + 2])); pts.append(cur); i += 3
        elif t == "C":
            p1 = (float(toks[i + 1]), float(toks[i + 2])); p2 = (float(toks[i + 3]), float(toks[i + 4]))
            p3 = (float(toks[i + 5]), float(toks[i + 6]))
            for k in range(1, n + 1): pts.append(bez(cur, p1, p2, p3, k / n))
            cur = p3; i += 7
        elif t == "Z": i += 1
        else: raise ValueError(t)
    return pts


def poly_to_d(poly):
    g = poly
    if g.geom_type == "MultiPolygon":
        g = max(g.geoms, key=lambda q: q.area)
    pts = list(g.exterior.coords)[:-1]
    return poly_d(pts)


# ----------------------------------------------------------------------------------------------
# Dieline geometry (all numbers come straight from the client's dieline .ai)
# ----------------------------------------------------------------------------------------------
X_GLUE, X_F0, X_F1, X_A1, X_B1, X_S1 = 147.616, 192.97, 561.474, 731.552, 1100.057, 1268.718
Y_TOP, Y_BOT = 261.412, 826.924
Y_LID_CREASE, Y_TONGUE_CREASE, Y_TONGUE_TOP = 259.995, 92.04, 35.349
Y_FLAP_BOT = 957.318

LID_D = ("M 192.97 259.995 L 192.97 89.916 L 194.387 89.916 L 194.387 63.696 "
         "C 194.387 56.178 197.374 48.967 202.69 43.651 C 208.006 38.336 215.216 35.349 222.734 35.349 L 531.71 35.349 "
         "C 539.228 35.349 546.438 38.336 551.754 43.651 C 557.07 48.967 560.057 56.178 560.057 63.696 L 560.057 89.916 "
         "L 561.474 89.916 L 561.474 259.995 Z")
GLUE_D = "M 192.97 261.412 L 147.616 273.565 L 147.616 814.204 L 192.97 826.357 Z"
FRONT_D = rrect_d(X_F0, Y_LID_CREASE, X_F1 - X_F0, Y_BOT - Y_LID_CREASE, 0)
SIDE_A_D = rrect_d(X_F1, Y_TOP, X_A1 - X_F1, Y_BOT - Y_TOP, 0)
BACK_D = rrect_d(X_A1, Y_TOP, X_B1 - X_A1, Y_BOT - Y_TOP, 0)
SIDE_B_D = rrect_d(X_B1, Y_TOP, X_S1 - X_B1, Y_BOT - Y_TOP, 0)
SIDE_A_TOP_D = ("M 561.474 261.412 L 564.835 261.038 L 571.395 251.491 L 574.23 148.026 L 679.363 148.026 "
                "C 685.773 148.026 691.993 150.198 697.009 154.188 C 702.026 158.179 705.541 163.751 706.983 169.996 "
                "L 722.198 235.9 L 730.702 244.404 L 730.702 261.412 Z")
SIDE_B_TOP_D = ("M 1100.907 261.412 L 1100.907 244.404 L 1109.411 235.9 L 1124.626 169.996 "
                "C 1126.068 163.751 1129.584 158.179 1134.6 154.188 C 1139.616 150.198 1145.837 148.026 1152.246 148.026 "
                "L 1255.962 148.026 L 1258.797 251.491 L 1268.718 261.412 Z")
SIDE_B_BOT_D = ("M 1268.718 826.924 L 1185.096 910.546 L 1193.804 943.044 C 1194.716 946.449 1193.993 950.085 1191.847 952.882 "
                "C 1189.701 955.678 1186.377 957.318 1182.852 957.318 L 1101.474 957.318 L 1101.474 826.924 Z")
BACK_BOT_D = ("M 732.704 826.924 L 815.883 911.963 L 815.883 945.979 C 815.883 948.986 817.078 951.87 819.204 953.997 "
              "C 821.331 956.123 824.215 957.318 827.222 957.318 L 1004.387 957.318 C 1007.395 957.318 1010.279 956.123 1012.405 953.997 "
              "C 1014.531 951.87 1015.726 948.986 1015.726 945.979 L 1015.726 911.963 L 1098.906 826.924 Z")
SIDE_A_BOT_D = ("M 562.628 826.924 L 646.513 910.546 L 637.805 943.044 C 636.893 946.449 637.616 950.085 639.762 952.882 "
                "C 641.908 955.678 645.233 957.318 648.758 957.318 L 730.135 957.318 L 730.135 826.924 Z")
FRONT_BOT_D = ("M 194.387 826.924 L 194.387 957.318 L 265.253 957.318 C 268.261 957.318 271.145 956.123 273.271 953.997 "
               "C 275.397 951.87 276.592 948.986 276.592 945.979 L 276.592 911.963 L 477.852 911.963 L 477.852 945.979 "
               "C 477.852 948.986 479.047 951.87 481.173 953.997 C 483.299 956.123 486.183 957.318 489.19 957.318 "
               "L 560.057 957.318 L 560.057 826.924 Z")

WINDOW = (254, 538, 246, 174, 16)   # x, y, w, h, r — photo window on the front panel


def bleed_d(d, amount=BLEED):
    return poly_to_d(Polygon(sample_d(d)).buffer(amount, join_style=2))


def bleed_below_crease_d(d, y_crease, amount=BLEED):
    g = Polygon(sample_d(d)).buffer(amount, join_style=2).intersection(shapely_box(0, y_crease, W, H))
    return poly_to_d(g)


# ----------------------------------------------------------------------------------------------
# Illustration helpers
# ----------------------------------------------------------------------------------------------
def leaf_el(x, y, L, Wd, angle, fill, vein=None, vein_w=1.1, name="Leaf"):
    t = T(x, y, angle)
    els = [path(PB(t).leaf(L, Wd).d(), fill=fill, name=name)]
    if vein:
        els.append(path(PB(t).M(L * 0.06, 0).L(L * 0.86, 0).d(), stroke=vein, sw_=vein_w, name=name + "-vein"))
    return els


def sprig(base, tip, n, fill, vein=None, stem=None, stem_w=2.0, leaf_len=24, leaf_w=11, bend=0.18, side=1, spread=40,
          name="Sprig", tip_leaf=True, taper=0.35):
    bx, by = base; tx, ty = tip
    dx, dy = tx - bx, ty - by
    L = math.hypot(dx, dy)
    nx, ny = -dy / L, dx / L
    p0, p3 = (bx, by), (tx, ty)
    p1 = (bx + dx * 0.33 + nx * L * bend, by + dy * 0.33 + ny * L * bend)
    p2 = (bx + dx * 0.72 + nx * L * bend, by + dy * 0.72 + ny * L * bend)
    els = []
    stem_col = stem or vein or fill
    els.append(path(f"M {f(p0[0])} {f(p0[1])} C {f(p1[0])} {f(p1[1])} {f(p2[0])} {f(p2[1])} {f(p3[0])} {f(p3[1])}",
                    stroke=stem_col, sw_=stem_w, name=name + "-stem"))
    count = n - (1 if tip_leaf else 0)
    for i in range(count):
        tt = 0.22 + 0.62 * (i / max(count - 1, 1))
        px, py = bez(p0, p1, p2, p3, tt)
        ang = bez_tangent(p0, p1, p2, p3, tt)
        s = side if i % 2 == 0 else -side
        ll = leaf_len * (1 - taper * i / max(count, 1))
        els += leaf_el(px, py, ll, leaf_w * (ll / leaf_len), ang + s * spread, fill, vein, name=f"{name}-leaf-{i + 1}")
    if tip_leaf:
        ang = bez_tangent(p0, p1, p2, p3, 1.0)
        els += leaf_el(tx, ty, leaf_len * (1 - taper), leaf_w * (1 - taper), ang, fill, vein, name=f"{name}-leaf-tip")
    return els


def honey_dipper(hx, hy, angle, scale=1.0, drip=True, name="Honey-Dipper"):
    """Head centred at (hx, hy); handle points along `angle` (degrees, screen orientation)."""
    t = T(hx, hy, angle, scale)
    els = []
    # handle
    els.append(path(PB(t).rrect(10, -4.5, 78, 9, 4.5).d(), fill=C["wood"], name=name + "-handle"))
    els.append(path(PB(t).M(16, -1.5).L(82, -1.5).d(), stroke=C["wood_light"], sw_=2 * scale, name=name + "-handle-light"))
    # head: barrel + grooves
    els.append(path(PB(t).rrect(-26, -15, 38, 30, 9).d(), fill=C["wood_light"], name=name + "-head"))
    for i, gx in enumerate((-19, -11, -3, 5)):
        els.append(path(PB(t).M(gx, -14).L(gx, 14).d(), stroke=C["wood_dark"], sw_=2.6 * scale, name=f"{name}-groove-{i + 1}"))
    # honey glaze on the lower half of the head (world-space "lower")
    glaze = PB(t).M(-26, 2).L(12, 2).C(14, 10, 8, 17, 0, 17).L(-16, 17).C(-24, 17, -28, 10, -26, 2).Z().d()
    els.append(path(glaze, fill=C["honey"], name=name + "-glaze"))
    if drip:
        # world-space drip under the head
        px, py = t.p(-6, 15)
        d = (f"M {f(px - 7 * scale)} {f(py)} C {f(px - 7 * scale)} {f(py + 10 * scale)} {f(px - 2 * scale)} {f(py + 12 * scale)} "
             f"{f(px - 1 * scale)} {f(py + 24 * scale)} C {f(px)} {f(py + 12 * scale)} {f(px + 6 * scale)} {f(py + 9 * scale)} "
             f"{f(px + 6 * scale)} {f(py)} Z")
        els.append(path(d, fill=C["honey"], name=name + "-drip"))
        els.append(path(circle_d(px - 1 * scale, py + 32 * scale, 4.2 * scale), fill=C["honey"], name=name + "-drop"))
        els.append(path(circle_d(px - 2.2 * scale, py + 30.8 * scale, 1.2 * scale), fill=C["cream_pale"], name=name + "-drop-light"))
    return els


def gingham(clip_d, bbox, cell=24.0, name="Gingham", base=None, stripe=None, cross=None):
    base = base or C["cream"]; stripe = stripe or C["blue_light"]; cross = cross or C["blue_mid"]
    x0, y0, x1, y1 = bbox
    els = [rect(x0, y0, x1 - x0, y1 - y0, fill=base, name=name + "-base")]
    i0, i1 = int(math.floor(x0 / cell)), int(math.ceil(x1 / cell))
    j0, j1 = int(math.floor(y0 / cell)), int(math.ceil(y1 / cell))
    cols = [i for i in range(i0, i1 + 1) if i % 2 == 1]
    rows = [j for j in range(j0, j1 + 1) if j % 2 == 1]
    for i in cols:
        els.append(rect(i * cell, y0, cell, y1 - y0, fill=stripe, name=f"{name}-v{i}"))
    for j in rows:
        els.append(rect(x0, j * cell, x1 - x0, cell, fill=stripe, name=f"{name}-h{j}"))
    for i in cols:
        for j in rows:
            els.append(rect(i * cell, j * cell, cell, cell, fill=cross, name=f"{name}-x{i}-{j}"))
    return group(name, els, clip=clip_d)


# ----------------------------------------------------------------------------------------------
# Logo — Fredoka Bold outlines + leaf details, as paths (a logo should never depend on a font)
# ----------------------------------------------------------------------------------------------
_FT = {}


def ft(font):
    if font not in _FT:
        _FT[font] = FTFont(os.path.join(FONT_DIR, FONTS[font]))
    return _FT[font]


def glyph_contours(font, ch, size, x, y_base):
    """Return (contours, advance) with contours as lists of ('M'|'L'|'C', pts) in absolute page coords."""
    fnt = ft(font); gs = fnt.getGlyphSet(); cmap = fnt.getBestCmap(); upem = fnt["head"].unitsPerEm
    sc = size / upem
    gname = cmap[ord(ch)]
    pen = RecordingPen(); gs[gname].draw(pen)
    adv = fnt["hmtx"][gname][0] * sc

    def P(pt):
        return (x + pt[0] * sc, y_base - pt[1] * sc)

    contours, cur, start, last = [], [], None, None
    for op, args in pen.value:
        if op == "moveTo":
            cur = [("M", [P(args[0])])]; start = args[0]; last = args[0]
        elif op == "lineTo":
            cur.append(("L", [P(args[0])])); last = args[0]
        elif op == "curveTo":
            cur.append(("C", [P(a) for a in args])); last = args[-1]
        elif op == "qCurveTo":
            pts = list(args)
            if pts[-1] is None:  # all off-curve: close on implied point
                pts = pts[:-1]; pts.append(((pts[0][0] + pts[-1][0]) / 2, (pts[0][1] + pts[-1][1]) / 2))
            offs, end = pts[:-1], pts[-1]
            prev = last
            for k, q in enumerate(offs):
                nxt = end if k == len(offs) - 1 else ((q[0] + offs[k + 1][0]) / 2, (q[1] + offs[k + 1][1]) / 2)
                c1 = (prev[0] + 2 / 3 * (q[0] - prev[0]), prev[1] + 2 / 3 * (q[1] - prev[1]))
                c2 = (nxt[0] + 2 / 3 * (q[0] - nxt[0]), nxt[1] + 2 / 3 * (q[1] - nxt[1]))
                cur.append(("C", [P(c1), P(c2), P(nxt)])); prev = nxt
            last = end
        elif op in ("closePath", "endPath"):
            if cur: contours.append(cur); cur = []
    if cur: contours.append(cur)
    return contours, adv


def contour_d(cnt):
    out = []
    for op, pts in cnt:
        out.append(op + " " + " ".join(f"{f(px)} {f(py)}" for px, py in pts))
    out.append("Z")
    return " ".join(out)


def contour_bbox(cnt):
    xs = [p[0] for _, pts in cnt for p in pts]; ys = [p[1] for _, pts in cnt for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def contour_area(cnt):
    b = contour_bbox(cnt); return (b[2] - b[0]) * (b[3] - b[1])


def logo(cx, y_base, size, fill, name="Logo-Grano"):
    """'Grano' wordmark centred on cx. Returns a group of paths."""
    font = "Fredoka-Bold"
    total = sw("Grano", font, size)
    x = cx - total / 2
    els = []
    pen_x = x
    for ch in "Grano":
        cnts, adv = glyph_contours(font, ch, size, pen_x, y_base)
        if ch == "o":
            outer = max(cnts, key=contour_area)
            inner = min(cnts, key=contour_area)
            ib = contour_bbox(inner)
            icx, icy = (ib[0] + ib[2]) / 2, (ib[1] + ib[3]) / 2
            ih = ib[3] - ib[1]
            leaf = PB(T(icx - ih * 0.36, icy + ih * 0.42, -52)).leaf(ih * 1.1, ih * 0.56).d()
            els.append(path(contour_d(outer) + " " + leaf, fill=fill, evenodd=True, name=name + "-o"))
        elif ch == "a":
            els.append(path(" ".join(contour_d(c) for c in cnts), fill=fill, evenodd=True, name=name + "-a"))
            # leaf sprig growing from the top-right of the 'a'
            ob = contour_bbox(max(cnts, key=contour_area))
            sx, sy = ob[2] - size * 0.19, ob[1] + size * 0.02
            els.append(path(f"M {f(sx)} {f(sy)} C {f(sx + size * 0.02)} {f(sy - size * 0.1)} {f(sx + size * 0.06)} {f(sy - size * 0.17)} "
                            f"{f(sx + size * 0.11)} {f(sy - size * 0.24)}", stroke=fill, sw_=size * 0.03, name=name + "-sprig-stem"))
            els += leaf_el(sx + size * 0.05, sy - size * 0.13, size * 0.22, size * 0.115, -122, fill, name=name + "-sprig-leaf-1")
            els += leaf_el(sx + size * 0.075, sy - size * 0.17, size * 0.23, size * 0.115, -34, fill, name=name + "-sprig-leaf-2")
        else:
            els.append(path(" ".join(contour_d(c) for c in cnts), fill=fill, evenodd=True, name=f"{name}-{ch}"))
        pen_x += adv
    return group(name, els)


# ----------------------------------------------------------------------------------------------
# Ingredient icons (each inside a ~30 pt box centred at cx, cy)
# ----------------------------------------------------------------------------------------------
def icon(kind, cx, cy, s=1.0):
    n = "Icon-" + kind
    els = []
    if kind == "oats":
        for i, (ox, oy, ang) in enumerate(((-7, 2, -62), (0, -2, -90), (8, 2, -118))):
            t = T(cx + ox * s, cy + oy * s, ang, s)
            els.append(path(PB(t).leaf(22, 9, base=(-11, 0)).d(), fill=C["gold"], name=f"{n}-{i + 1}"))
            els.append(path(PB(t).M(-8, 0).L(8, 0).d(), stroke=C["gold_deep"], sw_=1.1 * s, name=f"{n}-vein-{i + 1}"))
    elif kind == "pecan":
        t = T(cx, cy, -18, s)
        els.append(path(PB(t).ellipse(0, 0, 9.5, 14).d(), fill=C["brown"], name=n))
        els.append(path(PB(t).ellipse(0, 0, 6.5, 11).d(), fill=C["brown_light"], name=n + "-inner"))
        els.append(path(PB(t).M(0, -11).L(0, 11).d(), stroke=C["wood_dark"], sw_=1.8 * s, name=n + "-groove"))
        els.append(path(PB(t).M(-4, -6).L(-4, 6).d(), stroke=C["brown"], sw_=1.2 * s, name=n + "-ridge-1"))
        els.append(path(PB(t).M(4, -6).L(4, 6).d(), stroke=C["brown"], sw_=1.2 * s, name=n + "-ridge-2"))
    elif kind == "walnut":
        t = T(cx, cy, 0, s)
        els.append(path(PB(t).ellipse(0, 0, 13.5, 12.5).d(), fill=C["brown_light"], name=n))
        els.append(path(PB(t).M(0, -11).C(-2, -5, 2, 5, 0, 11).d(), stroke=C["brown"], sw_=2 * s, name=n + "-groove"))
        for i, (a, b) in enumerate((((-9, -4), (-3, 2)), ((-8, 5), (-3, 8)), ((9, -4), (3, 2)), ((8, 5), (3, 8)))):
            els.append(path(PB(t).M(a[0], a[1]).C(a[0] + 2, a[1] + 4, b[0] - 2, b[1] - 3, b[0], b[1]).d(),
                            stroke=C["brown"], sw_=1.4 * s, name=f"{n}-wrinkle-{i + 1}"))
    elif kind == "coconut":
        t = T(cx, cy, 20, s)
        els.append(path(PB(t).M(-13, 9).C(-13, -6, -2, -13, 12, -10).L(13, 9).Z().d(), fill=C["wood_dark"], name=n + "-husk"))
        els.append(path(PB(t).M(-9, 8).C(-9, -3, 0, -9, 10, -7).L(11, 8).Z().d(), fill=C["white"], name=n + "-flesh"))
        els.append(path(PB(t).M(-5, 4).C(-4, -1, 1, -4, 6, -3).d(), stroke=C["grey_light"], sw_=1.2 * s, name=n + "-shade"))
    elif kind == "almond":
        t = T(cx, cy, 24, s)
        els.append(path(PB(t).M(0, -14).C(8, -8, 9, 6, 0, 14).C(-9, 6, -8, -8, 0, -14).Z().d(), fill=C["amber"], name=n))
        els.append(path(PB(t).M(-1, -9).C(3, -6, 4, 4, -1, 9).d(), stroke=C["gold"], sw_=2 * s, name=n + "-ridge"))
    elif kind == "pumpkin":
        t = T(cx, cy, -90, s)
        els.append(path(PB(t).leaf(28, 15, base=(-14, 0)).d(), fill=C["green"], name=n))
        els.append(path(PB(t).leaf(20, 8, base=(-10, 0)).d(), fill=C["green_light"], name=n + "-inner"))
    elif kind == "honey":
        els += honey_dipper(cx - 4 * s, cy - 2 * s, -42, 0.42 * s, drip=True, name=n)
    elif kind == "cinnamon":
        for i, ang in enumerate((-28, 28)):
            t = T(cx, cy, ang, s)
            els.append(path(PB(t).rrect(-14, -3.8, 28, 7.6, 3.8).d(), fill=C["wood"], name=f"{n}-{i + 1}"))
            els.append(path(PB(t).M(-11, -1.2).L(11, -1.2).d(), stroke=C["wood_light"], sw_=1.3 * s, name=f"{n}-{i + 1}-light"))
            els.append(path(PB(t).circle(-13, 0, 2.2).d(), fill=C["wood_dark"], name=f"{n}-{i + 1}-end"))
    elif kind == "peanut":
        t = T(cx, cy, 0, s)
        els.append(path(PB(t).ellipse(0, 3, 14, 10).d(), fill=C["gold_deep"], name=n + "-base"))
        els.append(path(PB(t).M(-8, 2).C(-8, -6, 8, -8, 7, 0).C(6, 6, -4, 6, -3, 1).C(-2, -2, 3, -3, 3, 0).d(),
                        stroke=C["wood_light"], sw_=1.8 * s, name=n + "-swirl"))
        els.append(path(PB(t).M(1, -10).C(1, -6, 4, -5, 4, -2).C(2, -4, 0, -4, 1, -10).Z().d(), fill=C["gold_deep"], name=n + "-peak"))
    return group(n, els)


# ----------------------------------------------------------------------------------------------
# Granola (vector placeholder for the product photo, clipped to the window)
# ----------------------------------------------------------------------------------------------
def granola(x, y, w, h):
    rnd = random.Random(7)
    els = [rect(x, y, w, h, fill="#7A4A22", name="Granola-base")]
    tints = ["#A15820", "#B5692B", "#C98A3E", "#D99E4B", "#8B4A1C", "#C27A3C"]
    for i in range(170):
        r = rnd.uniform(4.5, 9.5)
        cx, cy = rnd.uniform(x + 2, x + w - 2), rnd.uniform(y + 2, y + h - 2)
        els.append(path(circle_d(cx, cy, r), fill=rnd.choice(tints), name=f"Cluster-{i + 1}"))
        if rnd.random() < 0.5:
            els.append(path(circle_d(cx - r * 0.3, cy - r * 0.3, r * 0.35), fill="#E3B46B", name=f"Cluster-{i + 1}-light"))
    for i in range(8):
        cx, cy = rnd.uniform(x + 15, x + w - 15), rnd.uniform(y + 15, y + h - 15)
        t = T(cx, cy, rnd.uniform(-60, 60))
        els.append(path(PB(t).ellipse(0, 0, 7, 11).d(), fill="#6B3315", name=f"Pecan-{i + 1}"))
        els.append(path(PB(t).ellipse(0, 0, 4.5, 8.5).d(), fill="#9A4E1E", name=f"Pecan-{i + 1}-inner"))
        els.append(path(PB(t).M(0, -8).L(0, 8).d(), stroke="#4A2210", sw_=1.5, name=f"Pecan-{i + 1}-groove"))
    for i in range(6):
        cx, cy = rnd.uniform(x + 12, x + w - 12), rnd.uniform(y + 12, y + h - 12)
        t = T(cx, cy, rnd.uniform(-80, 80))
        els.append(path(PB(t).M(0, -9).C(5, -5, 6, 4, 0, 9).C(-6, 4, -5, -5, 0, -9).Z().d(), fill="#F0D4A8", name=f"Almond-{i + 1}"))
    for i in range(6):
        cx, cy = rnd.uniform(x + 12, x + w - 12), rnd.uniform(y + 12, y + h - 12)
        t = T(cx, cy, rnd.uniform(-90, 90))
        els.append(path(PB(t).leaf(17, 9, base=(-8.5, 0)).d(), fill=C["green"], name=f"Pumpkin-seed-{i + 1}"))
    for i in range(10):
        cx, cy = rnd.uniform(x + 8, x + w - 8), rnd.uniform(y + 8, y + h - 8)
        t = T(cx, cy, rnd.uniform(-90, 90))
        els.append(path(PB(t).leaf(10, 4.5, base=(-5, 0)).d(), fill="#F3D08F", name=f"Oat-{i + 1}"))
    return els


# ----------------------------------------------------------------------------------------------
# Barcode (EAN-13, valid check digit — placeholder for the real GS1 code)
# ----------------------------------------------------------------------------------------------
EAN_L = ["0001101", "0011001", "0010011", "0111101", "0100011", "0110001", "0101111", "0111011", "0110111", "0001011"]
EAN_G = ["0100111", "0110011", "0011011", "0100001", "0011101", "0111001", "0000101", "0010001", "0001001", "0010111"]
EAN_R = ["1110010", "1100110", "1101100", "1000010", "1011100", "1001110", "1010000", "1000100", "1001000", "1110100"]
EAN_P = ["LLLLLL", "LLGLGG", "LLGGLG", "LLGGGL", "LGLLGG", "LGGLLG", "LGGGLL", "LGLGLG", "LGLGGL", "LGGLGL"]


def ean13_check(d12):
    s = sum(int(c) * (1 if i % 2 == 0 else 3) for i, c in enumerate(d12))
    return str((10 - s % 10) % 10)


def ean13(x, y, digits12, module=0.9, height=26, fill="#000000", font="Poppins-Regular"):
    code = digits12 + ean13_check(digits12)
    par = EAN_P[int(code[0])]
    bits = "101"
    for i, ch in enumerate(code[1:7]):
        bits += (EAN_L if par[i] == "L" else EAN_G)[int(ch)]
    bits += "01010"
    for ch in code[7:]:
        bits += EAN_R[int(ch)]
    bits += "101"
    els = []
    guard = set(range(0, 3)) | set(range(45, 50)) | set(range(92, 95))
    i = 0
    while i < len(bits):
        if bits[i] == "1":
            j = i
            while j < len(bits) and bits[j] == "1": j += 1
            h = height + (5 if i in guard else 0)
            els.append(rect(x + 11 * module + i * module, y, (j - i) * module, h, fill=fill, name=f"Bar-{i}"))
            i = j
        else:
            i += 1
    fs = 6.2
    els.append(text(x + 2, y + height + 6, code[0], font, fs, fill, name="EAN-first"))
    els.append(text(x + 11 * module + 3 * module + 21 * module, y + height + 6, " ".join(code[1:7]), font, fs, fill, "c", name="EAN-left"))
    els.append(text(x + 11 * module + 50 * module + 21 * module, y + height + 6, " ".join(code[7:]), font, fs, fill, "c", name="EAN-right"))
    return group("Barcode-EAN13", els), code


# ----------------------------------------------------------------------------------------------
# Panels
# ----------------------------------------------------------------------------------------------
def build_scene():
    layers = []  # (name, elements) in DRAWING order (bottom first)

    # ---- BACKGROUND ------------------------------------------------------------------------
    bg = []
    # bleed shapes first (outside the cut only; exact fills cover them inside the die)
    for d, col, nm in ((LID_D, C["orange"], "Bleed-Lid"), (GLUE_D, C["orange"], "Bleed-Glue-Flap"),
                       (SIDE_A_TOP_D, C["orange"], "Bleed-Dust-Flap-A"), (SIDE_B_TOP_D, C["orange"], "Bleed-Dust-Flap-B"),
                       (BACK_D, C["cream"], "Bleed-Back"), (SIDE_B_D, C["orange"], "Bleed-Side-B"),
                       (SIDE_A_D, C["blue"], "Bleed-Side-A")):
        bg.append(path(bleed_d(d), fill=col, name=nm))
    # exact panel fills
    bg.append(path(LID_D, fill=C["orange"], name="Lid"))
    bg.append(path(GLUE_D, fill=C["orange"], name="Glue-Flap"))
    bg.append(path(SIDE_A_TOP_D, fill=C["orange"], name="Dust-Flap-A"))
    bg.append(path(SIDE_B_TOP_D, fill=C["orange"], name="Dust-Flap-B"))
    bg.append(path(FRONT_D, fill=C["cream"], name="Front"))
    bg.append(path(SIDE_A_D, fill=C["blue"], name="Side-A"))
    bg.append(path(BACK_D, fill=C["cream"], name="Back"))
    bg.append(path(SIDE_B_D, fill=C["orange"], name="Side-B"))
    layers.append(("BACKGROUND", bg))

    # ---- GINGHAM (bottom flaps + bottom strips + picnic cloth) -----------------------------
    gg = []
    for d, nm in ((FRONT_BOT_D, "Flap-Front"), (SIDE_A_BOT_D, "Flap-Side-A"), (BACK_BOT_D, "Flap-Back"), (SIDE_B_BOT_D, "Flap-Side-B")):
        clip = bleed_below_crease_d(d, Y_BOT)
        gg.append(gingham(clip, (X_GLUE - 20, Y_BOT, X_S1 + 20, Y_FLAP_BOT + BLEED + 2), name="Gingham-" + nm))
    STRIP = 22
    for x0, x1, nm in ((X_F1, X_A1, "Side-A"), (X_A1, X_B1, "Back"), (X_B1, X_S1, "Side-B")):
        gg.append(gingham(rrect_d(x0, Y_BOT - STRIP, x1 - x0, STRIP, 0), (x0, Y_BOT - STRIP, x1, Y_BOT), name="Gingham-Strip-" + nm))
    # picnic cloth on the front with a soft wavy top edge
    cloth = (f"M {f(X_F0)} 662 C 240 650 280 672 330 660 C 380 648 420 670 470 660 C 510 652 540 664 {f(X_F1)} 656 "
             f"L {f(X_F1)} {f(Y_BOT)} L {f(X_F0)} {f(Y_BOT)} Z")
    gg.append(gingham(cloth, (X_F0, 640, X_F1, Y_BOT), name="Gingham-Cloth-Front"))
    layers.append(("GINGHAM", gg))

    # ---- PHOTO WINDOW (placeholder) --------------------------------------------------------
    wx, wy, ww, wh, wr = WINDOW
    win_d = rrect_d(wx, wy, ww, wh, wr)
    layers.append(("PHOTO-PLACEHOLDER (replace with granola photo)", [group("Window-Clip", granola(wx, wy, ww, wh), clip=win_d)]))

    # ---- ILLUSTRATIONS ---------------------------------------------------------------------
    il = []
    # Front: leaf sprigs + honey dipper (behind the basket)
    il += sprig((214, 548), (262, 418), 5, C["gold"], vein=C["gold_deep"], stem=C["gold_deep"], leaf_len=30, leaf_w=13, side=1, name="Sprig-Front-Left")
    il += leaf_el(222, 585, 26, 12, -150, C["green"], vein=C["green_deep"], name="Leaf-Front-Green-1")
    il += leaf_el(212, 468, 22, 10, 200, C["green"], vein=C["green_deep"], name="Leaf-Front-Green-2")
    il += sprig((296, 502), (334, 462), 3, C["gold"], vein=C["gold_deep"], stem=C["gold_deep"], leaf_len=22, leaf_w=10, side=-1, name="Sprig-Front-Mid-Left")
    il += sprig((458, 502), (420, 462), 3, C["gold"], vein=C["gold_deep"], stem=C["gold_deep"], leaf_len=22, leaf_w=10, side=1, name="Sprig-Front-Mid-Right")
    il += leaf_el(540, 540, 24, 11, 200, C["green"], vein=C["green_deep"], name="Leaf-Front-Green-3")
    il += honey_dipper(516, 486, -64, 0.8, drip=True, name="Honey-Dipper-Front")
    il += sprig((206, 800), (236, 742), 4, C["gold"], vein=C["gold_deep"], stem=C["gold_deep"], leaf_len=22, leaf_w=10, side=1, name="Sprig-Front-Bottom-Left")
    il += leaf_el(238, 806, 24, 11, 160, C["green"], vein=C["green_deep"], name="Leaf-Front-Green-4")
    # Front: basket body = frame around the photo window (even-odd hole), handle, rivets
    il.append(path(rrect_d(232, 512, 290, 222, 24) + " " + win_d, fill=C["cream_deep"], evenodd=True, name="Basket-Body"))
    il.append(path(rrect_d(232, 512, 290, 222, 24), stroke=C["blue_mid"], sw_=5, name="Basket-Body-Outline"))
    il.append(path(rrect_d(232 + 9, 512 + 9, 290 - 18, 222 - 18, 17), stroke=C["blue_light"], sw_=1.4, name="Basket-Body-Inner-Line"))
    il.append(path(win_d, stroke=C["blue_mid"], sw_=4.5, name="Window-Frame"))
    il.append(path("M 248 522 C 248 400 506 400 506 522", stroke=C["blue_dark"], sw_=12, cap="round", name="Basket-Handle"))
    il.append(path("M 248 522 C 248 400 506 400 506 522", stroke=C["blue_mid"], sw_=4, cap="round", name="Basket-Handle-Light"))
    for i, hx in enumerate((248, 506)):
        il.append(path(circle_d(hx, 524, 7), fill=C["blue_dark"], name=f"Basket-Rivet-{i + 1}"))
        il.append(path(circle_d(hx, 524, 3), fill=C["blue_light"], name=f"Basket-Rivet-{i + 1}-light"))
    # Front: label plate over the cloth
    il.append(path(rrect_d(262, 742, X_F1 - 262, Y_BOT - 742, 18, corners=(1, 0, 0, 0)), fill=C["cream"], name="Label-Plate"))
    # almond under 250 g
    t = T(520, 758, 35)
    il.append(path(PB(t).M(0, -13).C(8, -7, 9, 6, 0, 13).C(-9, 6, -8, -7, 0, -13).Z().d(), fill=C["amber"], name="Almond-Front"))
    il.append(path(PB(t).M(-1, -8).C(3, -5, 4, 4, -1, 8).d(), stroke=C["gold"], sw_=2, name="Almond-Front-ridge"))

    # Lid: pale leaf sprigs left & right
    il += sprig((236, 236), (218, 196), 3, C["orange_pale"], stem=C["orange_pale"], leaf_len=18, leaf_w=8, side=1, name="Sprig-Lid-Left", stem_w=1.6)
    il += sprig((518, 236), (536, 196), 3, C["orange_pale"], stem=C["orange_pale"], leaf_len=18, leaf_w=8, side=-1, name="Sprig-Lid-Right", stem_w=1.6)

    # Back: sprigs top corners
    il += sprig((752, 352), (786, 292), 4, C["gold"], vein=C["gold_deep"], stem=C["gold_deep"], leaf_len=24, leaf_w=11, side=1, name="Sprig-Back-Left")
    il += sprig((1080, 352), (1046, 292), 4, C["green"], vein=C["green_deep"], stem=C["green_deep"], leaf_len=24, leaf_w=11, side=-1, name="Sprig-Back-Right")
    # Back: three small leaf marks above the columns
    for i, cx in enumerate((752 + 8, 897 + 8, 1016 + 8)):
        il += leaf_el(cx - 6, 582, 20, 10, -62, C["orange_deep"], name=f"Leaf-Column-{i + 1}")

    # Side B: dipper, sprig, pale leaves
    il += honey_dipper(1190, 588, -40, 1.05, drip=True, name="Honey-Dipper-Side-B")
    il += sprig((1178, 790), (1150, 650), 6, C["orange_pale"], stem=C["orange_pale"], leaf_len=34, leaf_w=15, side=1, name="Sprig-Side-B", stem_w=2.4, bend=0.08)
    il += leaf_el(1166, 712, 34, 15, 170, C["green"], vein=C["green_deep"], name="Leaf-Side-B-Green-1")
    il += leaf_el(1182, 757, 30, 13, -20, C["green"], vein=C["green_deep"], name="Leaf-Side-B-Green-2")
    il += leaf_el(1186, 512, 16, 8, -120, C["orange_pale"], name="Leaf-Side-B-Pale-1")
    il += leaf_el(1192, 512, 16, 8, -60, C["orange_pale"], name="Leaf-Side-B-Pale-2")
    il.append(path("M 1189 528 L 1189 514", stroke=C["orange_pale"], sw_=1.6, name="Leaf-Side-B-Pale-stem"))

    # Side A: ingredient icons
    kinds = ["oats", "pecan", "walnut", "coconut", "almond", "pumpkin", "honey", "cinnamon", "peanut"]
    ROW0, ROWH = 372, 46.5
    for i, k in enumerate(kinds):
        il.append(icon(k, 616, ROW0 + i * ROWH + 14, 1.0))
    layers.append(("ILLUSTRATIONS", il))

    # ---- LOGO ------------------------------------------------------------------------------
    lg = [logo((X_F0 + X_F1) / 2, 362, 92, C["navy"], name="Logo-Front"),
          logo((X_A1 + X_B1) / 2, 352, 70, C["navy"], name="Logo-Back"),
          logo((X_F0 + X_F1) / 2, 205, 68, C["navy"], name="Logo-Lid")]
    layers.append(("LOGO", lg))

    # ---- TEXT ------------------------------------------------------------------------------
    tx = []
    navy = C["navy"]
    fcx = (X_F0 + X_F1) / 2
    # Lid
    tx.append(text(fcx, 68, "OPEN UP TO A BRIGHTER DAY.", "Poppins-SemiBold", 8.5, navy, "c", 0.08, name="Lid-Open"))
    tx.append(path(f"M 226 108 L {f(X_F1 - 33)} 108", stroke=navy, sw_=1.2, cap="butt", name="Lid-Rule"))
    tx.append(text(fcx, 236, "GOOD FOOD. BRIGHTER DAYS.", "Poppins-SemiBold", 9.5, navy, "c", 0.12, name="Lid-Tagline"))
    # Front
    tx.append(text(fcx, 394, "CLASSIC NATURAL GRANOLA", "Poppins-SemiBold", 11.5, navy, "c", 0.12, name="Front-Subtitle"))
    tx.append(text(372, 784, "PACK A BRIGHTER DAY.", "Poppins-Bold", 11, navy, "c", 0.06, name="Front-Pack"))
    tx.append(path("M 290 795 L 454 795", stroke=navy, sw_=1.2, cap="butt", name="Front-Rule"))
    tx.append(text(372, 814, "OATS, NUTS & SEEDS", "Poppins-SemiBold", 9, navy, "c", 0.1, name="Front-Oats"))
    tx.append(text(548, 814, "250g", "Poppins-Bold", 19, navy, "r", 0, name="Front-Weight"))
    # Side A
    acx = (X_F1 + X_A1) / 2
    tx += lines_(acx, 304, ["NINE", "GOOD THINGS", "TOGETHER."], "Poppins-ExtraBold", 13, navy, 15.5, "c", 0.02, name="Side-A-Title")
    tx.append(path("M 626 344 L 667 344", stroke=navy, sw_=1.4, cap="butt", name="Side-A-Rule"))
    labels = ["Oats", "Pecans", "Walnuts", "Coconut", "Blanched\nalmonds", "Pumpkin\nseeds", "Honey", "Cinnamon", "Peanut\nbutter"]
    for i, lab in enumerate(labels):
        yb = ROW0 + i * ROWH + 14
        tx.append(text(572, yb + 3.5, f"{i + 1:02d}", "Poppins-SemiBold", 9, navy, name=f"Side-A-No-{i + 1}"))
        ls = lab.split("\n")
        y0 = yb + 3.5 - (len(ls) - 1) * 5.5
        tx += lines_(640, y0, ls, "Poppins-SemiBold", 9.5, navy, 11, name=f"Side-A-Label-{i + 1}")
    tx.append(path(f"M 578 776 L {f(X_A1 - 16)} 776", stroke=navy, sw_=1.2, cap="butt", name="Side-A-Rule-2"))
    tx += lines_(acx, 790, ["Nine ingredients.", "One classic blend."], "Poppins-Bold", 9.8, navy, 12, "c", name="Side-A-Footer")
    # Back
    bcx = (X_A1 + X_B1) / 2
    tx.append(text(bcx, 378, "CLASSIC NATURAL GRANOLA", "Poppins-SemiBold", 9.5, navy, "c", 0.12, name="Back-Subtitle"))
    tx += lines_(bcx, 436, ["Look on the", "crunchy side."], "Fraunces-Black", 42, C["orange_deep"], 40, "c", name="Back-Headline")
    intro = ("A little crunch can change your perspective. Oats, pecans, walnuts, coconut, blanched almonds and pumpkin "
             "seeds meet honey, cinnamon and peanut butter in one joyfully classic blend.")
    tx += lines_(748, 507, wrap(intro, "Poppins-Regular", 8.6, X_B1 - 748 - 16), "Poppins-Regular", 8.6, navy, 12, name="Back-Intro")
    # three columns
    cols = [
        (748, 128, ["INGREDIENTS"], ["Oats, pecans, walnuts, coconut, blanched almonds, pumpkin seeds, honey, cinnamon, peanut butter.",
                                      "Contains oats, pecans, walnuts, almonds and peanuts.",
                                      "Store in a cool, dry place. Reseal the inner bag after opening."]),
        (897, 100, ["MAKE A", "BRIGHTER BREAK"], ["Pour over yogurt. Add milk. Or take a crunchy handful along for whatever the day brings."]),
        (1016, 72, ["ONE CLASSIC", "BLEND"], ["Simple ingredients. Big possibilities."]),
    ]
    for ci, (x0, wcol, head, paras) in enumerate(cols):
        y = 602
        tx += lines_(x0, y, head, "Poppins-Bold", 8.6, navy, 10.5, name=f"Back-Col-{ci + 1}-Head")
        y += 10.5 * len(head) + 2
        for pi, para in enumerate(paras):
            ls = wrap(para, "Poppins-Regular", 7.2, wcol)
            tx += lines_(x0, y, ls, "Poppins-Regular", 7.2, navy, 9.2, name=f"Back-Col-{ci + 1}-P{pi + 1}")
            y += 9.2 * len(ls) + 1.5
    for xd in (884, 1004):
        tx.append(path(f"M {xd} 574 L {xd} 700", stroke=navy, sw_=0.8, cap="butt", name="Back-Divider"))
    # nutrition table
    nx, ny, nw, nh = 745, 716, 226, 104
    tx.append(rect(nx, ny, nw, nh, fill=C["white"], stroke=C["grey"], sw_=0.7, rx=2, name="Nutrition-Box"))
    tx.append(text(nx + 6, ny + 11, "NUTRITION INFORMATION", "Poppins-Bold", 7.2, navy, name="Nutrition-Title"))
    tx.append(text(nx + 6, ny + 20, "Serving size: 45 g (1/2 cup)", "Poppins-Regular", 5.6, navy, name="Nutrition-Serving"))
    tx.append(text(nx + 6, ny + 27.5, "Servings per pack: Approx. 6", "Poppins-Regular", 5.6, navy, name="Nutrition-Servings"))
    rows = [("Typical values", "Per 100 g", "Per serving (45 g)"), ("Energy", "2010 kJ / 480 kcal", "905 kJ / 216 kcal"),
            ("Total Fat", "24 g", "10.8 g"), ("  - of which saturates", "6 g", "2.7 g"), ("Carbohydrate", "54 g", "24.3 g"),
            ("  - of which sugars", "17 g", "7.7 g"), ("Fibre", "7 g", "3.2 g"), ("Protein", "12 g", "5.4 g"), ("Salt", "0.02 g", "0.01 g")]
    ty0, rh = ny + 32, 7.9
    c1, c2, c3 = nx + 6, nx + 92, nx + 156
    tx.append(path(f"M {nx} {f(ty0)} L {nx + nw} {f(ty0)}", stroke=C["grey"], sw_=0.7, cap="butt", name="Nutrition-Line-Top"))
    for ri, (a, b, cc) in enumerate(rows):
        yb = ty0 + rh * (ri + 1) - 2.2
        fnt = "Poppins-SemiBold" if ri == 0 else "Poppins-Regular"
        tx.append(text(c1, yb, a, fnt, 5.6, navy, name=f"Nutrition-R{ri}-a"))
        tx.append(text(c2, yb, b, fnt, 5.6, navy, name=f"Nutrition-R{ri}-b"))
        tx.append(text(c3, yb, cc, fnt, 5.6, navy, name=f"Nutrition-R{ri}-c"))
        yl = ty0 + rh * (ri + 1)
        if ri < len(rows) - 1:
            tx.append(path(f"M {nx} {f(yl)} L {nx + nw} {f(yl)}", stroke=C["grey_light"], sw_=0.5, cap="butt", name=f"Nutrition-Line-{ri + 1}"))
    for xv in (c2 - 4, c3 - 4):
        tx.append(path(f"M {f(xv)} {f(ty0)} L {f(xv)} {f(ny + nh)}", stroke=C["grey_light"], sw_=0.5, cap="butt", name="Nutrition-VLine"))
    # barcode box
    bx_, by_, bw_, bh_ = 984, 716, 102, 52
    tx.append(rect(bx_, by_, bw_, bh_, fill=C["white"], stroke=C["grey"], sw_=0.7, rx=2, name="Barcode-Box"))
    tx.append(text(bx_ + 6, by_ + 10, "BARCODE", "Poppins-Bold", 6.2, navy, name="Barcode-Label"))
    bc, code = ean13(bx_ + 4, by_ + 14, "622400123456", module=0.88, height=22)
    tx.append(bc)
    # batch box
    tx.append(rect(bx_, 776, bw_, 44, fill=C["white"], stroke=C["grey"], sw_=0.7, rx=2, name="Batch-Box"))
    tx += lines_(bx_ + 6, 790, ["BATCH NO.:", "MFG DATE:", "BEST BEFORE:"], "Poppins-Bold", 6.2, navy, 12.5, name="Batch")
    # Side B
    sx0 = X_B1 + 18
    tx.append(text(sx0, 302, "GOOD FOOD.", "Poppins-SemiBold", 8, navy, ls=0.14, name="Side-B-Eyebrow"))
    tx += lines_(sx0, 358, ["Brighter", "days", "start", "here."], "Fraunces-Black", 35, navy, 36, name="Side-B-Headline")
    tx += lines_(sx0, 736, ["Real ingredients.", "A fresh perspective.", "Every single day."], "Poppins-SemiBold", 8.6, navy, 12.5, name="Side-B-Lines")
    tx.append(text(sx0, 792, "ONE CLASSIC BLEND", "Poppins-Bold", 7.4, navy, ls=0.1, name="Side-B-Footer"))
    layers.append(("TEXT", tx))

    # ---- NOTES (non-print) -----------------------------------------------------------------
    notes = []
    g = C["grey_note"]
    notes.append(text(X_GLUE, 22, "GRANO · Classic Natural Granola 250 g · carton 130 × 60 × 200 mm · dieline 500 × 350 mm · bleed 3 mm · "
                      "spot colours Dieline-Cut / Dieline-Crease (overprint) · fonts: Fredoka Bold (logo outlined) · Fraunces Black · Poppins · delete this layer before print.",
                      "Poppins-Regular", 7, g, name="Note-Header"))
    for x0, x1, lab in ((X_GLUE, X_F0, "GLUE FLAP 16 mm"), (X_F0, X_F1, "FRONT 130 × 200 mm"), (X_F1, X_A1, "SIDE 60 × 200 mm"),
                        (X_A1, X_B1, "BACK 130 × 200 mm"), (X_B1, X_S1, "SIDE 60 × 200 mm")):
        notes.append(text((x0 + x1) / 2, 978, lab, "Poppins-Medium", 7, g, "c", 0.04, name="Note-" + lab.split()[0]))
    notes.append(text(wx + ww / 2, wy + wh / 2 + 3, "PHOTO WINDOW · place the product photo here", "Poppins-SemiBold", 7, C["white"], "c", 0.04,
                      name="Note-Photo"))
    layers.append(("NOTES (delete before print)", notes))

    # ---- DIELINE ---------------------------------------------------------------------------
    dl = json.load(open(os.path.join(HERE, "dieline_paths.json")))
    cut, crease = [], []
    for pi, p in enumerate(dl):
        b = PB(); cur = None
        for kind, pts in p["items"]:
            if kind == "l":
                (x0, y0), (x1, y1) = pts
                if cur != (x0, y0): b.M(x0, y0)
                b.L(x1, y1); cur = (x1, y1)
            elif kind == "c":
                (x0, y0), (x1, y1), (x2, y2), (x3, y3) = pts
                if cur != (x0, y0): b.M(x0, y0)
                b.C(x1, y1, x2, y2, x3, y3); cur = (x3, y3)
        is_cut = abs(p["color"][1] - 0.53) < 0.05
        el = path(b.d(), stroke=SPOT_CUT if is_cut else SPOT_CREASE, sw_=0.75, cap="butt", join="miter",
                  name=("Cut-Outline" if is_cut else f"Crease-{pi}"))
        (cut if is_cut else crease).append(el)
    layers.append(("DIELINE - Crease", crease))
    layers.append(("DIELINE - Cut", cut))
    layers.append(("DIELINE - Window cut (optional)", [path(win_d, stroke=SPOT_CUT, sw_=0.75, cap="butt", join="miter", name="Window-Cut")]))
    return layers, code


# ----------------------------------------------------------------------------------------------
# PDF writer (ReportLab) + layer post-processing (PyMuPDF)
# ----------------------------------------------------------------------------------------------
def _tokens(d):
    toks = d.replace(",", " ").split(); i = 0
    while i < len(toks):
        t = toks[i]
        if t in ("M", "L"):
            yield t, [float(toks[i + 1]), float(toks[i + 2])]; i += 3
        elif t == "C":
            yield t, [float(v) for v in toks[i + 1:i + 7]]; i += 7
        elif t == "Z":
            yield t, []; i += 1
        else:
            raise ValueError(f"bad path token {t!r}")


class PdfWriter:
    def __init__(self, out):
        self.c = canvas.Canvas(out, pagesize=(W, H), pageCompression=0, initialFontName="Poppins-Regular")
        self.c.setTitle("Grano · Classic Natural Granola 250 g · carton artwork")
        self.c.setAuthor("Grano")
        self.c.setSubject("Carton artwork on dieline 500 x 350 mm — bleed 3 mm — spot colours Dieline-Cut / Dieline-Crease")
        self._spots = {}

    def y(self, v): return H - v

    def color(self, col):
        if isinstance(col, dict):
            key = col["spot"]
            if key not in self._spots:
                c, m, yy, k = col["cmyk"]
                self._spots[key] = CMYKColorSep(c, m, yy, k, spotName=key)
            return self._spots[key]
        return HexColor(col)

    def path_obj(self, d):
        p = self.c.beginPath()
        for cmd, a in _tokens(d):
            if cmd == "M": p.moveTo(a[0], self.y(a[1]))
            elif cmd == "L": p.lineTo(a[0], self.y(a[1]))
            elif cmd == "C": p.curveTo(a[0], self.y(a[1]), a[2], self.y(a[3]), a[4], self.y(a[5]))
            else: p.close()
        return p

    def el(self, e):
        c = self.c; t = e["t"]
        if t == "group":
            c.saveState()
            if e.get("clip"):
                c.clipPath(self.path_obj(e["clip"]), stroke=0, fill=0)
            if e.get("opacity", 1) != 1:
                c.setFillAlpha(e["opacity"]); c.setStrokeAlpha(e["opacity"])
            for ch in e["children"]: self.el(ch)
            c.restoreState()
            return
        c.saveState()
        if e.get("opacity", 1) != 1:
            c.setFillAlpha(e["opacity"]); c.setStrokeAlpha(e["opacity"])
        if t == "rect":
            x, yb, w, h, r = e["x"], self.y(e["y"] + e["h"]), e["w"], e["h"], e.get("rx") or 0
            if e.get("fill"): c.setFillColor(self.color(e["fill"]))
            if e.get("stroke"): c.setStrokeColor(self.color(e["stroke"])); c.setLineWidth(e["sw"])
            draw = (lambda s, fl: c.roundRect(x, yb, w, h, r, stroke=s, fill=fl)) if r else (lambda s, fl: c.rect(x, yb, w, h, stroke=s, fill=fl))
            draw(1 if e.get("stroke") else 0, 1 if e.get("fill") else 0)
        elif t == "path":
            p = self.path_obj(e["d"])
            if e.get("fill"): c.setFillColor(self.color(e["fill"]))
            if e.get("stroke"):
                st = e["stroke"]
                c.setStrokeColor(self.color(st)); c.setLineWidth(e["sw"])
                c.setLineCap({"round": 1, "butt": 0, "square": 2}[e.get("cap", "round")])
                c.setLineJoin({"round": 1, "miter": 0, "bevel": 2}[e.get("join", "round")])
                if e.get("dash"): c.setDash(e["dash"])
                if isinstance(st, dict): c.setStrokeOverprint(True)
            c.drawPath(p, stroke=1 if e.get("stroke") else 0, fill=1 if e.get("fill") else 0,
                       fillMode=0 if e.get("evenodd") else 1)
        elif t == "text":
            if not e["s"]:
                c.restoreState(); return
            font, size, ls = e["font"], e["size"], e.get("ls") or 0
            width = sw(e["s"], font, size, ls)
            x = e["x"] - (width / 2 if e["align"] == "c" else width if e["align"] == "r" else 0)
            c.setFillColor(self.color(e["fill"])); c.setFont(font, size)
            c.drawString(x, self.y(e["y"]), e["s"], charSpace=ls * size)
        c.restoreState()

    def layer(self, name, elements):
        self.c._code.append(f"%%LAYER-BEGIN {name}")
        for e in elements: self.el(e)
        self.c._code.append("%%LAYER-END")

    def save(self):
        self.c.showPage(); self.c.save()


def add_pdf_layers(pdf_path, layer_names_top_to_bottom):
    """Turn the %%LAYER markers into PDF optional-content groups (Illustrator reads them as layers)."""
    doc = pymupdf.open(pdf_path); page = doc[0]
    ocg = {nm: doc.add_ocg(nm, on=True) for nm in layer_names_top_to_bottom}
    cont = page.read_contents().decode("latin1")
    order = []

    def begin(m):
        nm = m.group(1).strip()
        if nm not in order: order.append(nm)
        return f"/OC /oc{order.index(nm) + 1} BDC"

    cont = re.sub(r"%%LAYER-BEGIN ([^\n]*)", begin, cont).replace("%%LAYER-END", "EMC")
    xrefs = page.get_contents()
    doc.update_stream(xrefs[0], cont.encode("latin1"))
    if len(xrefs) > 1:
        doc.xref_set_key(page.xref, "Contents", f"{xrefs[0]} 0 R")
    props = "<<" + " ".join(f"/oc{i + 1} {ocg[nm]} 0 R" for i, nm in enumerate(order)) + ">>"
    doc.xref_set_key(page.xref, "Resources/Properties", props)
    # trim box = artboard, art box = dieline bounds
    doc.xref_set_key(page.xref, "TrimBox", f"[0 0 {W} {H}]")
    doc.xref_set_key(page.xref, "ArtBox", f"[{X_GLUE - BLEED:.3f} {H - Y_FLAP_BOT - BLEED:.3f} {X_S1 + BLEED:.3f} {H - Y_TONGUE_TOP + BLEED:.3f}]")
    doc.set_metadata({"title": "Grano · Classic Natural Granola 250 g · carton artwork", "author": "Grano",
                      "subject": "Carton artwork on dieline 500 x 350 mm, bleed 3 mm, spot colours Dieline-Cut / Dieline-Crease",
                      "creator": "grano-granola-box/tools/build.py", "producer": "ReportLab + PyMuPDF"})
    tmp = pdf_path + ".tmp"
    doc.save(tmp, garbage=1, deflate=False)
    doc.close(); os.replace(tmp, pdf_path)


# ----------------------------------------------------------------------------------------------
# SVG writer
# ----------------------------------------------------------------------------------------------
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def slug(s):
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", s).strip("-")


class SvgWriter:
    def __init__(self):
        self.out = []; self.defs = []; self.nclip = 0; self.ids = set()

    def uid(self, base):
        b = slug(base or "el"); n = b; i = 2
        while n in self.ids: n = f"{b}-{i}"; i += 1
        self.ids.add(n); return n

    def col(self, c):
        return c["rgb"] if isinstance(c, dict) else c

    def el(self, e, ind="  "):
        t = e["t"]; nm = e.get("name")
        idattr = f' id="{self.uid(nm)}"' if nm else ""
        op = f' opacity="{e["opacity"]}"' if e.get("opacity", 1) != 1 else ""
        if t == "group":
            clip = ""
            if e.get("clip"):
                self.nclip += 1; cid = f"clip-{self.nclip}"
                self.defs.append(f'<clipPath id="{cid}"><path d="{e["clip"]}"/></clipPath>')
                clip = f' clip-path="url(#{cid})"'
            self.out.append(f'{ind}<g{idattr}{clip}{op}>')
            for ch in e["children"]: self.el(ch, ind + "  ")
            self.out.append(f"{ind}</g>")
            return
        fill = f' fill="{self.col(e["fill"])}"' if e.get("fill") else ' fill="none"'
        stroke = ""
        if e.get("stroke"):
            stroke = (f' stroke="{self.col(e["stroke"])}" stroke-width="{f(e["sw"])}"'
                      f' stroke-linecap="{e.get("cap", "round")}" stroke-linejoin="{e.get("join", "round")}"')
            if e.get("dash"): stroke += f' stroke-dasharray="{" ".join(f(v) for v in e["dash"])}"'
        if t == "rect":
            rx = f' rx="{f(e["rx"])}"' if e.get("rx") else ""
            self.out.append(f'{ind}<rect{idattr} x="{f(e["x"])}" y="{f(e["y"])}" width="{f(e["w"])}" height="{f(e["h"])}"{rx}{fill}{stroke}{op}/>')
        elif t == "path":
            fr = ' fill-rule="evenodd"' if e.get("evenodd") else ""
            self.out.append(f'{ind}<path{idattr} d="{e["d"]}"{fill}{stroke}{fr}{op}/>')
        elif t == "text":
            if not e["s"]: return
            font, size, ls = e["font"], e["size"], e.get("ls") or 0
            width = sw(e["s"], font, size, ls)
            x = e["x"] - (width / 2 if e["align"] == "c" else width if e["align"] == "r" else 0)
            lsattr = f' letter-spacing="{f(ls * size)}"' if ls else ""
            self.out.append(f'{ind}<text{idattr} x="{f(x)}" y="{f(e["y"])}" font-family="{font}" font-size="{f(size)}"'
                            f' fill="{self.col(e["fill"])}"{lsattr}>{esc(e["s"])}</text>')

    def layer(self, name, elements):
        self.out.append(f'  <g id="{self.uid(name)}">')
        for e in elements: self.el(e, "    ")
        self.out.append("  </g>")

    def save(self, out):
        head = (f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="{W}pt" height="{H}pt" '
                f'viewBox="0 0 {W} {H}">\n<title>Grano · Classic Natural Granola 250 g · carton artwork</title>\n')
        defs = "<defs>\n" + "\n".join(self.defs) + "\n</defs>\n" if self.defs else ""
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(head + defs + "\n".join(self.out) + "\n</svg>\n")


# ----------------------------------------------------------------------------------------------
# Swatches (.ase) + package zip
# ----------------------------------------------------------------------------------------------
def write_ase(out):
    import struct

    def u16(txt):
        return txt.encode("utf-16-be") + b"\x00\x00"

    def hex_rgb(h):
        return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))

    swatches = [("Cream", C["cream"]), ("Cream Deep", C["cream_deep"]), ("Orange", C["orange"]), ("Orange Deep", C["orange_deep"]),
                ("Orange Pale", C["orange_pale"]), ("Blue", C["blue"]), ("Blue Mid", C["blue_mid"]), ("Blue Dark", C["blue_dark"]),
                ("Blue Light", C["blue_light"]), ("Navy", C["navy"]), ("Gold", C["gold"]), ("Gold Deep", C["gold_deep"]),
                ("Amber", C["amber"]), ("Honey", C["honey"]), ("Green", C["green"]), ("Green Deep", C["green_deep"]),
                ("Wood", C["wood"]), ("Wood Dark", C["wood_dark"]), ("Brown", C["brown"]), ("Grey", C["grey"])]
    blocks = []
    gname = "Grano Carton"
    blocks.append(struct.pack(">HI", 0xC001, 2 + len(u16(gname))) + struct.pack(">H", len(gname) + 1) + u16(gname))
    for name, hx in swatches:
        body = struct.pack(">H", len(name) + 1) + u16(name) + b"RGB " + b"".join(struct.pack(">f", v) for v in hex_rgb(hx)) + struct.pack(">H", 0)
        blocks.append(struct.pack(">HI", 0x0001, len(body)) + body)
    for spot in (SPOT_CUT, SPOT_CREASE):
        name = spot["spot"]
        body = struct.pack(">H", len(name) + 1) + u16(name) + b"CMYK" + b"".join(struct.pack(">f", v) for v in spot["cmyk"]) + struct.pack(">H", 1)
        blocks.append(struct.pack(">HI", 0x0001, len(body)) + body)
    blocks.append(struct.pack(">HI", 0xC002, 0))
    with open(out, "wb") as fh:
        fh.write(b"ASEF" + struct.pack(">HHI", 1, 0, len(blocks)) + b"".join(blocks))


def write_zip(out):
    import zipfile
    names = [BASENAME + ".ai", BASENAME + ".pdf", BASENAME + ".svg", BASENAME + "-swatches.ase", "README.md"]
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            pth = os.path.join(ROOT, n)
            if os.path.exists(pth): z.write(pth, n)
        for sub in ("fonts", "dieline", "previews"):
            d = os.path.join(ROOT, sub)
            for fn in sorted(os.listdir(d)):
                if fn.endswith(".zip"): continue
                z.write(os.path.join(d, fn), f"{sub}/{fn}")


# ----------------------------------------------------------------------------------------------
def main():
    layers, code = build_scene()
    pdf_path = os.path.join(ROOT, BASENAME + ".pdf")
    pw = PdfWriter(pdf_path)
    for nm, els in layers: pw.layer(nm, els)
    pw.save()
    add_pdf_layers(pdf_path, [nm for nm, _ in reversed(layers)])
    shutil.copyfile(pdf_path, os.path.join(ROOT, BASENAME + ".ai"))
    sv = SvgWriter()
    for nm, els in layers: sv.layer(nm, els)
    sv.save(os.path.join(ROOT, BASENAME + ".svg"))
    os.makedirs(PREVIEW_DIR, exist_ok=True)
    subprocess.run(["pdftoppm", "-r", "110", "-png", "-singlefile", pdf_path, os.path.join(PREVIEW_DIR, BASENAME + "-preview")], check=True)
    subprocess.run(["pdftoppm", "-r", "300", "-png", "-singlefile", pdf_path, os.path.join(PREVIEW_DIR, BASENAME + "-300dpi")], check=True)
    write_ase(os.path.join(ROOT, BASENAME + "-swatches.ase"))
    write_zip(os.path.join(ROOT, BASENAME + "-package.zip"))
    n = sum(len(e) for _, e in layers)
    print(f"built {BASENAME}.ai/.pdf/.svg — {len(layers)} layers, {n} top-level elements, barcode {code}")


if __name__ == "__main__":
    main()

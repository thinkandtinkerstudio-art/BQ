#!/usr/bin/env python3
"""AFAQ Corporate Profile — single source of truth.

Builds the 8-slide (1080x1920) deck spec, then writes:
  pages/*.svg              import-safe SVG for Figma (inline fills only, editable <text>, no masks/CSS/transforms)
  pages-illustrator/*.svg  same pages with PostScript font names (Inter-Light …) so Illustrator picks the right weights
  assets/**                logo, graphics, icons, palette (SVG + JSON + ASE)
  spec/deck-spec.json      the spec consumed by figma/figma-build.js
  figma/slides/*.js        self-contained use_figma scripts (one per slide) and figma/scripter-build-all.js
"""
import json, math, os, re, struct
from xml.sax.saxutils import escape
from PIL import ImageFont
from fontTools.ttLib import TTFont

_HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("DECK_OUT") or (os.path.dirname(_HERE) if os.path.basename(_HERE) == "tools" else "/home/user/BQ/afaq-profile-1080x1920")
FONT_DIR = os.environ.get("DECK_FONTS") or (os.path.join(OUT, "fonts") if os.path.exists(os.path.join(OUT, "fonts", "Inter-Regular.ttf")) else os.path.expanduser("~/.fonts"))
W, H = 1080, 1920
M = 72
CW = W - 2 * M  # 936
FOOT_Y = 1800   # footer rule; content must end above 1744
K = 0.5522847498307936

# ---------------------------------------------------------------- palette
P = {
    "lime": "#C8FB5F", "lime_deep": "#A4DC3C", "lime_pale": "#E9FBB8",
    "teal": "#053C45", "teal_ink": "#03343D", "teal_mid": "#0E5560", "teal_deep": "#022C32", "teal_soft": "#1F7580",
    "cream": "#F5F4EB", "cream_2": "#E8E8DC", "white": "#FFFFFF",
    "charcoal": "#202C28", "orange": "#FD7E25", "orange_deep": "#B04C0E",
    "muted": "#5A7175", "line": "#D9DCCF",
}
PALETTE_DOC = [
    ("Lime", P["lime"], "Primary accent, ribbons, tabs, highlights"),
    ("Lime Deep", P["lime_deep"], "Ribbon shading"),
    ("Lime Pale", P["lime_pale"], "Ribbon highlight"),
    ("Teal", P["teal"], "Dark backgrounds, headlines on light"),
    ("Teal Ink", P["teal_ink"], "Wordmark and label text on light / orange"),
    ("Teal Mid", P["teal_mid"], "Cards on dark backgrounds"),
    ("Teal Deep", P["teal_deep"], "Photo placeholder gradient (light pages)"),
    ("Teal Soft", P["teal_soft"], "Illustration mid-tone, ribbon underside on dark pages"),
    ("Cream", P["cream"], "Light backgrounds"),
    ("Cream 2", P["cream_2"], "Subtle surfaces"),
    ("White", P["white"], "Cards on light backgrounds"),
    ("Charcoal", P["charcoal"], "Panel silhouettes"),
    ("Orange", P["orange"], "Label blocks, sun, accent rule (shapes only)"),
    ("Orange Deep", P["orange_deep"], "Accent text on white / cream (AA contrast)"),
    ("Muted", P["muted"], "Secondary text on light"),
    ("Line", P["line"], "Rules on light"),
]

FONT_FILES = {300: "Inter-Light.ttf", 400: "Inter-Regular.ttf", 500: "Inter-Medium.ttf", 600: "Inter-SemiBold.ttf", 700: "Inter-Bold.ttf"}
STYLE_NAMES = {300: "Light", 400: "Regular", 500: "Medium", 600: "Semi Bold", 700: "Bold"}
PS_NAMES = {300: "Inter-Light", 400: "Inter-Regular", 500: "Inter-Medium", 600: "Inter-SemiBold", 700: "Inter-Bold"}

_tt = TTFont(os.path.join(FONT_DIR, "Inter-Regular.ttf"))
UPM = _tt["head"].unitsPerEm
ASC = _tt["hhea"].ascent / UPM
DESC = -_tt["hhea"].descent / UPM

def baseline(size, lh):
    """First baseline offset from the top of a line box (Figma centres the glyph box in the line box)."""
    return (lh - (ASC + DESC) * size) / 2 + ASC * size

_fonts = {}
def font(weight, size):
    key = (weight, size)
    if key not in _fonts:
        _fonts[key] = ImageFont.truetype(os.path.join(FONT_DIR, FONT_FILES[weight]), size)
    return _fonts[key]

def text_width(s, size, weight, ls=0.0):
    return font(weight, size).getlength(s) + ls * size * max(len(s) - 1, 0)

def wrap(text, size, weight, width, ls=0.0):
    """Greedy wrap against a slightly narrower limit so Figma's own layout never adds an extra line."""
    limit = width - max(3.0, 0.015 * width)
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            cand = word if not cur else cur + " " + word
            if not cur or text_width(cand, size, weight, ls) <= limit:
                cur = cand
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
    return lines

def fmt(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s

def pt(p):
    return f"{fmt(p[0])} {fmt(p[1])}"

# ---------------------------------------------------------------- geometry (absolute M/L/C/Z only)
def unit(ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy) or 1.0
    return dx / L, dy / L

def rounded_polygon(pts, radii):
    """Closed path through pts (clockwise) with per-corner radius; works for convex and concave (reflex) corners."""
    n = len(pts)
    if not isinstance(radii, (list, tuple)):
        radii = [radii] * n
    segs = []
    for i, (cx, cy) in enumerate(pts):
        px, py = pts[i - 1]
        nx, ny = pts[(i + 1) % n]
        r = radii[i]
        dix, diy = unit(px, py, cx, cy)
        dox, doy = unit(cx, cy, nx, ny)
        s = (cx - dix * r, cy - diy * r)
        e = (cx + dox * r, cy + doy * r)
        c1 = (s[0] + dix * r * K, s[1] + diy * r * K)
        c2 = (e[0] - dox * r * K, e[1] - doy * r * K)
        segs.append((r, s, c1, c2, e))
    d = [f"M {pt(segs[0][1])}"]
    for i, (r, s, c1, c2, e) in enumerate(segs):
        if i > 0:
            d.append(f"L {pt(s)}")
        if r > 0:
            d.append(f"C {pt(c1)} {pt(c2)} {pt(e)}")
    d.append("Z")
    return " ".join(d)

def rect_path(x, y, w, h, r=0, notch=None):
    """Rounded rect; notch={'corner':'tl'|'tr'|'bl'|'br','w':..,'h':..,'r':..} cuts a rounded notch out of that corner."""
    if not notch:
        return rounded_polygon([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], r)
    nw, nh, nr = notch["w"], notch["h"], notch.get("r", r * 0.6)
    c = notch["corner"]
    if c == "tr":
        pts = [(x, y), (x + w - nw, y), (x + w - nw, y + nh), (x + w, y + nh), (x + w, y + h), (x, y + h)]
        rad = [r, r, nr, r, r, r]
    elif c == "tl":
        pts = [(x + nw, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y + nh), (x + nw, y + nh)]
        rad = [r, r, r, r, r, nr]
    elif c == "br":
        pts = [(x, y), (x + w, y), (x + w, y + h - nh), (x + w - nw, y + h - nh), (x + w - nw, y + h), (x, y + h)]
        rad = [r, r, r, nr, r, r]
    else:  # bl
        pts = [(x, y), (x + w, y), (x + w, y + h), (x + nw, y + h), (x + nw, y + h - nh), (x, y + h - nh)]
        rad = [r, r, r, r, nr, r]
    return rounded_polygon(pts, rad)

def tab_path(x, y, w, h, tab_w, tab_h, r=28, inner_r=20, corner="tl"):
    """Single silhouette: rect whose top edge sits at y+tab_h with a tab of width tab_w rising to y (tl or tr)."""
    if corner == "tl":
        pts = [(x, y), (x + tab_w, y), (x + tab_w, y + tab_h), (x + w, y + tab_h), (x + w, y + h), (x, y + h)]
        rad = [r, r, inner_r, r, r, r]
    else:
        pts = [(x, y + tab_h), (x + w - tab_w, y + tab_h), (x + w - tab_w, y), (x + w, y), (x + w, y + h), (x, y + h)]
        rad = [r, inner_r, r, r, r, r]
    return rounded_polygon(pts, rad)

def circle_path(cx, cy, r):
    k = K * r
    return (f"M {fmt(cx + r)} {fmt(cy)} C {fmt(cx + r)} {fmt(cy + k)} {fmt(cx + k)} {fmt(cy + r)} {fmt(cx)} {fmt(cy + r)} "
            f"C {fmt(cx - k)} {fmt(cy + r)} {fmt(cx - r)} {fmt(cy + k)} {fmt(cx - r)} {fmt(cy)} "
            f"C {fmt(cx - r)} {fmt(cy - k)} {fmt(cx - k)} {fmt(cy - r)} {fmt(cx)} {fmt(cy - r)} "
            f"C {fmt(cx + k)} {fmt(cy - r)} {fmt(cx + r)} {fmt(cy - k)} {fmt(cx + r)} {fmt(cy)} Z")

def band_path(pts, thickness):
    """Ribbon band: cubic polyline pts (1+3k points) is the top edge; the bottom edge is the same curve shifted down."""
    top = pts
    bottom = [(px, py + thickness) for px, py in pts][::-1]
    def run(ps):
        return [f"C {pt(ps[i])} {pt(ps[i + 1])} {pt(ps[i + 2])}" for i in range(1, len(ps), 3)]
    return " ".join([f"M {pt(top[0])}"] + run(top) + [f"L {pt(bottom[0])}"] + run(bottom) + ["Z"])

def tx_path(d, s, ox, oy):
    """Scale+translate an absolute M/L/C/Z path string (so the output never needs a transform attribute)."""
    out, i, toks = [], 0, d.replace(",", " ").split()
    while i < len(toks):
        t = toks[i]
        if t.isalpha():
            out.append(t); i += 1
        else:
            x, y = float(toks[i]), float(toks[i + 1])
            out.append(f"{fmt(x * s + ox)} {fmt(y * s + oy)}"); i += 2
    return " ".join(out)

def path_bounds(d, pad=0.0):
    nums = [float(t) for t in d.replace(",", " ").split() if not t.isalpha()]
    xs, ys = nums[0::2], nums[1::2]
    return min(xs) - pad, min(ys) - pad, max(xs) + pad, max(ys) + pad

def poly(ps):
    return "M " + " L ".join(pt(p) for p in ps) + " Z"

# ---------------------------------------------------------------- element constructors
def T(name, x, y, w, text, size, weight=400, color="#000000", lh=None, ls=0.0, align="left", case=None, opacity=1.0):
    lh = lh or round(size * 1.3)
    shown = text.upper() if case == "upper" else text
    lines = wrap(shown, size, weight, w, ls)
    return {"type": "text", "name": name, "x": x, "y": y, "w": w, "text": text, "lines": lines, "size": size,
            "weight": weight, "color": color, "lh": lh, "ls": ls, "align": align, "case": case,
            "opacity": opacity, "h": len(lines) * lh}

def R(name, x, y, w, h, fill, rx=0, opacity=1.0, stroke=None, sw=0):
    return {"type": "rect", "name": name, "x": x, "y": y, "w": w, "h": h, "rx": rx, "fill": fill,
            "opacity": opacity, "stroke": stroke, "sw": sw}

def C(name, cx, cy, r, fill, opacity=1.0, stroke=None, sw=0):
    return {"type": "circle", "name": name, "cx": cx, "cy": cy, "r": r, "fill": fill, "opacity": opacity,
            "stroke": stroke, "sw": sw}

def PATH(name, d, fill=None, stroke=None, sw=0, cap="round", join="round", opacity=1.0):
    return {"type": "path", "name": name, "d": d, "fill": fill, "stroke": stroke, "sw": sw, "cap": cap,
            "join": join, "opacity": opacity}

def LINE(name, x1, y1, x2, y2, stroke, sw=1, opacity=1.0):
    return PATH(name, f"M {fmt(x1)} {fmt(y1)} L {fmt(x2)} {fmt(y2)}", stroke=stroke, sw=sw, cap="butt", opacity=opacity)

def G(name, children):
    return {"type": "group", "name": name, "children": children}

def LIN(x1, y1, x2, y2, stops):
    return {"type": "linear", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "stops": stops}

# ---------------------------------------------------------------- brand graphics
# Wordmark traced from the brand board: heavy round-capped strokes (27 % of cap height) in a 100-high box.
# A = arch with a stepped left foot, apex right of centre; F = large rounded shoulder, mid bar at 50 %;
# Q = wide rounded rectangle (1.39:1) with a short down-right tail. Visual bbox ≈ 0..484 x 0..117 (tail).
WM_SW = 27
WORDMARK_W = 484
_q_body = rounded_polygon([(340.5, 13.5), (452.5, 13.5), (452.5, 86.5), (340.5, 86.5)], 22.5)
WORDMARK_LETTERS = {
    "A": "M 22 82 L 32 62 L 66 62 L 98 15 L 162 86",
    "F": "M 198.5 86.5 L 198.5 35.5 C 198.5 23.6 208.1 14 220 14 L 304.5 14 M 198.5 50 L 286 50",
    "Q": _q_body + " M 438 82 L 470 104",
}

def wordmark(x, y, h, color, name="Wordmark-AFQ"):
    s = h / 100.0
    kids = [PATH(f"Letter-{k}", tx_path(d, s, x, y), stroke=color, sw=WM_SW * s) for k, d in WORDMARK_LETTERS.items()]
    return G(name, kids)

def lockup(x, y, h, color, tag_color=None, name="Logo-Lockup"):
    """Wordmark + 'ENERGY. ENGINEERED.' tracked to the wordmark width (as on the board). Returns (group, total height)."""
    tag_color = tag_color or color
    tag_size = max(11, round(h * 0.19))
    text = "ENERGY. ENGINEERED."
    target = WORDMARK_W * h / 100.0
    base = text_width(text, tag_size, 500, 0)
    ls = min(0.6, max(0.14, (target - base) / (tag_size * (len(text) - 1))))
    tag_y = y + h + max(12, round(h * 0.2))
    tag = T("Tagline", x, tag_y, 1200, text, tag_size, 500, tag_color, lh=round(tag_size * 1.3), ls=round(ls, 3))
    return G(name, [wordmark(x, y, h, color), tag]), (tag_y + tag["h"]) - y

def ribbon(name, pts, thickness, teal_fill=None, teal=True, orange=True):
    """Three readable layers like the board: teal band twisting under, a continuous orange edge, the lime band on top.
    `pts` is the lime band's TOP edge; the teal underside bottoms out at y + 1.45 * thickness."""
    kids = []
    if teal:
        kids.append(PATH("Ribbon-Teal", band_path([(px + 40, py + thickness * 0.55) for px, py in pts], thickness * 0.90),
                         fill=teal_fill or P["teal"]))
    if orange:
        kids.append(PATH("Ribbon-Orange", band_path([(px, py + thickness - 2) for px, py in pts], 10), fill=P["orange"]))
    x0, x1 = pts[0][0], pts[-1][0]
    fill = LIN(x0, 0, x1, 0, [(0, P["lime_deep"], 1), (0.35, P["lime"], 1), (0.55, P["lime_pale"], 1), (0.75, P["lime"], 1), (1, P["lime_deep"], 1)])
    kids.append(PATH("Ribbon-Lime", band_path(pts, thickness), fill=fill))
    return G(name, kids)

def dark_ribbon_fill(pts):
    return LIN(pts[0][0], 0, pts[-1][0], 0, [(0, P["teal_mid"], 1), (1, P["teal_soft"], 1)])

# Icons in a 48x48 box, stroke 3 (scaled). Only M/L/C/Z.
def _rr(x, y, w, h, r):
    return rounded_polygon([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], r)

ICONS = {
    "pv-module": [_rr(5, 10, 38, 28, 3), "M 17.7 10 L 17.7 38 M 30.3 10 L 30.3 38 M 5 24 L 43 24"],
    "battery": [_rr(5, 14, 32, 20, 3), _rr(37, 20, 5, 8, 1.5), "M 23 17 L 17 25 L 22 25 L 19 31 L 25 23 L 20 23 Z"],
    "inverter": [_rr(5, 9, 38, 30, 3), "M 11 24 C 14 24 14 17 18 17 C 22 17 22 31 26 31 C 30 31 30 24 37 24", "M 5 17 L 11 17"],
    "infrastructure": ["M 24 5 L 12 43 M 24 5 L 36 43 M 15 33 L 33 33 M 19 21 L 29 21 M 8 13 L 40 13 M 8 13 L 11 8 M 40 13 L 37 8"],
    "sun": [circle_path(24, 24, 8), "M 24 5 L 24 10 M 24 38 L 24 43 M 5 24 L 10 24 M 38 24 L 43 24 M 10.6 10.6 L 14.1 14.1 M 33.9 33.9 L 37.4 37.4 M 10.6 37.4 L 14.1 33.9 M 33.9 14.1 L 37.4 10.6"],
    "continuous": [circle_path(24, 24, 18), "M 24 13 L 24 24 L 32 29"],
    "off-grid": ["M 5 40 L 24 9 L 43 40 Z M 24 40 L 24 30 L 29 40", "M 11 40 L 37 40"],
    "construction": ["M 10 43 L 10 13 L 40 13 M 10 19 L 20 13 M 34 13 L 34 24 M 30 24 L 38 24 M 34 24 L 34 28 C 34 31 30 31 30 28", "M 5 43 L 15 43"],
    "clipboard": [_rr(10, 8, 28, 36, 3), _rr(18, 4, 12, 7, 2), "M 16 27 L 21 32 L 32 20"],
    "boxes": [_rr(5, 26, 18, 16, 2), _rr(25, 26, 18, 16, 2), _rr(15, 8, 18, 16, 2)],
    "factory": ["M 5 43 L 5 23 L 15 29 L 15 23 L 25 29 L 25 23 L 35 29 L 35 9 L 43 9 L 43 43 Z", "M 12 36 L 16 36 M 22 36 L 26 36 M 32 36 L 36 36"],
    "shield": ["M 24 5 L 40 11 L 40 23 C 40 33 33 40 24 43 C 15 40 8 33 8 23 L 8 11 Z", "M 17 24 L 22 29 L 31 19"],
    "badge": [circle_path(24, 18, 11), "M 17 27 L 14 43 L 24 38 L 34 43 L 31 27"],
    "document": ["M 11 5 L 29 5 L 39 15 L 39 43 L 11 43 Z M 29 5 L 29 15 L 39 15", "M 17 25 L 33 25 M 17 32 L 29 32"],
    "team": [circle_path(17, 15, 6), circle_path(32, 17, 5), "M 5 41 C 5 31 10 27 17 27 C 24 27 29 31 29 41 Z", "M 31 41 C 36 41 43 41 43 41 C 43 34 40 29 33 29"],
    "phone": ["M 14 7 C 14 5 15 5 17 5 L 21 5 L 24 13 L 20 16 C 22 22 26 26 32 28 L 35 24 L 43 27 L 43 31 C 43 33 43 34 41 34 C 26 34 14 22 14 7 Z"],
    "mail": [_rr(5, 10, 38, 28, 3), "M 5 13 L 24 27 L 43 13"],
    "pin": ["M 24 43 C 24 43 9 28 9 18 C 9 10 16 4 24 4 C 32 4 39 10 39 18 C 39 28 24 43 24 43 Z", circle_path(24, 18, 5)],
}

def icon(name, key, x, y, size, color, sw=None):
    s = size / 48.0
    sw = sw or 3 * s
    return G(f"Icon-{key}" if name is None else name,
             [PATH(f"Icon-{key}-{i + 1}", tx_path(d, s, x, y), stroke=color, sw=sw) for i, d in enumerate(ICONS[key])])

def photo_slot(name, x, y, w, h, r=40, notch=None, dark=False, art="solar"):
    """Photo placeholder: ONE shape (set an image fill on it in Figma/Illustrator) + flat vector art inside its bounds.
    dark=True (teal pages): lighter gradient + 2 px lime hairline so the frame reads against the background."""
    if dark:
        base = PATH(name + "__set-image-fill", rect_path(x, y, w, h, r, notch),
                    fill=LIN(0, y, 0, y + h, [(0, P["teal_mid"], 1), (1, P["teal_soft"], 1)]), stroke=P["lime"], sw=2, cap="butt")
    else:
        base = PATH(name + "__set-image-fill", rect_path(x, y, w, h, r, notch),
                    fill=LIN(0, y, 0, y + h, [(0, P["teal_deep"], 1), (1, P["teal_mid"], 1)]))
    nrect = None
    if notch:
        nw, nh, c = notch["w"], notch["h"], notch["corner"]
        nx = x if c in ("tl", "bl") else x + w - nw
        ny = y if c in ("tl", "tr") else y + h - nh
        nrect = (nx - 24, ny - 24, nx + nw + 24, ny + nh + 24)
    def clear(x0, y0, x1, y1):
        return not nrect or x1 < nrect[0] or x0 > nrect[2] or y1 < nrect[1] or y0 > nrect[3]
    art_els = []
    sun_left = not (notch and notch["corner"] == "tl")
    sr = min(w, h) * 0.085
    scx = x + (w * 0.24 if sun_left else w * 0.76)
    scy = y + h * 0.26
    art_els.append(C("Sun-Glow", scx, scy, sr * 1.9, P["orange"], opacity=0.18))
    art_els.append(C("Sun", scx, scy, sr, P["orange"]))
    y1, y2 = y + h * 0.42, y + h * 0.60
    base_y = y2 + h * 0.07
    far = [(x, base_y), (x + w * 0.18, y1 + h * 0.06), (x + w * 0.33, y1 + h * 0.11), (x + w * 0.52, y1),
           (x + w * 0.70, y1 + h * 0.10), (x + w * 0.86, y1 + h * 0.04), (x + w, y1 + h * 0.12), (x + w, base_y)]
    near = [(x, base_y), (x + w * 0.12, y2 - h * 0.05), (x + w * 0.30, y2 + h * 0.02), (x + w * 0.46, y2 - h * 0.08),
            (x + w * 0.64, y2 + h * 0.01), (x + w * 0.80, y2 - h * 0.04), (x + w, y2 + h * 0.03), (x + w, base_y)]
    art_els.append(PATH("Mountains-Far", poly(far), fill=P["teal_soft"], opacity=0.55))
    art_els.append(PATH("Mountains-Near", poly(near), fill=P["teal"], opacity=0.9))
    inset = 56
    if art == "solar":
        panels = []
        for ri, (fy, fh, n) in enumerate([(0.655, 0.065, 7), (0.745, 0.075, 6), (0.845, 0.09, 5)]):
            py0, ph = y + h * fy, h * fh
            gap = 14 + ri * 6
            pw = (w - 2 * inset - gap * (n - 1)) / n
            skew = ph * 0.22
            for i in range(n):
                px0 = x + inset + i * (pw + gap)
                pts = [(px0 + skew, py0), (px0 + pw + skew, py0), (px0 + pw, py0 + ph), (px0, py0 + ph)]
                if not clear(px0, py0, px0 + pw + skew, py0 + ph):
                    continue
                panels.append(PATH(f"Panel-{ri + 1}-{i + 1}", rounded_polygon(pts, 3), fill=P["charcoal"], stroke=P["lime"], sw=1.5, opacity=0.95))
                panels.append(PATH(f"Panel-{ri + 1}-{i + 1}-line", f"M {fmt(px0 + skew + pw / 2)} {fmt(py0)} L {fmt(px0 + pw / 2)} {fmt(py0 + ph)}",
                                   stroke=P["lime"], sw=1, cap="butt", opacity=0.35))
        art_els.append(G("Solar-Array", panels))
    elif art == "storage":
        # row of battery cabinets on a plinth
        cabs = []
        n = 4
        gap = 28
        cw_ = (w - 2 * inset - gap * (n - 1)) / n
        ch_ = h * 0.30
        cy0 = y + h - inset - ch_
        cabs.append(R("Plinth", x + inset - 12, cy0 + ch_ - 6, w - 2 * inset + 24, 12, P["teal_deep"], rx=4, opacity=0.9))
        for i in range(n):
            cx0 = x + inset + i * (cw_ + gap)
            if not clear(cx0, cy0, cx0 + cw_, cy0 + ch_):
                continue
            cabs.append(PATH(f"Cabinet-{i + 1}", _rr(cx0, cy0, cw_, ch_, 10), fill=P["charcoal"], stroke=P["lime"], sw=1.5, opacity=0.95))
            for k in range(3):
                vy = cy0 + ch_ * (0.30 + k * 0.14)
                cabs.append(LINE(f"Cabinet-{i + 1}-vent-{k + 1}", cx0 + cw_ * 0.18, vy, cx0 + cw_ * 0.82, vy, P["lime"], 1.5, opacity=0.35))
            cabs.append(C(f"Cabinet-{i + 1}-led", cx0 + cw_ * 0.5, cy0 + ch_ * 0.14, 4, P["lime"]))
            cabs.append(LINE(f"Cabinet-{i + 1}-door", cx0 + cw_ * 0.5, cy0 + ch_ * 0.24, cx0 + cw_ * 0.5, cy0 + ch_ * 0.9, P["lime"], 1, opacity=0.25))
        art_els.append(G("Battery-Cabinets", cabs))
    else:  # grid: pylons with sagging cables, scaled so the arms stay inside the slot
        grid = []
        n = 3
        s = min(h * 0.60 / 38.0, (w - 2 * inset) / (n * 32 + (n - 1) * 40))  # icon spans x 8..40, y 5..43
        half = 16 * s
        ph = 38 * s
        py0 = y + h - inset * 0.6 - ph
        first, last = x + inset + half, x + w - inset - half
        tops = []
        for i in range(n):
            cx0 = first + i * (last - first) / (n - 1)
            d = tx_path(ICONS["infrastructure"][0], s, cx0 - 24 * s, py0 - 5 * s)
            grid.append(PATH(f"Pylon-{i + 1}", d, stroke=P["lime"], sw=2.5, opacity=0.85))
            tops.append((cx0 - half, py0 + 8 * s, cx0 + half))
        for i in range(n - 1):
            lx, ay, _ = tops[i][2], tops[i][1], None
            rx_, by = tops[i + 1][0], tops[i + 1][1]
            span = rx_ - lx
            sag = span * 0.12
            grid.append(PATH(f"Cable-{i + 1}", f"M {fmt(lx)} {fmt(ay)} C {fmt(lx + span * 0.3)} {fmt(ay + sag)} {fmt(rx_ - span * 0.3)} {fmt(by + sag)} {fmt(rx_)} {fmt(by)}",
                             stroke=P["lime"], sw=1.5, cap="butt", opacity=0.6))
        art_els.append(G("Transmission-Line", grid))
    # hard guarantee: placeholder art never leaves the slot (there is no clipping in the SVG)
    def check(e):
        if e["type"] == "group":
            for c in e["children"]:
                check(c)
            return
        if e["type"] == "path":
            bx0, by0, bx1, by1 = path_bounds(e["d"], (e.get("sw") or 0) / 2)
        elif e["type"] == "rect":
            bx0, by0, bx1, by1 = e["x"], e["y"], e["x"] + e["w"], e["y"] + e["h"]
        else:
            bx0, by0, bx1, by1 = e["cx"] - e["r"], e["cy"] - e["r"], e["cx"] + e["r"], e["cy"] + e["r"]
        if bx0 < x - 0.5 or by0 < y - 0.5 or bx1 > x + w + 0.5 or by1 > y + h + 0.5:
            raise ValueError(f"{name}: art element {e['name']} leaves the slot: {(round(bx0), round(by0), round(bx1), round(by1))} vs {(x, y, x + w, y + h)}")
    for e in art_els:
        check(e)
    return G(name, [base, G("Placeholder-Art (delete after placing photo)", art_els)])

# ---------------------------------------------------------------- shared slide parts
def header(dark, eyebrow_color=None, eyebrow_opacity=None):
    col = P["cream"] if dark else P["teal_ink"]
    sub = eyebrow_color or (P["cream"] if dark else P["muted"])
    lock, _ = lockup(M, 66, 56, col)
    eyebrow = T("Eyebrow", W - M - 420, 84, 420, "Corporate Profile 2026", 15, 500, sub, lh=20, ls=0.22, align="right",
                case="upper", opacity=eyebrow_opacity if eyebrow_opacity is not None else (0.85 if dark else 1.0))
    return G("Header", [lock, eyebrow])

def footer(section, n, dark, color=None, rule_opacity=None, text_opacity=None):
    col = color or (P["cream"] if dark else P["muted"])
    rule = LINE("Footer-Rule", M, FOOT_Y, W - M, FOOT_Y, color or (P["cream"] if dark else P["line"]), 1,
                opacity=rule_opacity if rule_opacity is not None else (0.25 if dark else 1.0))
    top = text_opacity if text_opacity is not None else (0.75 if dark else 1.0)
    left = T("Footer-Section", M, 1822, 600, section, 16, 400, col, lh=22, opacity=top)
    right = T("Footer-Page", W - M - 200, 1822, 200, f"{n:02d} / 08", 16, 500, col, lh=22, align="right", opacity=top)
    return G("Footer", [rule, left, right])

def title(text, dark, y=300, size=76, color=None):
    return T("Title", M, y, CW, text, size, 300, color or (P["cream"] if dark else P["teal"]), lh=round(size * 1.1), ls=-0.02)

def subtitle(text, dark, y, w=880, color=None, opacity=None):
    return T("Subtitle", M, y, w, text, 26, 400, color or (P["cream"] if dark else P["muted"]), lh=38,
             opacity=opacity if opacity is not None else (0.85 if dark else 1.0))

# ---------------------------------------------------------------- slides
def slide_cover():
    els = [R("Background", 0, 0, W, H, P["cream"])]
    lock, _ = lockup(M, 96, 96, P["teal_ink"])
    els.append(lock)
    els.append(T("Eyebrow", W - M - 420, 132, 420, "Corporate Profile 2026", 18, 500, P["muted"], lh=24, ls=0.22, align="right", case="upper"))
    head = T("Headline", M, 372, CW, "AFAQ for Energy\n& Integrated Business", 92, 300, P["teal"], lh=100, ls=-0.025)
    els.append(head)
    y = 372 + head["h"] + 40
    els.append(R("Accent-Rule", M, y, 64, 6, P["orange"], rx=3))
    slog = T("Slogan", M, y + 26, CW, "Innovating today, sustaining tomorrow", 40, 300, P["teal"], lh=50)
    els.append(slog)
    y = y + 26 + slog["h"] + 18
    scope = T("Scope", M, y, 720, "Solar power and energy storage in the Sultanate of Oman", 24, 400, P["muted"], lh=34)
    els.append(scope)
    py = y + scope["h"] + 48
    ph = 1480 - py
    notch = {"corner": "tr", "w": 312, "h": 132, "r": 24}
    els.append(photo_slot("Photo-Hero", M, py, CW, ph, 40, notch))
    tab_x, tab_y, tab_w, tab_h = W - M - 296, py, 296, 116
    els.append(G("Label-Tab", [
        R("Label-Tab-Shape", tab_x, tab_y, tab_w, tab_h, P["orange"], rx=24),
        T("Label-Tab-Text", tab_x + 28, tab_y + 24, tab_w - 56, "SOLAR\nSTORAGE\nELECTRICAL", 16, 500, P["teal_ink"], lh=22, ls=0.18),
    ]))
    pts = [(-60, 1690), (160, 1700), (300, 1540), (520, 1560), (740, 1580), (820, 1760), (1140, 1690)]
    els.append(ribbon("Ribbon", pts, 118))
    return {"name": "01 Cover", "bg": P["cream"], "elements": els}

def slide_about():
    dark = True
    els = [R("Background", 0, 0, W, H, P["teal"]), header(dark)]
    t = title("About AFAQ", dark)
    els.append(t)
    els.append(R("Accent-Rule", M, 300 + t["h"] + 22, 80, 6, P["lime"], rx=3))
    y = 300 + t["h"] + 22 + 6 + 44
    paras = [
        "AFAQ for Energy & Integrated Business is an Omani company based in Muscat. It works in solar power, energy storage and the electrical systems that go with them.",
        "The company designs photovoltaic systems, supplies their components, installs them and brings them into operation, at sizes ranging from building systems to project plants.",
        "AFAQ works directly with facility owners, and with contractors and developers inside their own projects.",
    ]
    for i, p in enumerate(paras):
        el = T(f"Body-{i + 1}", M, y, CW, p, 26, 400, P["cream"], lh=40, opacity=0.9)
        els.append(el)
        y += el["h"] + 26
    py = y + 34
    ph = 1744 - py
    notch = {"corner": "bl", "w": 324, "h": 150, "r": 24}
    els.append(photo_slot("Photo-Site", M, py, CW, ph, 40, notch, dark=True, art="storage"))
    tab_w, tab_h = 308, 134
    tab_x, tab_y = M, py + ph - tab_h
    els.append(G("Services-Tab", [
        R("Services-Tab-Shape", tab_x, tab_y, tab_w, tab_h, P["lime"], rx=24),
        T("Services-Tab-Text", tab_x + 28, tab_y + 22, tab_w - 56, "SOLAR\nSTORAGE\nELECTRICAL\nENGINEERING", 15, 500, P["teal"], lh=22, ls=0.18),
    ]))
    els.append(footer("About AFAQ", 2, dark))
    return {"name": "02 About AFAQ", "bg": P["teal"], "elements": els}

def slide_components():
    dark = False
    els = [R("Background", 0, 0, W, H, P["cream"]), header(dark)]
    t = title("System components", dark)
    els.append(t)
    sub = subtitle("A photovoltaic system is built from four components. AFAQ holds a direct supply agreement with a main supplier for each.", dark, 300 + t["h"] + 20)
    els.append(sub)
    comps = [
        ("01", "PV modules", "Selected according to the mounting area available and the conditions on site.", "Main suppliers", "AACE · Ronma", "pv-module"),
        ("02", "Battery energy storage", "Sized on the loads to be covered and the autonomy required.", "Main supplier", "Goshin", "battery"),
        ("03", "Inverters and power conversion", "Selected according to the array configuration and the connection requirements of the grid operator.", "Main supplier", "Star Charge", "inverter"),
        ("04", "Plant infrastructure", "Mounting structures, foundations, DC and AC cabling, and connection and protection panels, specified to suit the site.", None, None, "infrastructure"),
    ]
    y = 300 + t["h"] + 20 + sub["h"] + 56
    PAD = 36
    def card_h(note, lab):
        n = T("m", M + 40, 0, 640, note, 22, 400, "#000000", lh=32)
        return 126 + n["h"] + (14 + 24 + 30 if lab else 0) + PAD
    heights = [card_h(n, l) for _, _, n, l, _, _ in comps]
    gap = round(min(48, max(24, (1744 - y - sum(heights)) / (len(comps) - 1))))
    for i, (num, name, note, lab, sup, ic) in enumerate(comps):
        ch = heights[i]
        kids = [R("Card-Shape", M, y, CW, ch, P["white"], rx=28),
                T("Number", M + 40, y + 34, 80, num, 22, 600, P["orange_deep"], lh=28),
                C("Icon-Disc", W - M - 40 - 44, y + 34 + 44, 44, P["lime"]),
                icon("Icon", ic, W - M - 40 - 44 - 24, y + 34 + 44 - 24, 48, P["teal"]),
                T("Card-Title", M + 40, y + 74, 640, name, 32, 600, P["teal"], lh=40)]
        note_el = T("Card-Note", M + 40, y + 126, 640, note, 22, 400, P["muted"], lh=32)
        kids.append(note_el)
        if lab:
            ly = y + 126 + note_el["h"] + 14
            kids.append(T("Supplier-Label", M + 40, ly, 400, lab, 13, 500, P["muted"], lh=18, ls=0.16, case="upper"))
            kids.append(T("Supplier", M + 40, ly + 24, 600, sup, 22, 500, P["teal"], lh=30))
        els.append(G(f"Card-{num}", kids))
        y += ch + gap
    els.append(footer("System components", 3, dark))
    return {"name": "03 System components", "bg": P["cream"], "elements": els}

def slide_scope():
    dark = False
    els = [R("Background", 0, 0, W, H, P["lime"]), header(False, eyebrow_color=P["teal"], eyebrow_opacity=0.8)]
    t = title("Scope of work", dark)
    els.append(t)
    sub = subtitle("The project sets the scope, from supply alone to full operation.", dark, 300 + t["h"] + 20, color=P["teal"], opacity=0.85)
    els.append(sub)
    steps = [
        ("01", "Study and design", "Load analysis and consumption data, a site survey, system sizing and placement, and the expected annual yield.", "A report covering system capacity, expected annual yield and estimated cost."),
        ("02", "Supply", "PV modules, batteries, inverters and electrical equipment, with manufacturer warranties.", "A component list with specifications, source and warranty terms."),
        ("03", "Installation and connection", "Installation, electrical works, and grid-tied, off-grid or hybrid connection.", "A working system and a testing and commissioning record."),
        ("04", "Operation and monitoring", "Performance monitoring and maintenance under an operation and maintenance contract.", "A performance report comparing actual output against the design figure."),
    ]
    y = 300 + t["h"] + 20 + sub["h"] + 60
    cx, tx, tw = M + 28, M + 92, CW - 92
    def step_height(body, deliv):
        b = T("m", tx, 0, tw, body, 24, 400, "#000000", lh=34)
        dl = T("m", tx + 28, 0, tw - 56, deliv, 20, 400, "#000000", lh=28)
        return 56 + b["h"] + 18 + (44 + dl["h"] + 22)
    natural = sum(step_height(b, d) for _, _, b, d in steps)
    gap = round(max(44, (1744 - y - natural) / (len(steps) - 1) - 8))
    step_tops = []
    for num, name, body, deliv in steps:
        step_tops.append(y)
        kids = [C("Node", cx, y + 22, 28, P["teal"]),
                T("Node-Number", cx - 28, y + 22 - 13, 56, num, 19, 600, P["lime"], lh=26, align="center"),
                T("Step-Title", tx, y, tw, name, 32, 600, P["teal"], lh=44)]
        b = T("Step-Body", tx, y + 56, tw, body, 24, 400, P["teal"], lh=34, opacity=0.85)
        kids.append(b)
        by = y + 56 + b["h"] + 18
        dl = T("Deliverable-Text", tx + 28, by + 44, tw - 56, deliv, 20, 400, P["teal"], lh=28)
        bh = 44 + dl["h"] + 22
        kids.insert(3, R("Deliverable-Box", tx, by, tw, bh, P["cream"], rx=18))
        kids.append(T("Deliverable-Label", tx + 28, by + 18, 300, "Deliverable", 13, 500, P["orange_deep"], lh=18, ls=0.16, case="upper"))
        kids.append(dl)
        els.append(G(f"Step-{num}", kids))
        y = round(by + bh + gap)
    conns = [LINE(f"Connector-{i + 1}", cx, step_tops[i] + 22 + 36, cx, step_tops[i + 1] + 22 - 36, P["teal"], 2, opacity=0.35)
             for i in range(len(step_tops) - 1)]
    els.insert(2, G("Connectors", conns))
    els.append(footer("Scope of work", 4, False, color=P["teal"], rule_opacity=0.25, text_opacity=0.8))
    return {"name": "04 Scope of work", "bg": P["lime"], "elements": els}

def slide_ways():
    dark = True
    els = [R("Background", 0, 0, W, H, P["teal"]), header(dark)]
    t = title("Ways of working", dark)
    els.append(t)
    cards = [
        ("01", "Supply and installation for projects", "One party responsible for design, supply, installation and commissioning.", "clipboard"),
        ("02", "Component supply", "Supply to the specification and quantities of the project, for contractors and installation companies.", "boxes"),
    ]
    y = 300 + t["h"] + 72
    ch, tab_w, tab_h = 312, 168, 52
    for num, name, body, ic in cards:
        # lime folder tab with the board's concave 22 px fillet where it meets the body; 2 px under the body hides the seam
        tab = PATH("Tab-Fill", rounded_polygon(
            [(M, y), (M + tab_w, y), (M + tab_w, y + tab_h), (M + tab_w + 22, y + tab_h), (M + tab_w + 22, y + tab_h + 2), (M, y + tab_h + 2)],
            [26, 26, 22, 0, 0, 0]), fill=P["lime"])
        body_shape = PATH("Card-Body", rounded_polygon(
            [(M, y + tab_h), (M + CW, y + tab_h), (M + CW, y + ch), (M, y + ch)], [0, 32, 32, 32]), fill=P["teal_mid"])
        tt = T("Card-Title", M + 48, y + 112, 640, name, 32, 600, P["cream"], lh=40)
        kids = [tab, body_shape,
                T("Number", M, y + 13, tab_w, num, 20, 600, P["teal"], lh=26, align="center"),
                tt,
                T("Card-Body-Text", M + 48, y + 112 + tt["h"] + 16, 680, body, 24, 400, P["cream"], lh=34, opacity=0.85),
                icon("Icon", ic, W - M - 48 - 72, y + 146, 72, P["lime"], sw=4)]
        els.append(G(f"Card-{num}", kids))
        y += ch + 44
    pts = [(-60, 1310), (200, 1290), (380, 1490), (600, 1480), (820, 1470), (900, 1280), (1140, 1330)]
    els.append(ribbon("Ribbon", pts, 190, teal_fill=dark_ribbon_fill(pts)))
    els.append(footer("Ways of working", 5, dark))
    return {"name": "05 Ways of working", "bg": P["teal"], "elements": els}

def slide_uses():
    dark = False
    els = [R("Background", 0, 0, W, H, P["cream"]), header(dark)]
    t = title("Where the\nsystems are used", dark)
    els.append(t)
    sub = subtitle("The pattern of consumption shapes the system more than the type of business does.", dark, 300 + t["h"] + 20)
    els.append(sub)
    blocks = [
        ("Sites that consume\nduring the day", "Offices, retail centres, hotels, factories, schools and residential compounds. Their heaviest load falls within sunlight hours.", "sun"),
        ("Sites with continuous loads", "Hospitals, cold stores, production lines and data centres. The system works alongside the backup already in place, cutting generator running hours and fuel use.", "continuous"),
        ("Sites away from the grid", "Farms, irrigation pumps, camps and work sites that run on diesel.", "off-grid"),
        ("Projects under construction", "Contractors and developers delivering the energy scope within a live project.", "construction"),
    ]
    y0 = 300 + t["h"] + 20 + sub["h"] + 56
    cw, gap = (CW - 30) / 2, 30
    chh = 440
    titles = [T("m", 0, 0, cw - 80, n, 28, 600, "#000000", lh=36) for n, _, _ in blocks]
    title_h = max(tt["h"] for tt in titles)  # shared so side-by-side bodies share a baseline
    for i, (name, body, ic) in enumerate(blocks):
        x = M + (i % 2) * (cw + gap)
        y = y0 + (i // 2) * (chh + gap)
        kids = [R("Card-Shape", x, y, cw, chh, P["white"], rx=28),
                C("Icon-Disc", x + 40 + 44, y + 40 + 44, 44, P["lime"]),
                icon("Icon", ic, x + 40 + 44 - 24, y + 40 + 44 - 24, 48, P["teal"]),
                T("Card-Title", x + 40, y + 156, cw - 80, name, 28, 600, P["teal"], lh=36),
                T("Card-Body", x + 40, y + 156 + title_h + 14, cw - 80, body, 21, 400, P["muted"], lh=31)]
        els.append(G(f"Card-{i + 1}", kids))
    pts = [(-60, 1600), (200, 1580), (380, 1660), (600, 1650), (820, 1640), (900, 1560), (1140, 1600)]
    els.append(ribbon("Ribbon", pts, 94))
    els.append(footer("Where the systems are used", 6, dark))
    return {"name": "06 Where the systems are used", "bg": P["cream"], "elements": els}

def slide_brings():
    dark = True
    els = [R("Background", 0, 0, W, H, P["teal"]), header(dark)]
    t = title("What AFAQ brings", dark)
    els.append(t)
    items = [
        ("Supply from a factory in Oman", "AACE modules are manufactured in Oman, which shortens supply time compared with importing.", "factory"),
        ("Warranty handled inside Oman", "AFAQ processes module warranty claims locally, without sending them to a manufacturer abroad.", "shield"),
        ("In-country value", "Modules made in Oman support local content requirements in tenders and government projects.", "badge"),
        ("Direct supply agreements", "Written agreements with module, battery and inverter suppliers, covering availability and manufacturer warranties.", "document"),
        ("Delivery team", "An engineering team for design and supervision, and a field crew for installation and commissioning.", "team"),
    ]
    y = 300 + t["h"] + 64
    for i, (name, body, ic) in enumerate(items):
        kids = [T("Number", M, y + 8, 60, f"{i + 1:02d}", 20, 600, P["lime"], lh=26),
                icon("Icon", ic, W - M - 44, y + 2, 44, P["lime"], sw=2.6)]
        tt = T("Item-Title", M + 84, y, 760, name, 32, 600, P["cream"], lh=40)
        kids.append(tt)
        b = T("Item-Body", M + 84, y + tt["h"] + 8, 760, body, 22, 400, P["cream"], lh=32, opacity=0.8)
        kids.append(b)
        ly = y + tt["h"] + 8 + b["h"] + 26
        if i < len(items) - 1:
            kids.append(LINE("Divider", M, ly, W - M, ly, P["cream"], 1, opacity=0.15))
        els.append(G(f"Item-{i + 1:02d}", kids))
        y = ly + 27
    py = y + 30
    els.append(photo_slot("Photo-Strip", M, py, CW, 1744 - py, 32, dark=True, art="grid"))
    els.append(footer("What AFAQ brings", 7, dark))
    return {"name": "07 What AFAQ brings", "bg": P["teal"], "elements": els}

def slide_contact():
    dark = True
    els = [R("Background", 0, 0, W, H, P["teal"]), header(dark)]
    slog = T("Slogan", M, 340, CW, "Innovating today,\nsustaining tomorrow", 80, 300, P["lime"], lh=90, ls=-0.02)
    els.append(slog)
    y = 340 + slog["h"] + 48
    els.append(T("Contact-Title", M, y, CW, "Contact", 26, 500, P["cream"], lh=34, opacity=0.7))
    y += 34 + 36
    rows = [("Phone", "+968 9190 7789", "phone"), ("Email", "afaq@gmail.com", "mail"), ("Address", "Al Khuwair, behind Zakher Mall, Muscat", "pin")]
    for lab, val, ic in rows:
        kids = [C("Icon-Disc", M + 34, y + 34, 34, P["lime"]),
                icon("Icon", ic, M + 34 - 16, y + 34 - 16, 32, P["teal"], sw=2.2),
                T("Label", M + 100, y, 500, lab, 14, 500, P["cream"], lh=20, ls=0.16, case="upper", opacity=0.6),
                T("Value", M + 100, y + 26, 820, val, 32, 500, P["cream"], lh=42)]
        els.append(G(f"Contact-{lab}", kids))
        y += 68 + 48
    y += 40
    els.append(LINE("Rule", M, y, W - M, y, P["cream"], 1, opacity=0.2))
    y += 56
    lock, _ = lockup(M, y, 110, P["cream"], P["lime"])
    els.append(lock)
    pts = [(-60, 1410), (180, 1450), (340, 1330), (560, 1350), (780, 1370), (880, 1550), (1140, 1470)]
    els.append(ribbon("Ribbon", pts, 118, teal_fill=dark_ribbon_fill(pts)))
    els.append(footer("AFAQ for Energy & Integrated Business", 8, dark))
    return {"name": "08 Contact", "bg": P["teal"], "elements": els}

SLIDES = [slide_cover, slide_about, slide_components, slide_scope, slide_ways, slide_uses, slide_brings, slide_contact]

# ---------------------------------------------------------------- SVG writer
class SvgWriter:
    def __init__(self, ps_names=False):
        self.defs = []
        self.ids = {}
        self.gcount = 0
        self.ps_names = ps_names

    def uid(self, name):
        base = "".join(ch if (ch.isalnum() or ch in "-_") else "-" for ch in name).strip("-") or "Layer"
        n = self.ids.get(base, 0)
        self.ids[base] = n + 1
        return base if n == 0 else f"{base}-{n + 1}"

    def paint(self, fill):
        if fill is None:
            return "none"
        if isinstance(fill, str):
            return fill
        self.gcount += 1
        gid = f"grad-{self.gcount}"
        stops = "".join(f'<stop offset="{fmt(o)}" stop-color="{c}" stop-opacity="{fmt(a)}"/>' for o, c, a in fill["stops"])
        self.defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{fmt(fill["x1"])}" y1="{fmt(fill["y1"])}" x2="{fmt(fill["x2"])}" y2="{fmt(fill["y2"])}">{stops}</linearGradient>')
        return f"url(#{gid})"

    def el(self, e, depth=1):
        ind = "  " * depth
        op = "" if e.get("opacity", 1) == 1 else f' opacity="{fmt(e["opacity"])}"'
        t = e["type"]
        if t == "group":
            inner = "".join(self.el(c, depth + 1) for c in e["children"])
            return f'{ind}<g id="{self.uid(e["name"])}">\n{inner}{ind}</g>\n'
        if t == "rect":
            stroke = f' stroke="{e["stroke"]}" stroke-width="{fmt(e["sw"])}"' if e.get("stroke") else ""
            rx = f' rx="{fmt(e["rx"])}"' if e.get("rx") else ""
            return f'{ind}<rect id="{self.uid(e["name"])}" x="{fmt(e["x"])}" y="{fmt(e["y"])}" width="{fmt(e["w"])}" height="{fmt(e["h"])}"{rx} fill="{self.paint(e["fill"])}"{stroke}{op}/>\n'
        if t == "circle":
            stroke = f' stroke="{e["stroke"]}" stroke-width="{fmt(e["sw"])}"' if e.get("stroke") else ""
            return f'{ind}<circle id="{self.uid(e["name"])}" cx="{fmt(e["cx"])}" cy="{fmt(e["cy"])}" r="{fmt(e["r"])}" fill="{self.paint(e["fill"])}"{stroke}{op}/>\n'
        if t == "path":
            fill = self.paint(e.get("fill"))
            stroke = ""
            if e.get("stroke"):
                stroke = f' stroke="{e["stroke"]}" stroke-width="{fmt(e["sw"])}" stroke-linecap="{e["cap"]}" stroke-linejoin="{e["join"]}"'
            return f'{ind}<path id="{self.uid(e["name"])}" d="{e["d"]}" fill="{fill}"{stroke}{op}/>\n'
        if t == "text":
            size, lh = e["size"], e["lh"]
            b = baseline(size, lh)
            anchor = {"left": "start", "right": "end", "center": "middle"}[e["align"]]
            # right-aligned tracked text: cancel the trailing letter-space so the glyphs end on the margin
            ax = e["x"] if e["align"] == "left" else (e["x"] + e["w"] + e["ls"] * size if e["align"] == "right" else e["x"] + e["w"] / 2)
            ls = f' letter-spacing="{fmt(e["ls"] * size)}"' if e["ls"] else ""
            ta = f' text-anchor="{anchor}"' if anchor != "start" else ""
            family = PS_NAMES[e["weight"]] if self.ps_names else "Inter"
            common = f'font-family="{family}" font-size="{fmt(size)}" font-weight="{e["weight"]}" fill="{e["color"]}"{ls}{ta}{op}'
            lines = e["lines"]
            if len(lines) == 1:
                return f'{ind}<text id="{self.uid(e["name"])}" x="{fmt(ax)}" y="{fmt(e["y"] + b)}" {common}>{escape(lines[0])}</text>\n'
            inner = "".join(f'{ind}  <text id="{self.uid(e["name"] + "-line")}" x="{fmt(ax)}" y="{fmt(e["y"] + b + i * lh)}" {common}>{escape(l)}</text>\n' for i, l in enumerate(lines))
            return f'{ind}<g id="{self.uid(e["name"])}">\n{inner}{ind}</g>\n'
        raise ValueError(t)

    def document(self, elements, width, height, title):
        body = "".join(self.el(e) for e in elements)
        defs = f'  <defs>\n    {"".join(self.defs)}\n  </defs>\n' if self.defs else ""
        return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<!-- {escape(title)} — AFAQ Corporate Profile, {width}x{height}. Editable vector: inline fills only, text as <text>, no masks/CSS/transforms. Font: Inter (300/400/500/600). -->\n'
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
                f'{defs}{body}</svg>\n')

def write(path, content, mode="w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode, encoding=None if "b" in mode else "utf-8") as f:
        f.write(content)

def svg_of(elements, width, height, title, ps_names=False):
    return SvgWriter(ps_names).document(elements, width, height, title)

# ---------------------------------------------------------------- ASE palette (Illustrator swatches)
def write_ase(path, swatches):
    def block(name, hexcol):
        r, g, b = (int(hexcol[i:i + 2], 16) / 255 for i in (1, 3, 5))
        name_u = (name + "\0").encode("utf-16-be")
        data = struct.pack(">H", len(name) + 1) + name_u + b"RGB " + struct.pack(">fff", r, g, b) + struct.pack(">H", 0)
        return struct.pack(">HI", 0x0001, len(data)) + data
    body = b"".join(block(n, c) for n, c, _ in swatches)
    write(path, b"ASEF" + struct.pack(">HH", 1, 0) + struct.pack(">I", len(swatches)) + body, "wb")

# ---------------------------------------------------------------- assets
def build_assets():
    A = os.path.join(OUT, "assets")
    for variant, col, bg in [("teal", P["teal_ink"], None), ("cream", P["cream"], P["teal"]), ("lime", P["lime"], P["teal"]), ("white", P["white"], None)]:
        lock, h = lockup(40, 40, 120, col)
        lw = round(WORDMARK_W * 1.2) + 80
        els = ([R("Background", 0, 0, lw, 80 + h, bg)] if bg else []) + [lock]
        write(os.path.join(A, "logo", f"afq-lockup-{variant}.svg"), svg_of(els, lw, int(80 + h), f"AFQ lockup ({variant})"))
        ww = WORDMARK_W + 80
        els = ([R("Background", 0, 0, ww, 200, bg)] if bg else []) + [wordmark(40, 40, 100, col)]
        write(os.path.join(A, "logo", f"afq-wordmark-{variant}.svg"), svg_of(els, ww, 200, f"AFQ wordmark ({variant})"))
    pts = [(-60, 190), (160, 200), (300, 40), (520, 60), (740, 80), (820, 260), (1140, 190)]
    write(os.path.join(A, "graphics", "ribbon-lime-teal-orange.svg"), svg_of([ribbon("Ribbon", pts, 118)], 1080, 460, "Ribbon"))
    write(os.path.join(A, "graphics", "ribbon-on-dark.svg"), svg_of([R("Background", 0, 0, 1080, 460, P["teal"]), ribbon("Ribbon", pts, 118, teal_fill=dark_ribbon_fill(pts))], 1080, 460, "Ribbon on dark"))
    write(os.path.join(A, "graphics", "ribbon-lime-only.svg"), svg_of([ribbon("Ribbon", pts, 118, teal=False, orange=False)], 1080, 460, "Ribbon (lime)"))
    write(os.path.join(A, "graphics", "tab-panel.svg"), svg_of([PATH("Tab-Panel", tab_path(20, 20, 600, 360, 168, 52, 32, 22, "tl"), fill=P["teal_mid"])], 640, 400, "Tab panel"))
    write(os.path.join(A, "graphics", "tab-panel-lime.svg"), svg_of([PATH("Tab-Panel", tab_path(20, 20, 600, 360, 168, 52, 32, 22, "tr"), fill=P["lime"])], 640, 400, "Tab panel (lime)"))
    for corner in ("tl", "tr", "bl", "br"):
        els = [photo_slot("Photo-Slot", 20, 20, 900, 640, 40, {"corner": corner, "w": 300, "h": 130, "r": 24})]
        write(os.path.join(A, "graphics", f"photo-slot-notch-{corner}.svg"), svg_of(els, 940, 680, f"Photo slot (notch {corner})"))
    write(os.path.join(A, "graphics", "photo-slot-plain.svg"), svg_of([photo_slot("Photo-Slot", 20, 20, 900, 640, 40)], 940, 680, "Photo slot"))
    for art in ("solar", "storage", "grid"):
        write(os.path.join(A, "graphics", f"photo-slot-dark-{art}.svg"), svg_of([R("Background", 0, 0, 940, 680, P["teal"]), photo_slot("Photo-Slot", 20, 20, 900, 640, 40, dark=True, art=art)], 940, 680, f"Photo slot dark ({art})"))
    for key in ICONS:
        write(os.path.join(A, "icons", f"icon-{key}.svg"), svg_of([icon(None, key, 8, 8, 48, P["teal"])], 64, 64, f"Icon {key}"))
    sheet = [R("Background", 0, 0, 1000, 420, P["cream"])]
    for i, key in enumerate(ICONS):
        x, y = 40 + (i % 6) * 156, 40 + (i // 6) * 130
        sheet.append(C(f"Disc-{key}", x + 44, y + 44, 44, P["lime"]))
        sheet.append(icon(None, key, x + 20, y + 20, 48, P["teal"]))
        sheet.append(T(f"Name-{key}", x - 20, y + 98, 128, key, 13, 500, P["muted"], lh=18, align="center"))
    write(os.path.join(A, "icons", "_icon-sheet.svg"), svg_of(sheet, 1000, 420, "Icon sheet"))
    pal = [R("Background", 0, 0, 1000, 680, P["white"])]
    for i, (name, col, use) in enumerate(PALETTE_DOC):
        x, y = 40 + (i % 4) * 236, 40 + (i // 4) * 156
        pal.append(R(f"Swatch-{name}", x, y, 200, 90, col, rx=16, stroke=P["line"], sw=1))
        pal.append(T(f"Name-{name}", x, y + 100, 200, name, 15, 600, P["charcoal"], lh=20))
        pal.append(T(f"Hex-{name}", x, y + 122, 200, col, 13, 400, P["muted"], lh=18))
    write(os.path.join(A, "palette", "afaq-palette.svg"), svg_of(pal, 1000, 680, "Palette"))
    write_ase(os.path.join(A, "palette", "afaq-palette.ase"), PALETTE_DOC)
    write(os.path.join(A, "palette", "palette.json"), json.dumps(
        {"brand": "AFAQ for Energy & Integrated Business", "colors": [{"name": n, "hex": c, "use": u} for n, c, u in PALETTE_DOC],
         "typography": {"family": "Inter", "styles": {"display": "Light 300", "title": "Light 300", "heading": "Semi Bold 600", "body": "Regular 400", "label": "Medium 500 (tracking +16–30%)"}}},
        indent=2))

# ---------------------------------------------------------------- Figma scripts (same spec, slimmed)
def slim(e):
    if e["type"] == "group":
        return {"type": "group", "name": e["name"], "children": [slim(c) for c in e["children"]]}
    e = {k: v for k, v in e.items() if k != "lines"}
    for k in ("x", "y", "w", "h", "cx", "cy", "r", "rx", "sw", "lh"):
        if k in e and isinstance(e[k], float):
            e[k] = round(e[k], 2)
    return e

def write_figma_scripts(spec):
    builder_path = os.path.join(OUT, "figma", "figma-build.js")
    if not os.path.exists(builder_path):
        print("figma/figma-build.js missing — skipped Figma scripts")
        return
    body = open(builder_path, encoding="utf-8").read().split("// eslint-disable-next-line")[0]
    slides = [{"name": s["name"], "bg": s["bg"], "elements": [slim(e) for e in s["elements"]]} for s in spec["slides"]]
    for i, s in enumerate(slides):
        one = {"canvas": spec["canvas"], "slides": [s]}
        js = (f"// use_figma script — builds slide {s['name']} as a native 1080x1920 frame on the current page.\n"
              f"// Generated by tools/deck.py from the same spec as pages/*.svg; readable source: figma/figma-build.js\n"
              f"const SPEC = {json.dumps(one, separators=(',', ':'))};\n{body}\nreturn await buildDeck(SPEC);\n")
        write(os.path.join(OUT, "figma", "slides", f"slide-{i + 1:02d}.js"), js)
    full = {"canvas": spec["canvas"], "slides": slides}
    write(os.path.join(OUT, "figma", "scripter-build-all.js"),
          f"// Scripter plugin: paste everything and run. Builds all 8 slides to the right of existing content.\n"
          f"// Generated by tools/deck.py from the same spec as pages/*.svg.\n"
          f"const SPEC = {json.dumps(full, separators=(',', ':'))};\n{body}\nconst result = await buildDeck(SPEC);\nconsole.log(result);\n")

# ---------------------------------------------------------------- main
def main():
    spec = {"canvas": {"width": W, "height": H}, "font": {"family": "Inter", "styles": STYLE_NAMES, "metrics": {"ascent": ASC, "descent": DESC}},
            "palette": P, "slides": []}
    for i, fn in enumerate(SLIDES):
        s = fn()
        spec["slides"].append(s)
        fname = f"{i + 1:02d}-{s['name'][3:].lower().replace(' ', '-')}.svg"
        write(os.path.join(OUT, "pages", fname), svg_of(s["elements"], W, H, s["name"]))
        write(os.path.join(OUT, "pages-illustrator", fname), svg_of(s["elements"], W, H, s["name"], ps_names=True))
        print("wrote pages/" + fname)
    write(os.path.join(OUT, "spec", "deck-spec.json"), json.dumps(spec, indent=1))
    write_figma_scripts(spec)
    build_assets()
    print("assets, spec and figma scripts written to", OUT)

if __name__ == "__main__":
    main()

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
# Wordmark: the official 4-letter AFAQ artwork, traced from the master file (1879x336 px, 0.23 % pixel deviation).
# One filled path (A, F+A, Q with counter); scaled so that h = full artwork height (tail included). Baseline at 310/336.
AFAQ_NAT_W, AFAQ_NAT_H = 1879, 336
AFAQ_PATH = "M 1831.78 334.97 C 1824.65 333.77 1816.66 329.69 1810.89 324.32 C 1808.04 321.67 1793.57 304.88 1778.73 287 C 1763.88 269.12 1750.34 253.23 1748.62 251.68 C 1746.9 250.13 1742.58 247.43 1739 245.68 C 1732.88 242.68 1731.86 242.5 1721.5 242.53 C 1704.42 242.57 1703.26 243.28 1677 269.85 C 1653.98 293.13 1650.25 295.88 1636.79 299.38 C 1629.32 301.33 1505.21 302.77 1487.86 301.11 C 1465.98 299.01 1448.84 293.07 1431.55 281.56 C 1413.96 269.86 1400.79 254.76 1391.51 235.63 C 1382.08 216.21 1382.5 220.25 1382.5 150 C 1382.5 80.67 1382.21 83.73 1390.39 66.47 C 1402.21 41.51 1422.52 20.71 1446.5 9 C 1465.22 -0.14 1453 0.62 1587.5 0.22 C 1673.76 -0.04 1708.98 0.18 1715.5 1.02 C 1754.86 6.09 1790.02 37.57 1801.67 78.16 L 1804.35 87.5 L 1804.99 141 C 1805.55 187.66 1805.85 195.14 1807.33 199.5 C 1810.3 208.22 1807.42 204.81 1846.94 246.24 C 1877.5 278.26 1878.5 279.86 1878.5 296.4 C 1878.49 306.9 1878.32 307.83 1875.35 313.52 C 1869.65 324.43 1858.51 332.69 1846.53 334.91 C 1840 336.12 1838.63 336.12 1831.78 334.97 Z M 575.26 308.46 C 563.09 305.18 551.14 296.09 545.41 285.75 L 542.5 280.5 L 542.5 197.47 C 542.5 117.77 542.58 114.26 544.42 109.97 C 546.64 104.81 549.18 101.39 572.91 71.5 C 620.66 11.37 617.97 14.37 629.5 8.54 C 643.25 1.6 635.84 1.94 767.09 2.23 L 885.5 2.5 L 890.39 5 C 898.19 8.98 903.55 14.38 907.45 22.18 C 910.66 28.59 911 30.06 911 37.55 C 911 43.66 910.43 47.32 908.8 51.57 C 905.74 59.56 897.85 67.87 889.78 71.6 L 883.5 74.5 L 781.5 75.01 C 668.46 75.58 678.35 74.97 664.72 82.23 C 649.54 90.32 633.31 113.29 634.2 125.41 L 634.5 129.5 L 733 130 L 831.5 130.5 L 836.77 133.42 C 848.92 140.15 855.59 151.71 854.72 164.5 C 854.46 168.37 853.33 173.58 852.2 176.15 C 849.14 183.1 840.62 191.25 833.68 193.85 C 827.95 195.99 827.53 196 741.01 196 C 680.71 196 652.5 196.34 648.88 197.12 C 644.77 198 642.67 199.23 638.95 202.95 C 632.46 209.44 632 212.26 632 245.44 C 632 270.09 631.8 273.44 629.97 279.35 C 623.26 301.08 597.92 314.56 575.26 308.46 Z M 858.27 307.64 C 839.44 300.47 828.96 281.95 832.93 262.84 C 834.35 256 837.42 251.42 864 216.36 C 879.12 196.43 884.81 189.68 889.35 186.34 C 898.52 179.57 901.65 179 930 179 C 957.22 179 963.53 178.24 972.75 173.87 C 982.13 169.41 989.37 161.94 1005.85 139.69 C 1030.33 106.64 1052.8 76.19 1074.25 47 C 1097.02 16 1103.59 8.8 1113.62 3.87 C 1120.19 0.63 1120.92 0.5 1132 0.5 C 1143.12 0.5 1143.8 0.63 1150.52 3.92 C 1157.84 7.51 1167.21 16 1172.14 23.5 C 1174.31 26.79 1211.15 80.46 1231.51 110 C 1234.36 114.12 1250.78 137.98 1268.02 163 C 1285.25 188.02 1305.87 217.95 1313.84 229.5 C 1332.12 256 1333.47 258.8 1333.44 270.01 C 1333.42 277.37 1333 279.4 1330.37 285.01 C 1325.09 296.26 1315.42 304.36 1303.54 307.45 C 1289.66 311.06 1275.34 307.9 1265.65 299.09 C 1264.08 297.67 1257.59 289.3 1251.21 280.5 C 1244.84 271.7 1237.31 261.35 1234.47 257.5 C 1231.64 253.65 1219.79 237.39 1208.16 221.36 C 1196.52 205.34 1185.14 190.55 1182.87 188.5 C 1180.6 186.45 1176.21 183.58 1173.12 182.14 L 1167.5 179.5 L 1085.33 179.72 C 1007.03 179.93 1002.93 180.03 998.11 181.86 C 990.14 184.89 983.62 190.38 976.21 200.31 C 966.47 213.34 932.57 258.9 920.27 275.5 C 906.47 294.11 899.43 301.18 890.14 305.78 C 883.54 309.04 881.81 309.45 873.64 309.71 C 865.97 309.96 863.5 309.63 858.27 307.64 Z M 29.5 307.68 C 17.81 304.68 8.13 296.78 3.16 286.18 C 0.84 281.22 0.5 279.24 0.5 270.5 C 0.5 263.96 1.01 259.29 1.97 257 C 3.51 253.34 46.91 194.94 52.36 189.19 C 54.09 187.37 58.41 184.45 61.97 182.69 L 68.45 179.5 L 98.47 178.9 C 125.85 178.36 129.02 178.11 134.42 176.15 C 141.55 173.55 148.4 169.28 152.61 164.81 C 154.32 162.99 177.98 131.8 205.19 95.5 C 232.39 59.2 257.46 25.77 260.9 21.2 C 271.85 6.66 279.86 2.64 298 2.55 C 308.85 2.5 309.87 2.68 316 5.6 C 324.78 9.78 331.1 15.75 339.83 28.12 C 348.81 40.86 371.07 72.68 401.98 117 C 414.83 135.43 431.48 159.27 438.97 170 C 446.47 180.73 461.99 202.95 473.47 219.39 C 485.42 236.49 495.43 251.89 496.87 255.39 C 498.87 260.23 499.41 263.27 499.45 270 C 499.49 277.49 499.13 279.27 496.41 285 C 492.43 293.36 488.92 297.45 481.69 302.12 C 473.32 307.53 463.11 309.69 453.17 308.14 C 437.81 305.75 433.78 302.46 415.72 277.54 C 408.53 267.62 401.43 257.93 399.96 256 C 398.48 254.07 387.67 239.23 375.94 223 C 364.2 206.77 352.78 191.75 350.55 189.62 C 348.32 187.48 343.57 184.33 340 182.62 L 333.5 179.5 L 255.31 179.22 C 188.06 178.97 176.19 179.14 170.53 180.46 C 162.24 182.38 156.98 185.06 151.41 190.19 C 149 192.41 132.28 214.05 114.26 238.27 C 96.24 262.49 78.91 285.61 75.74 289.65 C 69.13 298.08 62.82 303.09 55.1 306.03 C 48.33 308.61 36.17 309.39 29.5 307.68 Z M 1681.87 221.55 C 1696.19 217.73 1708.47 207.89 1714.75 195.18 L 1718.5 187.6 L 1718.5 148.05 L 1718.5 108.5 L 1715.71 102.53 C 1709.66 89.61 1699.15 79.99 1685.32 74.72 L 1679.5 72.5 L 1596 72.22 L 1512.5 71.93 L 1504.37 74.46 C 1489.87 78.97 1478.19 88.77 1471.77 101.81 L 1468.5 108.45 L 1468.22 146.74 C 1467.97 179.68 1468.16 185.7 1469.53 189.77 C 1474.47 204.41 1486.82 216.17 1502 220.67 C 1509.48 222.89 1509.67 222.89 1593 222.93 C 1662.31 222.97 1677.41 222.73 1681.87 221.55 Z"
WORDMARK_W = round(AFAQ_NAT_W / AFAQ_NAT_H * 100, 1)   # width of the mark when h = 100
WM_SW = 0

def wordmark(x, y, h, color, name="Wordmark-AFAQ"):
    s = h / AFAQ_NAT_H
    return G(name, [PATH("Letters-AFAQ", tx_path(AFAQ_PATH, s, x, y), fill=color)])

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

def box_ribbon(name, x0, x1, y_bottom, thickness, rel=(0.0, -0.4, 0.5, 0.2, -0.2, -0.8, -0.6), teal_fill=None):
    """Ribbon whose teal underside never leaves [x0, x1] x (.., y_bottom]: used inside photo frames (no clipping needed)."""
    xs = [x0 + (x1 - 40 - x0) * i / (len(rel) - 1) for i in range(len(rel))]
    amp = thickness * 0.55
    base = y_bottom - 8 - 1.45 * thickness - amp * 0.5
    pts = [(round(xx), round(base + r * amp)) for xx, r in zip(xs, rel)]
    return ribbon(name, pts, thickness, teal_fill=teal_fill)

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

def photo_slot(name, x, y, w, h, r=40, notch=None, dark=False, art="solar", sun=None):
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
    if sun:
        sun_left = (sun == "left")
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

# ---------------------------------------------------------------- shared slide parts (layout v2: matches the client's board)
M = 80
CW = W - 2 * M  # 920
FOOT_Y = 1836
LIME_PALE_BG = "#E9FBB8"
CARD_GREY = "#E6E6DA"

def eyebrow(num, label, dark=False, on_lime=False, y=112):
    pill_fill = P["teal"] if on_lime else P["lime"]
    num_col = P["lime"] if on_lime else P["teal"]
    lab_col = P["cream"] if dark else (P["teal"] if on_lime else P["muted"])
    return G("Eyebrow", [
        R("Eyebrow-Pill", M, y, 48, 26, pill_fill, rx=13),
        T("Eyebrow-Number", M, y + 3, 48, num, 12, 600, num_col, lh=20, align="center"),
        T("Eyebrow-Label", M + 64, y + 4, 700, label, 12, 500, lab_col, lh=18, ls=0.22, case="upper", opacity=0.75 if dark else 1.0),
    ])

def footer(section, n, dark, on_lime=False):
    col = P["cream"] if dark else P["teal"]
    op = 0.7 if dark else 0.8
    rule_col = P["cream"] if dark else (P["teal"] if on_lime else P["line"])
    kids = [LINE("Footer-Rule", M, FOOT_Y, W - M, FOOT_Y, rule_col, 1, opacity=0.2 if (dark or on_lime) else 1.0),
            wordmark(M, 1862, 18, col, name="Footer-Wordmark"),
            LINE("Footer-Divider", M + 108, 1860, M + 108, 1882, col, 1, opacity=0.35),
            T("Footer-Profile", M + 124, 1862, 400, "Corporate Profile 2026", 11, 500, col, lh=18, ls=0.22, case="upper", opacity=op),
            T("Footer-Section", W - M - 520, 1862, 480, f"{section}   |   {n:02d}", 11, 500, col, lh=18, ls=0.22, case="upper", align="right", opacity=op)]
    return G("Footer", kids)

def title(text, dark, y=156, size=96, color=None, w=CW):
    return T("Title", M, y, w, text, size, 300, color or (P["cream"] if dark else P["teal"]), lh=round(size * 1.02), ls=-0.03)

def services_list(x, y, color, size=13, rule=True, rule_color=None, lh=19):
    kids = []
    if rule:
        kids.append(LINE("Services-Rule", x, y + 2, x, y + 4 * lh - 4, rule_color or P["orange"], 2))
    kids.append(T("Services-List", x + (18 if rule else 0), y, 300, "SOLAR\nSTORAGE\nELECTRICAL\nENGINEERING", size, 500, color, lh=lh, ls=0.2))
    return G("Services", kids)

def lockup_with_services(x, y, h, color, services_color=None):
    lock, lh_ = lockup(x, y, h, color)
    wm_w = WORDMARK_W * h / 100.0
    div_x = x + wm_w + 40
    kids = [lock, LINE("Lockup-Divider", div_x, y, div_x, y + h * 1.1, color, 1.5, opacity=0.6),
            services_list(div_x + 30, y + 2, services_color or color, size=max(11, round(h * 0.2)), rule=False, lh=round(h * 0.28))]
    return G("Logo-Lockup-Services", kids)

def orange_label(x, y, w=132, h=104, text="SOLAR\nSTORAGE\nELECTRICAL\nENGINEERING", size=10):
    return G("Label-Tab", [R("Label-Tab-Shape", x, y, w, h, P["orange"], rx=16),
                           T("Label-Tab-Text", x + 18, y + 18, w - 30, text, size, 500, P["teal_ink"], lh=16, ls=0.18)])

def notch_outline(x, y, w, h, color, sw=58, edge=P["orange"], name="Deco-Outline"):
    d = rect_path(x, y, w, h, 96, {"corner": "tl", "w": w * 0.42, "h": h * 0.34, "r": 40})
    return G(name, [PATH(name + "-Edge", d, stroke=edge, sw=sw + 6, cap="butt", join="round"),
                    PATH(name + "-Body", d, stroke=color, sw=sw, cap="butt", join="round")])

# ---------------------------------------------------------------- slides
def slide_cover():
    els = [R("Background", 0, 0, W, H, P["teal"])]
    lock, _ = lockup(M, 96, 58, P["cream"])
    els.append(lock)
    els.append(G("Profile-Tab", [R("Profile-Tab-Shape", W - M - 130, 96, 130, 98, P["orange"], rx=14),
                                 T("Profile-Tab-Text", W - M - 130 + 20, 96 + 24, 110, "CORPORATE\nPROFILE\n2026", 10, 500, P["cream"], lh=16, ls=0.16)]))
    head = T("Headline", M, 300, 900, "AFAQ for Energy\n& Integrated\nBusiness.", 100, 300, P["cream"], lh=104, ls=-0.03)
    els.append(head)
    y = 300 + head["h"] + 36
    slog = T("Slogan", M, y, CW, "Innovating today, sustaining tomorrow", 42, 300, P["lime"], lh=52)
    els.append(slog)
    els.append(T("Scope", M, y + slog["h"] + 22, 800, "Solar power and energy storage in the Sultanate of Oman", 21, 400, P["cream"], lh=30, opacity=0.7))
    els.append(photo_slot("Photo-Hero", M, 860, CW, 740, 40, {"corner": "tr", "w": 246, "h": 170, "r": 30}, dark=False))
    pts = [(330, 2000), (420, 1880), (560, 1700), (760, 1600), (920, 1560), (1040, 1520), (1180, 1420)]
    els.append(ribbon("Ribbon", pts, 230))
    els.append(services_list(M, 1760, P["cream"]))
    return {"name": "01 Cover", "bg": P["teal"], "elements": els}

def slide_about():
    dark = False
    els = [R("Background", 0, 0, W, H, P["cream"]), eyebrow("01", "About AFAQ")]
    t = title("About AFAQ.", dark)
    els.append(t)
    y = 156 + t["h"] + 36
    p1 = T("Body-1", M, y, 760, "AFAQ for Energy & Integrated Business is an Omani company based in Muscat. It works in solar power, energy storage and the electrical systems that go with them.", 27, 400, P["teal"], lh=40)
    els.append(p1)
    y += p1["h"] + 34
    col_w = (CW - 60) / 2
    p2 = T("Body-2", M, y, col_w, "The company designs photovoltaic systems, supplies their components, installs them and brings them into operation, at sizes ranging from building systems to project plants.", 17, 400, P["muted"], lh=26)
    p3 = T("Body-3", M + col_w + 60, y, col_w, "AFAQ works directly with facility owners, and with contractors and developers inside their own projects.", 17, 400, P["muted"], lh=26)
    els += [p2, p3]
    py = y + max(p2["h"], p3["h"]) + 56
    ph = 1776 - py
    els.append(photo_slot("Photo-Array", M, py, CW, ph, 36, dark=False, art="solar", sun="right"))
    # lime statement panel overlapping the photo's top-left
    panel_w, panel_h = 520, 400
    els.append(G("Statement-Panel", [
        R("Statement-Shape", M, py, panel_w, panel_h, P["lime"], rx=36),
        T("Statement-Text", M + 44, py + 44, panel_w - 80, "Energy.\nEngineered.", 72, 300, P["teal"], lh=76, ls=-0.03),
        lockup_with_services(M + 44, py + 44 + 152 + 60, 44, P["teal"]),
    ]))
    els.append(orange_label(W - M - 36 - 132, py + 36))
    els.append(box_ribbon("Ribbon", M, W - M, py + ph, 96))
    els.append(footer("About AFAQ", 2, dark))
    return {"name": "02 About AFAQ", "bg": P["cream"], "elements": els}

def slide_components():
    dark = False
    els = [R("Background", 0, 0, W, H, P["cream"]), eyebrow("02", "System components")]
    t = title("System components.", dark, size=86)
    els.append(t)
    sub = T("Subtitle", M, 156 + t["h"] + 40, 480, "A photovoltaic system is built from four components. AFAQ holds a direct supply agreement with a main supplier for each.", 24, 400, P["teal"], lh=34, opacity=0.85)
    els.append(sub)
    py = 156 + t["h"] + 36
    ph = 920 - py
    notch_h = sub["h"] + 60
    els.append(photo_slot("Photo-Plant", M, py, CW, ph, 36, {"corner": "tl", "w": 560, "h": notch_h, "r": 30}, dark=False, art="grid"))
    els.append(box_ribbon("Ribbon", M, W - M, py + ph, 80, rel=(0.3, -0.5, 0.4, 0.1, -0.4, -0.9, -0.7)))
    comps = [
        ("01", "PV modules", "Selected according to the mounting area available and the conditions on site.", "Main suppliers", "AACE · Ronma", "pv-module"),
        ("02", "Battery energy storage", "Sized on the loads to be covered and the autonomy required.", "Main supplier", "Goshin", "battery"),
        ("03", "Inverters and power conversion", "Selected according to the array configuration and the connection requirements of the grid operator.", "Main supplier", "Star Charge", "inverter"),
        ("04", "Plant infrastructure", "Mounting structures, foundations, DC and AC cabling, and connection and protection panels, specified to suit the site.", None, None, "infrastructure"),
    ]
    y0, gap = 964, 24
    cw = (CW - gap) / 2
    ch = (1776 - y0 - gap) / 2
    for i, (num, name, note, lab, sup, ic) in enumerate(comps):
        x = M + (i % 2) * (cw + gap)
        y = y0 + (i // 2) * (ch + gap)
        dark_card = (i == 3)
        fill = P["teal"] if dark_card else CARD_GREY
        shape = (PATH("Card-Shape", rect_path(x, y, cw, ch, 28, {"corner": "br", "w": 150, "h": 84, "r": 22}), fill=fill) if dark_card
                 else R("Card-Shape", x, y, cw, ch, fill, rx=28))
        tcol = P["cream"] if dark_card else P["teal"]
        bcol = P["cream"] if dark_card else P["muted"]
        kids = [shape,
                T("Number", x + 32, y + 36, 200, num, 60, 300, tcol, lh=64, ls=-0.02),
                C("Icon-Disc", x + cw - 32 - 28, y + 36 + 28, 28, P["lime"]),
                icon("Icon", ic, x + cw - 32 - 28 - 14, y + 36 + 28 - 14, 28, P["teal"], sw=2.2),
                ]
        tt = T("Card-Title", x + 32, y + 120, cw - 64, name, 25, 400, tcol, lh=32)
        kids.append(tt)
        nb = T("Card-Note", x + 32, y + 120 + tt["h"] + 10, cw - 64, note, 15, 400, bcol, lh=23, opacity=0.8 if dark_card else 1.0)
        kids.append(nb)
        if lab:
            ly = y + ch - 32 - 22 - 20 - 18
            kids.append(LINE("Card-Divider", x + 32, ly - 18, x + cw - 32, ly - 18, P["teal"], 1, opacity=0.15))
            kids.append(T("Supplier-Label", x + 32, ly, 300, lab, 11, 500, bcol, lh=16, ls=0.18, case="upper"))
            kids.append(T("Supplier", x + 32, ly + 20, cw - 64, sup, 17, 500, tcol, lh=24))
        els.append(G(f"Card-{num}", kids))
    els.append(footer("System components", 3, dark))
    return {"name": "03 System components", "bg": P["cream"], "elements": els}

def slide_scope():
    dark = False
    els = [R("Background", 0, 0, W, H, P["cream"]), eyebrow("03", "Scope of work")]
    t = title("Scope of\nwork.", dark)
    els.append(t)
    sub = T("Subtitle", M, 156 + t["h"] + 40, 560, "The project sets the scope, from supply alone to full operation.", 24, 400, P["teal"], lh=34, opacity=0.85)
    els.append(sub)
    rpts = [(700, -60), (860, 60), (960, 260), (1030, 420), (1080, 520), (1120, 580), (1160, 640)]
    els.insert(1, ribbon("Ribbon", rpts, 110))
    steps = [
        ("01", "Study and design", "Load analysis and consumption data, a site survey, system sizing and placement, and the expected annual yield.", "a report covering system capacity, expected annual yield and estimated cost.", "clipboard"),
        ("02", "Supply", "PV modules, batteries, inverters and electrical equipment, with manufacturer warranties.", "a component list with specifications, source and warranty terms.", "boxes"),
        ("03", "Installation and connection", "Installation, electrical works, and grid-tied, off-grid or hybrid connection.", "a working system and a testing and commissioning record.", "infrastructure"),
        ("04", "Operation and monitoring", "Performance monitoring and maintenance under an operation and maintenance contract.", "a performance report comparing actual output against the design figure.", "inverter"),
    ]
    y0 = 156 + t["h"] + 40 + sub["h"] + 72
    cx = M + 34
    tx = M + 130
    tw = W - M - tx
    label_w = text_width("Deliverable:", 15, 600) + 12
    def step_h(body, deliv):
        b = T("m", tx, 0, 560, body, 15, 400, "#000000", lh=23)
        dl = T("m", 0, 0, tw - 60 - label_w - 28, deliv, 15, 400, "#000000", lh=23)
        return 64 + b["h"] + 18 + 18 + dl["h"] + 18
    hs = [step_h(b, d) for _, _, b, d, _ in steps]
    gap = (1776 - y0 - sum(hs)) / (len(steps) - 1)
    ys = []
    yy = y0
    for hh in hs:
        ys.append(round(yy)); yy += hh + gap
    for i, (num, name, body, deliv, ic) in enumerate(steps):
        y = ys[i]
        kids = [C("Node", cx, y + 34, 34, P["lime"]),
                T("Node-Number", cx - 34, y + 34 - 13, 68, num, 17, 600, P["teal"], lh=26, align="center"),
                icon("Icon", ic, tx, y + 18, 30, P["teal"], sw=2.2),
                T("Step-Title", tx + 46, y + 14, tw - 46, name, 28, 400, P["teal"], lh=36)]
        b = T("Step-Body", tx, y + 64, 560, body, 15, 400, P["muted"], lh=23)
        kids.append(b)
        by = y + 64 + b["h"] + 18
        dl = T("Deliverable-Text", tx + 60 + label_w, by + 18, tw - 60 - label_w - 28, deliv, 15, 400, P["teal"], lh=23)
        bh = 18 + dl["h"] + 18
        kids.append(R("Deliverable-Box", tx, by, tw, bh, LIME_PALE_BG, rx=18))
        kids.append(PATH("Deliverable-Check", f"M {tx + 26} {by + 29} L {tx + 33} {by + 36} L {tx + 46} {by + 23}", stroke=P["lime_deep"], sw=2.4))
        kids.append(T("Deliverable-Label", tx + 60, by + 18, label_w, "Deliverable:", 15, 600, P["teal"], lh=23))
        kids.append(dl)
        els.append(G(f"Step-{num}", kids))
        if i < len(steps) - 1:
            els.append(LINE(f"Connector-{i + 1}", cx, y + 34 + 40, cx, ys[i + 1] + 34 - 40, P["lime_deep"], 2, opacity=0.5))
    els.append(footer("Scope of work", 4, dark))
    return {"name": "04 Scope of work", "bg": P["cream"], "elements": els}

def slide_ways():
    els = [R("Background", 0, 0, W, H, P["lime"]), eyebrow("04", "Ways of working", on_lime=True)]
    t = title("Ways of\nworking.", False)
    els.append(t)
    cards = [
        ("01", "Supply and installation for projects", "One party responsible for design, supply, installation and commissioning.", "clipboard", True),
        ("02", "Component supply", "Supply to the specification and quantities of the project, for contractors and installation companies.", "boxes", False),
    ]
    y = 520
    ch, gap = 320, 28
    for num, name, body, ic, notched in cards:
        if notched:
            shape = PATH("Card-Shape", rect_path(M, y, CW, ch, 36, {"corner": "tl", "w": 220, "h": 160, "r": 30}), fill=P["teal"])
        else:
            shape = R("Card-Shape", M, y, CW, ch, P["teal"], rx=36)
        tt = T("Card-Title", M + 260, y + 44, 520, name, 36, 300, P["cream"], lh=42)
        kids = [shape,
                T("Number", M + 40, y + 36, 160, num, 64, 300, P["teal"] if notched else P["lime"], lh=70, ls=-0.02),
                tt,
                T("Card-Body-Text", M + 260, y + 44 + tt["h"] + 18, 520, body, 20, 400, P["cream"], lh=30, opacity=0.8),
                C("Icon-Disc", W - M - 40 - 30, y + 44 + 30, 30, P["lime"]),
                icon("Icon", ic, W - M - 40 - 30 - 14, y + 44 + 30 - 14, 28, P["teal"], sw=2.2)]
        els.append(G(f"Card-{num}", kids))
        y += ch + gap
    els.append(notch_outline(770, 1340, 520, 440, P["teal"]))
    els.append(lockup_with_services(M, 1660, 64, P["teal"]))
    els.append(footer("Ways of working", 5, False, on_lime=True))
    return {"name": "05 Ways of working", "bg": P["lime"], "elements": els}

def slide_uses():
    dark = False
    els = [R("Background", 0, 0, W, H, P["cream"]), eyebrow("05", "Where the systems are used")]
    t = title("Where the\nsystems are used.", dark, size=90)
    els.append(t)
    py = 156 + t["h"] + 44
    panel_h = 800
    sub = T("Statement", M + 40, py + 44, 640, "The pattern of consumption shapes the system more than the type of business does.", 40, 300, P["teal"], lh=50, ls=-0.02)
    img_y = py + 44 + sub["h"] + 36
    els.append(G("Statement-Panel", [R("Statement-Shape", M, py, CW, panel_h, P["lime"], rx=36), sub]))
    els.append(photo_slot("Photo-Site", M + 20, img_y, CW - 40, py + panel_h - 20 - img_y, 28, dark=False, art="solar"))
    els.append(orange_label(W - M - 20 - 24 - 124, img_y + 24, w=124, h=96))
    blocks = [
        ("Sites that consume during the day", "Offices, retail centres, hotels, factories, schools and residential compounds. Their heaviest load falls within sunlight hours.", "sun"),
        ("Sites with continuous loads", "Hospitals, cold stores, production lines and data centres. The system works alongside the backup already in place, cutting generator running hours and fuel use.", "continuous"),
        ("Sites away from the grid", "Farms, irrigation pumps, camps and work sites that run on diesel.", "off-grid"),
        ("Projects under construction", "Contractors and developers delivering the energy scope within a live project.", "construction"),
    ]
    y0 = py + panel_h + 36
    gap = 24
    cw = (CW - gap) / 2
    ch = (1776 - y0 - gap) / 2
    titles = [T("m", 0, 0, cw - 64, n, 23, 400, "#000000", lh=30) for n, _, _ in blocks]
    th = max(x["h"] for x in titles)
    for i, (name, body, ic) in enumerate(blocks):
        x = M + (i % 2) * (cw + gap)
        y = y0 + (i // 2) * (ch + gap)
        kids = [R("Card-Shape", x, y, cw, ch, CARD_GREY, rx=28),
                C("Icon-Disc", x + 32 + 26, y + 32 + 26, 26, P["lime"]),
                icon("Icon", ic, x + 32 + 26 - 13, y + 32 + 26 - 13, 26, P["teal"], sw=2.2),
                T("Card-Title", x + 32, y + 118, cw - 64, name, 23, 400, P["teal"], lh=30),
                T("Card-Body", x + 32, y + 118 + th + 10, cw - 64, body, 14, 400, P["muted"], lh=21)]
        els.append(G(f"Card-{i + 1}", kids))
    els.append(footer("Where the systems are used", 6, dark))
    return {"name": "06 Where the systems are used", "bg": P["cream"], "elements": els}

def slide_brings():
    dark = True
    els = [R("Background", 0, 0, W, H, P["teal"]), eyebrow("06", "What AFAQ brings", dark=True)]
    t = title("What AFAQ\nbrings.", dark)
    els.append(t)
    py = 156 + t["h"] + 44
    ph = 1170 - py
    els.append(photo_slot("Photo-Storage", M, py, CW, ph, 36, {"corner": "tl", "w": 190, "h": 136, "r": 30}, dark=True, art="storage"))
    els.append(orange_label(M, py, w=160, h=108))
    rpts = [(-60, 940), (200, 900), (400, 980), (600, 960), (800, 920), (950, 860), (1140, 880)]
    els.append(ribbon("Ribbon", rpts, 110, teal_fill=dark_ribbon_fill(rpts)))
    items = [
        ("Supply from a factory in Oman", "AACE modules are manufactured in Oman, which shortens supply time compared with importing.", "factory"),
        ("Warranty handled inside Oman", "AFAQ processes module warranty claims locally, without sending them to a manufacturer abroad.", "shield"),
        ("In-country value", "Modules made in Oman support local content requirements in tenders and government projects.", "badge"),
        ("Direct supply agreements", "Written agreements with module, battery and inverter suppliers, covering availability and manufacturer warranties.", "document"),
        ("Delivery team", "An engineering team for design and supervision, and a field crew for installation and commissioning.", "team"),
    ]
    y = 1240
    row_h = (1776 - y) / len(items)
    for i, (name, body, ic) in enumerate(items):
        ry = round(y + i * row_h)
        kids = [icon("Icon", ic, M, ry + 6, 24, P["lime"], sw=2),
                T("Item-Title", M + 44, ry, 300, name, 23, 400, P["cream"], lh=30),
                T("Item-Body", M + 420, ry + 4, CW - 420, body, 14, 400, P["cream"], lh=21, opacity=0.7)]
        if i < len(items) - 1:
            kids.append(LINE("Divider", M, round(ry + row_h - 10), W - M, round(ry + row_h - 10), P["cream"], 1, opacity=0.12))
        els.append(G(f"Item-{i + 1:02d}", kids))
    els.append(footer("What AFAQ brings", 7, dark))
    return {"name": "07 What AFAQ brings", "bg": P["teal"], "elements": els}

def slide_contact():
    dark = False
    els = [R("Background", 0, 0, W, H, P["cream"])]
    py, ph = 92, 730
    els.append(photo_slot("Photo-Farm", M, py, CW, ph, 36, {"corner": "tl", "w": 450, "h": 200, "r": 34}, dark=False, art="solar"))
    els.append(eyebrow("07", "Contact", y=100))
    els.append(title("Contact.", dark, y=140, size=80, w=420))
    rpts = [(-60, 760), (180, 740), (380, 800), (580, 790), (760, 760), (920, 700), (1140, 720)]
    els.append(ribbon("Ribbon", rpts, 110))
    rows = [("Phone", "+968 9190 7789", "phone"), ("Email", "afaq@gmail.com", "mail"), ("Address", "Al Khuwair, behind Zakher Mall, Muscat", "pin")]
    y = 1120
    for i, (lab, val, ic) in enumerate(rows):
        kids = [C("Icon-Disc", M + 32, y + 40, 32, P["lime"]),
                icon("Icon", ic, M + 32 - 14, y + 40 - 14, 28, P["teal"], sw=2),
                T("Label", M + 100, y + 6, 400, lab, 12, 500, P["muted"], lh=18, ls=0.2, case="upper"),
                T("Value", M + 100, y + 30, 800, val, 38, 400, P["teal"], lh=48)]
        if i < len(rows) - 1:
            kids.append(LINE("Divider", M, y + 118, W - M, y + 118, P["line"], 1))
        els.append(G(f"Contact-{lab}", kids))
        y += 150
    els.append(lockup_with_services(M, 1640, 64, P["teal"]))
    els.append(footer("Contact", 8, dark))
    return {"name": "08 Contact", "bg": P["cream"], "elements": els}

def slide_back():
    els = [R("Background", 0, 0, W, H, P["teal"])]
    lock, _ = lockup(M, 110, 66, P["cream"])
    els.append(lock)
    # ribbon field: three bands crossing (page clips the ends)
    a = [(-60, 560), (160, 480), (380, 700), (600, 760), (800, 640), (960, 440), (1140, 380)]
    b = [(-60, 980), (180, 1060), (400, 860), (600, 700), (820, 760), (980, 920), (1140, 980)]
    c = [(-60, 420), (200, 360), (420, 520), (640, 1000), (820, 1080), (980, 1040), (1140, 940)]
    els.append(ribbon("Ribbon-A", a, 130, teal_fill=dark_ribbon_fill(a)))
    els.append(ribbon("Ribbon-B", b, 120, teal_fill=dark_ribbon_fill(b)))
    els.append(ribbon("Ribbon-C", c, 110, teal_fill=dark_ribbon_fill(c)))
    slog = T("Slogan", M, 1220, CW, "Innovating today,\nsustaining tomorrow.", 92, 300, P["cream"], lh=96, ls=-0.03)
    els.append(slog)
    els.append(T("Company", M, 1220 + slog["h"] + 24, 760, "AFAQ for Energy & Integrated Business", 24, 400, P["cream"], lh=32, opacity=0.8))
    els.append(notch_outline(800, 1430, 520, 440, P["lime"], edge=P["lime"]))
    els.append(services_list(M, 1740, P["cream"]))
    return {"name": "09 Back cover", "bg": P["teal"], "elements": els}

SLIDES = [slide_cover, slide_about, slide_components, slide_scope, slide_ways, slide_uses, slide_brings, slide_contact, slide_back]

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

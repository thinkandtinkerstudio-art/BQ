#!/usr/bin/env python3
"""Rova Skin product stickers: spec/products.json -> Illustrator SVGs, one .ai/.pdf (12 artboards), PNG previews.

Every sticker exists twice: portrait (60 x 90 mm) and landscape (90 x 60 mm).  All numbers in this file are
millimetres unless a name says `pt`.  The SVGs keep live text (Georgia / Syne / Amiri) so Illustrator opens them
fully editable; the PDF/.ai carries embedded glyphs, CMYK brand values and a `CutContour` spot colour dieline.

Run:  python3 tools/build.py            (from the rova-skin-stickers folder, or anywhere)
"""
import json, os, re, io, math, html
from fontTools.ttLib import TTFont
import arabic_reshaper
from bidi.algorithm import get_display
import cairosvg
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont as RLFont
from reportlab.lib.colors import CMYKColor, CMYKColorSep

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
MM = 72 / 25.4          # pt per mm
PT = 25.4 / 72          # mm per pt

# --------------------------------------------------------------------------------------------- colours
class Col:
    def __init__(self, hex_, cmyk, name=""):
        self.hex, self.cmyk, self.name = hex_, cmyk, name
    @property
    def rgb(self):
        h = self.hex.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def mix(a, b, t, name=""):
    """Linear mix a->b by t, in both RGB (for screens) and CMYK (for the print PDF)."""
    rgb = tuple(round(x + (y - x) * t) for x, y in zip(a.rgb, b.rgb))
    cmyk = tuple(round(x + (y - x) * t, 4) for x, y in zip(a.cmyk, b.cmyk))
    return Col("#%02X%02X%02X" % rgb, cmyk, name)

BURGUNDY = Col("#3C1219", (0, .70, .58, .76), "Deep Burgundy")
IVORY    = Col("#EFDFD0", (0, .07, .13, .06), "Ivory")
ROSE     = Col("#BDA69D", (0, .12, .17, .26), "Rose tint")
MAGENTA  = Col("#FF00FF", (0, 1, 0, 0), "CutContour")
CYAN     = Col("#00A0E9", (1, 0, 0, 0), "Safe area")

def scheme(field):
    """Ink / line / watermark colours for each of the three brand fields (color guide p.3-4)."""
    if field == "ivory":
        return dict(bg=IVORY, ink=BURGUNDY, line=ROSE, wm=mix(IVORY, BURGUNDY, .10, "10% screen"))
    if field == "burgundy":
        return dict(bg=BURGUNDY, ink=IVORY, line=mix(BURGUNDY, IVORY, .38), wm=mix(BURGUNDY, IVORY, .08))
    if field == "rose":
        return dict(bg=ROSE, ink=BURGUNDY, line=mix(ROSE, BURGUNDY, .42), wm=mix(ROSE, BURGUNDY, .09))
    raise ValueError(field)

# --------------------------------------------------------------------------------------------- fonts
# key -> (SVG family / style / weight for Illustrator, preview family, metrics file, PDF font name)
FONTS = {
    "georgia":        dict(svg=("Georgia", "normal", 400), prev=("Gelasio", "normal", 400), file="Gelasio-Regular.ttf", pdf="Georgia"),
    "georgia-italic": dict(svg=("Georgia", "italic", 400), prev=("Gelasio", "italic", 400), file="Gelasio-Italic.ttf",  pdf="Georgia-Italic"),
    "syne":           dict(svg=("Syne", "normal", 700),    prev=("Syne", "normal", 700),    file="Syne-Bold.ttf",       pdf="Syne-Bold"),
    "amiri":          dict(svg=("Amiri", "normal", 700),   prev=("Amiri", "normal", 700),   file="Amiri-Bold.ttf",      pdf="Amiri-Bold"),
}

class Metrics:
    def __init__(self):
        self.f = {}
        for k, v in FONTS.items():
            tt = TTFont(P("fonts", v["file"]))
            upm = tt["head"].unitsPerEm
            os2 = tt["OS/2"]
            self.f[k] = dict(cmap=tt.getBestCmap(), hmtx=tt["hmtx"], upm=upm,
                             cap=(getattr(os2, "sCapHeight", 0) or 0.7 * upm) / upm)
    def width_mm(self, text, font, size_pt, track_em=0.0):
        f = self.f[font]; w = 0
        for ch in text:
            g = f["cmap"].get(ord(ch)) or f["cmap"].get(ord("?"))
            w += f["hmtx"][g][0]
        return (w / f["upm"] * size_pt + track_em * size_pt * len(text)) * PT
    def cap_mm(self, font, size_pt):
        return self.f[font]["cap"] * size_pt * PT

M = Metrics()

def shape_arabic(s):
    """Logical Arabic -> visual, presentation-form string (for renderers without a shaping engine)."""
    return get_display(arabic_reshaper.reshape(s))

# --------------------------------------------------------------------------------------------- type styles (pt)
STYLE = {
    "step":            dict(font="syne", size=5.5, track=.30, asc=1.0, desc=0.0),
    "name":            dict(font="georgia", size=13.0, track=.05, asc=1.0, desc=0.05, lh=1.22),
    "arabic":          dict(font="amiri", size=9.5, track=0, asc=1.05, desc=0.45),
    "descriptor":      dict(font="georgia-italic", size=8.5, track=0, asc=1.0, desc=0.3),
    "actives":         dict(font="syne", size=5.0, track=.18, asc=1.0, desc=0.0, lh=1.6),
    "benefits_caps":   dict(font="syne", size=5.5, track=.22, asc=1.0, desc=0.0),
    "benefits_italic": dict(font="georgia-italic", size=7.5, track=0, asc=1.0, desc=0.3),
    "size":            dict(font="syne", size=6.0, track=.20, asc=1.0, desc=0.0),
}
# asc/desc are multiples of the cap height, used only to stack lines.

def wrap(text, style, maxw, prefer_sep=" · "):
    """Greedy wrap to maxw (mm); for dotted lists, prefer breaking at the separators."""
    st = STYLE[style]
    fits = lambda s: M.width_mm(s, st["font"], st["size"], st["track"]) <= maxw
    if fits(text): return [text]
    units = text.split(prefer_sep) if prefer_sep in text else text.split(" ")
    joiner = prefer_sep if prefer_sep in text else " "
    lines, cur = [], ""
    for u in units:
        cand = (cur + joiner + u) if cur else u
        if fits(cand): cur = cand
        else:
            if cur: lines.append(cur)
            cur = u
            if not fits(cur) and " " in cur:            # a single unit too long: fall back to words
                sub = wrap(cur, style, maxw, prefer_sep="\x00")
                lines.extend(sub[:-1]); cur = sub[-1]
    if cur: lines.append(cur)
    return lines

def fit_name(text, maxw, max_lines=2):
    """Shrink the product name (0.5 pt steps, floor 10.5 pt) until it wraps to <= max_lines."""
    st = dict(STYLE["name"])
    while True:
        STYLE["name"] = st
        lines = wrap(text, "name", maxw, prefer_sep="\x00")
        if len(lines) <= max_lines or st["size"] <= 10.5: break
        st = dict(st, size=st["size"] - 0.5)
    STYLE["name"] = dict(STYLE["name"], size=13.0)      # restore
    return lines, st["size"]

# --------------------------------------------------------------------------------------------- logo kit
KIT = json.load(open(P("tools", "logo_kit.json")))

def logo(name, x, y, w=None, h=None, color=None):
    k = KIT[name]
    s = (w / k["w"]) if w else (h / k["h"])
    return dict(type="logo", name=name, x=x, y=y, s=s, color=color, w=k["w"] * s, h=k["h"] * s)

def text(x, y, s, style, color, align="center", size=None, rtl=False, id=None):
    st = dict(STYLE[style]);
    if size: st["size"] = size
    return dict(type="text", x=x, y=y, text=s, font=st["font"], size=st["size"], track=st["track"],
                color=color, align=align, rtl=rtl, id=id)

def line(x1, y1, x2, y2, color, sw=0.2):
    return dict(type="line", x1=x1, y1=y1, x2=x2, y2=y2, color=color, sw=sw)

def rect(x, y, w, h, fill=None, stroke=None, sw=0, rx=0, dash=None, id=None, spot=None):
    return dict(type="rect", x=x, y=y, w=w, h=h, fill=fill, stroke=stroke, sw=sw, rx=rx, dash=dash, id=id, spot=spot)

def group(id, children, clip=None):
    return dict(type="group", id=id, children=children, clip=clip)

# --------------------------------------------------------------------------------------------- product icons
# One line icon per product, drawn on a 24 x 24 grid in the style of the Rova highlight icons: a single stroke
# weight, round caps, never filled (small dots excepted).  Only M / L / C / Z commands so the PDF writer can draw them.
from math import cos, sin, tan, radians, degrees, atan2, sqrt, ceil
K = 0.5522847498
ICON_STROKE = 1.25           # grid units

def _f(v): return f"{v:.3f}"

def circle_d(cx, cy, r):
    return (f"M{_f(cx+r)} {_f(cy)} C{_f(cx+r)} {_f(cy+K*r)} {_f(cx+K*r)} {_f(cy+r)} {_f(cx)} {_f(cy+r)} "
            f"C{_f(cx-K*r)} {_f(cy+r)} {_f(cx-r)} {_f(cy+K*r)} {_f(cx-r)} {_f(cy)} "
            f"C{_f(cx-r)} {_f(cy-K*r)} {_f(cx-K*r)} {_f(cy-r)} {_f(cx)} {_f(cy-r)} "
            f"C{_f(cx+K*r)} {_f(cy-r)} {_f(cx+r)} {_f(cy-K*r)} {_f(cx+r)} {_f(cy)} Z")

def arc_d(cx, cy, r, a0, a1, move=True):
    """Circular arc a0 -> a1 (degrees, y-down so positive = clockwise) as cubic segments of <= 90 degrees."""
    out = []; n = max(1, ceil(abs(a1 - a0) / 90)); da = (a1 - a0) / n
    for i in range(n):
        t0, t1 = radians(a0 + i * da), radians(a0 + (i + 1) * da)
        k = 4 / 3 * tan((t1 - t0) / 4)
        p0 = (cx + r * cos(t0), cy + r * sin(t0)); p3 = (cx + r * cos(t1), cy + r * sin(t1))
        p1 = (p0[0] - k * r * sin(t0), p0[1] + k * r * cos(t0)); p2 = (p3[0] + k * r * sin(t1), p3[1] - k * r * cos(t1))
        if i == 0 and move: out.append(f"M{_f(p0[0])} {_f(p0[1])}")
        out.append(f"C{_f(p1[0])} {_f(p1[1])} {_f(p2[0])} {_f(p2[1])} {_f(p3[0])} {_f(p3[1])}")
    return " ".join(out)

def _sweep_through(sa, ea, through):
    """End angle so that the arc from sa to ea passes through angle `through` (all degrees)."""
    pos = (ea - sa) % 360; off = (through - sa) % 360
    return sa + pos if off <= pos else sa - (360 - pos)

def crescent_d(c1, r1, c2, r2):
    """Crescent = circle 1 minus circle 2, as one closed outline."""
    dx, dy = c2[0] - c1[0], c2[1] - c1[1]; d = sqrt(dx * dx + dy * dy)
    a = (r1 * r1 - r2 * r2 + d * d) / (2 * d); h = sqrt(max(r1 * r1 - a * a, 0))
    px, py = c1[0] + a * dx / d, c1[1] + a * dy / d
    ia = (px + h * dy / d, py - h * dx / d); ib = (px - h * dy / d, py + h * dx / d)
    ang = lambda c, p: degrees(atan2(p[1] - c[1], p[0] - c[0]))
    away = degrees(atan2(-dy, -dx)); toward = degrees(atan2(dy, dx))
    outer = arc_d(c1[0], c1[1], r1, ang(c1, ia), _sweep_through(ang(c1, ia), ang(c1, ib), away))
    inner = arc_d(c2[0], c2[1], r2, ang(c2, ib), _sweep_through(ang(c2, ib), ang(c2, ia), toward + 180), move=False)
    return outer + " " + inner + " Z"

def sparkle_d(cx, cy, s, pinch=0.08):
    """Four-point star outline; tips at distance s, waist pulled to the centre."""
    tips = [(cx, cy - s), (cx + s, cy), (cx, cy + s), (cx - s, cy)]
    out = [f"M{_f(tips[0][0])} {_f(tips[0][1])}"]
    for i in range(4):
        p0, p2 = tips[i], tips[(i + 1) % 4]
        q = (cx + (p0[0] + p2[0] - 2 * cx) * pinch, cy + (p0[1] + p2[1] - 2 * cy) * pinch)   # quadratic control near centre
        c1 = (p0[0] + 2 / 3 * (q[0] - p0[0]), p0[1] + 2 / 3 * (q[1] - p0[1]))
        c2 = (p2[0] + 2 / 3 * (q[0] - p2[0]), p2[1] + 2 / 3 * (q[1] - p2[1]))
        out.append(f"C{_f(c1[0])} {_f(c1[1])} {_f(c2[0])} {_f(c2[1])} {_f(p2[0])} {_f(p2[1])}")
    return " ".join(out) + " Z"

def dot(cx, cy, r=0.95): return dict(d=circle_d(cx, cy, r), fill=True)
def stroke(d): return dict(d=d, fill=False)

def build_icons():
    I = {}
    # 01 RENEW · overnight peel: crescent moon + a sparkle
    I["renew"] = [stroke(crescent_d((11.2, 12.6), 8.0, (14.6, 10.4), 7.3)), stroke(sparkle_d(18.6, 6.2, 2.4))]
    # 02 REPAIR · cica recovery: a leaf inside a shield
    shield = "M12 2.9 L19.6 5.9 L19.6 11.6 C19.6 16.4 16.4 20 12 21.6 C7.6 20 4.4 16.4 4.4 11.6 L4.4 5.9 Z"
    leaf = "M8.9 16.1 C8.6 12.2 11.2 8.6 15.6 8.3 C15.9 12.4 13.4 15.9 8.9 16.1 Z"
    vein = "M8.9 16.1 C10.6 13.9 12.4 11.9 14.6 9.9"
    I["repair"] = [stroke(shield), stroke(leaf), stroke(vein)]
    # 03 CORRECT · even tone: one circle, spots on one side, clear and bright on the other
    diag = f"M{_f(12-8*cos(radians(45)))} {_f(12+8*sin(radians(45)))} L{_f(12+8*cos(radians(45)))} {_f(12-8*sin(radians(45)))}"
    I["correct"] = [stroke(circle_d(12, 12, 8)), stroke(diag), dot(8.3, 8.6), dot(11.4, 6.1), dot(6.4, 12.3),
                    stroke(sparkle_d(15.4, 15.4, 2.6))]
    # 04 HYDRATE · barrier moisturiser: a drop with a highlight
    drop = ("M12 3.4 C12 3.4 5.6 10.7 5.6 15 C5.6 18.53 8.47 21.4 12 21.4 C15.53 21.4 18.4 18.53 18.4 15 "
            "C18.4 10.7 12 3.4 12 3.4 Z")
    I["hydrate"] = [stroke(drop), stroke(arc_d(12, 15, 3.7, 128, 196))]
    # 05 GLOW · radiance serum: a sun
    rays = [stroke(f"M{_f(12+6.4*cos(radians(a)))} {_f(12+6.4*sin(radians(a)))} L{_f(12+9*cos(radians(a)))} {_f(12+9*sin(radians(a)))}")
            for a in range(0, 360, 45)]
    I["glow"] = [stroke(circle_d(12, 12, 4.1))] + rays
    # GIFT · lip gloss: lips with a shine
    lips = ("M3.4 12.2 C6.3 8.6 9.4 8.3 12 10.3 C14.6 8.3 17.7 8.6 20.6 12.2 "
            "C17.6 15.9 14.6 17.2 12 17.2 C9.4 17.2 6.4 15.9 3.4 12.2 Z")
    lipline = "M3.4 12.2 C8 12.9 16 12.9 20.6 12.2"
    I["gift"] = [stroke(lips), stroke(lipline), stroke(sparkle_d(19.4, 5.6, 2.0))]
    return I

ICONS = build_icons()

def icon(name, cx, cy, size, color):
    """Product icon centred on (cx, cy); `size` = the 24-unit grid in mm."""
    s = size / 24
    return dict(type="icon", name=name, x=cx - size / 2, y=cy - size / 2, s=s, color=color, sw=ICON_STROKE * s)

def circle(cx, cy, r, stroke=None, sw=0.2, fill=None, id=None):
    return dict(type="circle", cx=cx, cy=cy, r=r, stroke=stroke, sw=sw, fill=fill, id=id)

def medallion(name, cx, cy, r, ink, line_col):
    """Thin circle on the rule with the product icon inside."""
    return [circle(cx, cy, r, stroke=line_col, sw=0.22, id="medallion"), icon(name, cx, cy, r * 1.4, ink)]

# --------------------------------------------------------------------------------------------- flow block
def flow(items, maxw):
    """items: list of (style, text, extra) -> list of lines with relative baselines, plus block height."""
    lines, cur = [], 0.0
    for i, (style, s, gap_after, opts) in enumerate(items):
        st = dict(STYLE[style], **opts)
        cap = M.cap_mm(st["font"], st["size"])
        if style == "name":
            wrapped, size = fit_name(s, maxw); st["size"] = size; cap = M.cap_mm(st["font"], size)
        elif style == "actives":
            wrapped = wrap(s, style, maxw)
        else:
            wrapped = [s]
        for j, ln in enumerate(wrapped):
            base = cur + cap * st["asc"]
            lines.append(dict(style=style, text=ln, baseline=base, size=st["size"], opts=opts))
            cur = base + cap * st["desc"]
            if j < len(wrapped) - 1:
                cur = base + st["size"] * PT * st.get("lh", 1.3) - cap * st["asc"]   # next line top
        cur += gap_after
    height = cur - (items[-1][2] if items else 0)
    return lines, height

def content_items(p):
    step = f"{p['step']} · {p['step_name']}" if p.get("step") else p["step_name"]
    items = [("step", step, 2.8, {})]
    items.append(("name", p["name"], 1.7, {}))
    items.append(("arabic", p["arabic"], 1.6, {}))
    if p.get("descriptor"): items.append(("descriptor", p["descriptor"], 3.4, {}))
    else: items[-1] = ("arabic", p["arabic"], 3.4, {})
    if p.get("actives"): items.append(("actives", p["actives"], 1.9, {}))
    bstyle = "benefits_caps" if p["benefits_style"] == "caps" else "benefits_italic"
    items.append((bstyle, p["benefits"], 0, {}))
    return items

def place_block(lines, height, top, bottom, x, align, ink, flip_rtl=True):
    y0 = top + (bottom - top - height) / 2
    out = []
    for ln in lines:
        rtl = ln["style"] == "arabic"
        out.append(text(x, y0 + ln["baseline"], ln["text"], ln["style"], ink, align=align, size=ln["size"], rtl=rtl,
                        id=ln["style"]))
    return out

# --------------------------------------------------------------------------------------------- lockups
def skin_lockup(cx, top, mark_h, word_w, ink, horizontal=False):
    """Mark over ROVA over S K I N (stacked), centred on cx.  Returns (elements, bottom_y)."""
    els = []
    mk = logo("mark", 0, top, h=mark_h, color=ink); mk["x"] = cx - mk["w"] / 2; els.append(mk)
    y = top + mark_h + mark_h * 0.22
    wm = logo("wordmark", cx - word_w / 2, y, w=word_w, color=ink); els.append(wm)
    rova_h = wm["h"]
    cap = rova_h * 0.125                               # BEAUTY CLINIC sits at ~10 % of the ROVA height
    size_pt = cap / (M.f["syne"]["cap"]) / PT
    base = y + rova_h + rova_h * 0.12 + cap
    els.append(dict(type="text", x=cx, y=base, text="SKIN", font="syne", size=size_pt, track=.48,
                    color=ink, align="center", rtl=False, id="skin"))
    return els, base

# --------------------------------------------------------------------------------------------- layouts
def layout_portrait(p, S, sizes):
    W, H, bleed, safe, r = sizes["portrait"]["w"], sizes["portrait"]["h"], sizes["bleed"], sizes["safe"], sizes["corner_radius"]
    ink, bg, ln, wm = S["ink"], S["bg"], S["line"], S["wm"]
    cx = W / 2
    g = []
    g.append(group("Background", [rect(-bleed, -bleed, W + 2 * bleed, H + 2 * bleed, fill=bg, id="field")]))
    wmk = logo("mark", 33.5, 60.5, h=40, color=wm)
    g.append(group("Watermark", [wmk], clip=(-bleed, -bleed, W + 2 * bleed, H + 2 * bleed)))
    lock, lock_bottom = skin_lockup(cx, 8.0, 11.0, 21.0, ink)
    g.append(group("Logo", lock))
    mr = 4.7                                           # medallion radius
    y1 = lock_bottom + 2.2 + mr
    rules = [line(11, y1, cx - mr - 1.6, y1, ln), line(cx + mr + 1.6, y1, W - 11, y1, ln), line(11, 81.4, W - 11, 81.4, ln)]
    g.append(group("Rules", rules))
    g.append(group("Icon", medallion(p["icon"], cx, y1, mr, ink, ln)))
    lines, hgt = flow(content_items(p), W - 2 * safe - 2)
    body = place_block(lines, hgt, y1 + mr + 2.6, 81.4 - 2.4, cx, "center", ink)
    body.append(text(cx, 85.3, p["size"], "size", ink, align="center", id="size"))
    g.append(group("Text", [b for b in body if b["id"] != "arabic"]))
    g.append(group("Arabic", [b for b in body if b["id"] == "arabic"]))
    g.append(group("Dieline", [
        rect(0, 0, W, H, stroke=MAGENTA, sw=0.1, rx=r, id="CutContour", spot="CutContour"),
        rect(safe, safe, W - 2 * safe, H - 2 * safe, stroke=CYAN, sw=0.08, rx=max(r - safe, 0.5), dash=(1, 1), id="SafeArea"),
    ]))
    return g

def layout_landscape(p, S, sizes):
    W, H, bleed, safe, r = sizes["landscape"]["w"], sizes["landscape"]["h"], sizes["bleed"], sizes["safe"], sizes["corner_radius"]
    ink, bg, ln, wm = S["ink"], S["bg"], S["line"], S["wm"]
    g = []
    g.append(group("Background", [rect(-bleed, -bleed, W + 2 * bleed, H + 2 * bleed, fill=bg, id="field")]))
    wmk = logo("mark", 65.5, 35.0, h=34, color=wm)
    g.append(group("Watermark", [wmk], clip=(-bleed, -bleed, W + 2 * bleed, H + 2 * bleed)))
    # stacked lockup, vertically centred in the left zone
    mark_h, word_w = 11.0, 20.0
    rova_h = word_w * KIT["wordmark"]["h"] / KIT["wordmark"]["w"]
    total = mark_h + mark_h * .22 + rova_h + rova_h * .12 + rova_h * .125
    lcx = 15.5
    lock, lock_bottom = skin_lockup(lcx, (H - total) / 2, mark_h, word_w, ink)
    g.append(group("Logo", lock))
    vx, mr = 32.6, 4.5
    tx, tw = 39.0, W - safe - 39.0 - 1.0
    rules = [line(vx, 10.5, vx, H / 2 - mr - 1.6, ln), line(vx, H / 2 + mr + 1.6, vx, H - 10.5, ln), line(tx, 49.0, W - safe, 49.0, ln)]
    g.append(group("Rules", rules))
    g.append(group("Icon", medallion(p["icon"], vx, H / 2, mr, ink, ln)))
    lines, hgt = flow(content_items(p), tw)
    body = place_block(lines, hgt, 8.5, 49.0 - 2.4, tx, "left", ink)
    body.append(text(W - safe, 53.6, p["size"], "size", ink, align="right", id="size"))
    g.append(group("Text", [b for b in body if b["id"] != "arabic"]))
    g.append(group("Arabic", [b for b in body if b["id"] == "arabic"]))
    g.append(group("Dieline", [
        rect(0, 0, W, H, stroke=MAGENTA, sw=0.1, rx=r, id="CutContour", spot="CutContour"),
        rect(safe, safe, W - 2 * safe, H - 2 * safe, stroke=CYAN, sw=0.08, rx=max(r - safe, 0.5), dash=(1, 1), id="SafeArea"),
    ]))
    return g

# --------------------------------------------------------------------------------------------- SVG writer
def fmt(v): return f"{v:.3f}".rstrip("0").rstrip(".")

def svg_text(e, preview):
    fam, style, weight = FONTS[e["font"]]["prev" if preview else "svg"]
    s = e["text"]; attrs = []
    anchor = {"left": "start", "center": "middle", "right": "end"}[e["align"]]
    if e["rtl"]:
        if preview: s = shape_arabic(s)          # cairo has no shaping engine: pre-shaped, visual order
        else: attrs.append('xml:lang="ar"')      # Illustrator: logical order, shaped by the ME composer
    size_mm = e["size"] * PT
    a = [f'x="{fmt(e["x"])}"', f'y="{fmt(e["y"])}"', f'font-family="{fam}"', f'font-size="{fmt(size_mm)}"']
    if style != "normal": a.append(f'font-style="{style}"')
    if weight != 400: a.append(f'font-weight="{weight}"')
    if e["track"]: a.append(f'letter-spacing="{fmt(e["track"] * size_mm)}"')
    a.append(f'text-anchor="{anchor}"'); a.append(f'fill="{e["color"].hex}"')
    if e.get("id"): a.append(f'id="{e["id"]}"')
    a += attrs
    return f'<text {" ".join(a)}>{html.escape(s)}</text>'

def svg_el(e, preview, defs):
    t = e["type"]
    if t == "group":
        extra = ""
        if e.get("clip"):
            cid = f"clip{len(defs)}"; x, y, w, h = e["clip"]
            defs.append(f'<clipPath id="{cid}"><rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" height="{fmt(h)}"/></clipPath>')
            extra = f' clip-path="url(#{cid})"'
        if preview and e["id"] == "Dieline": return ""
        inner = "".join(svg_el(c, preview, defs) for c in e["children"])
        return f'<g id="{e["id"]}"{extra}>{inner}</g>'
    if t == "rect":
        a = [f'x="{fmt(e["x"])}"', f'y="{fmt(e["y"])}"', f'width="{fmt(e["w"])}"', f'height="{fmt(e["h"])}"']
        if e["rx"]: a.append(f'rx="{fmt(e["rx"])}"')
        a.append(f'fill="{e["fill"].hex if e["fill"] else "none"}"')
        if e["stroke"]:
            a.append(f'stroke="{e["stroke"].hex}" stroke-width="{fmt(e["sw"])}"')
            if e["dash"]: a.append(f'stroke-dasharray="{" ".join(fmt(d) for d in e["dash"])}"')
        if e.get("id"): a.append(f'id="{e["id"]}"')
        return f'<rect {" ".join(a)}/>'
    if t == "line":
        return (f'<line x1="{fmt(e["x1"])}" y1="{fmt(e["y1"])}" x2="{fmt(e["x2"])}" y2="{fmt(e["y2"])}" '
                f'stroke="{e["color"].hex}" stroke-width="{fmt(e["sw"])}" stroke-linecap="round"/>')
    if t == "logo":
        paths = "".join(f'<path d="{d}"/>' for d in KIT[e["name"]]["paths"])
        return (f'<g id="{e["name"]}" fill="{e["color"].hex}" transform="translate({fmt(e["x"])} {fmt(e["y"])}) '
                f'scale({e["s"]:.6f})">{paths}</g>')
    if t == "circle":
        a = [f'cx="{fmt(e["cx"])}"', f'cy="{fmt(e["cy"])}"', f'r="{fmt(e["r"])}"', f'fill="{e["fill"].hex if e["fill"] else "none"}"']
        if e["stroke"]: a.append(f'stroke="{e["stroke"].hex}" stroke-width="{fmt(e["sw"])}"')
        if e.get("id"): a.append(f'id="{e["id"]}"')
        return f'<circle {" ".join(a)}/>'
    if t == "icon":
        parts = []
        for p in ICONS[e["name"]]:
            parts.append(f'<path d="{p["d"]}" fill="{e["color"].hex}" stroke="none"/>' if p["fill"] else f'<path d="{p["d"]}"/>')
        return (f'<g id="icon-{e["name"]}" fill="none" stroke="{e["color"].hex}" stroke-width="{ICON_STROKE}" '
                f'stroke-linecap="round" stroke-linejoin="round" transform="translate({fmt(e["x"])} {fmt(e["y"])}) '
                f'scale({e["s"]:.6f})">{"".join(parts)}</g>')
    if t == "text":
        return svg_text(e, preview)
    raise ValueError(t)

def uniquify_ids(svg):
    seen = {}
    def rep(m):
        i = m.group(1); n = seen.get(i, 0) + 1; seen[i] = n
        return f'id="{i}"' if n == 1 else f'id="{i}-{n}"'
    return re.sub(r'id="([^"]+)"', rep, svg)

def svg_doc(groups, W, H, title, preview=False, rounded=None):
    defs = []
    body = uniquify_ids("".join(svg_el(g, preview, defs) for g in groups))
    if preview and rounded:
        defs.append(f'<clipPath id="trim"><rect x="0" y="0" width="{fmt(W)}" height="{fmt(H)}" rx="{fmt(rounded)}"/></clipPath>')
        body = f'<g clip-path="url(#trim)">{body}</g>'
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{fmt(W)}mm" height="{fmt(H)}mm" viewBox="0 0 {fmt(W)} {fmt(H)}">\n'
            f'<title>{html.escape(title)}</title>\n'
            f'<desc>Rova Skin product sticker. Units: 1 user unit = 1 mm. Trim {fmt(W)} x {fmt(H)} mm, 3 mm bleed drawn outside the '
            f'artboard, 5 mm safe area. Fonts: Georgia, Georgia Italic, Syne Bold, Amiri. Group "Dieline" is non-printing.</desc>\n'
            f'<defs>{"".join(defs)}</defs>\n{body}\n</svg>\n')

# --------------------------------------------------------------------------------------------- PDF writer
def register_pdf_fonts():
    """Georgia cannot be redistributed, so the PDF embeds Gelasio (metric-compatible, OFL) glyphs under the
    PostScript names Georgia / Georgia-Italic: Illustrator then maps the text to the installed Georgia on open."""
    for k, v in FONTS.items():
        if v["pdf"] not in pdfmetrics.getRegisteredFontNames():
            f = RLFont(v["pdf"], P("fonts", v["file"]))
            f.face.name = v["pdf"].encode("latin1")
            pdfmetrics.registerFont(f)

def _path_tokens(d):
    for tok in re.finditer(r'([MLCHVZ])([^MLCHVZ]*)', d):
        yield tok.group(1), [float(v) for v in tok.group(2).split()]

class Pdf:
    def __init__(self, path, title):
        register_pdf_fonts()
        self.c = canvas.Canvas(path, pagesize=(100, 100), initialFontName="Syne-Bold")
        self.c.setTitle(title); self.c.setAuthor("Rova Beauty Clinic / Think and Tinker Studio")
        self.c.setSubject("Rova Skin product stickers, portrait and landscape, CMYK, CutContour dieline")
    def begin(self, W, H, bleed):
        self.W, self.H, self.b = W, H, bleed
        pw, ph = (W + 2 * bleed) * MM, (H + 2 * bleed) * MM
        self.c.setPageSize((pw, ph))
        self.c.setTrimBox((bleed * MM, bleed * MM, (W + bleed) * MM, (H + bleed) * MM))
        self.c.setBleedBox((0, 0, pw, ph))
        self.c.setArtBox((bleed * MM, bleed * MM, (W + bleed) * MM, (H + bleed) * MM))
    def X(self, x): return (x + self.b) * MM
    def Y(self, y): return (self.H + self.b - y) * MM
    def col(self, col, spot=None):
        if spot: return CMYKColorSep(*col.cmyk, spotName=spot)
        return CMYKColor(*col.cmyk)
    def el(self, e):
        c, t = self.c, e["type"]
        if t == "group":
            c.saveState()
            if e.get("clip"):
                x, y, w, h = e["clip"]; p = c.beginPath(); p.rect(self.X(x), self.Y(y + h), w * MM, h * MM); c.clipPath(p, stroke=0, fill=0)
            for ch in e["children"]:
                if e["id"] == "Dieline" and ch.get("id") != "CutContour": continue   # only the spot dieline goes to print
                self.el(ch)
            c.restoreState()
        elif t == "rect":
            x, y, w, h = self.X(e["x"]), self.Y(e["y"] + e["h"]), e["w"] * MM, e["h"] * MM
            if e["fill"]:
                c.setFillColor(self.col(e["fill"]))
                (c.roundRect(x, y, w, h, e["rx"] * MM, stroke=0, fill=1) if e["rx"] else c.rect(x, y, w, h, stroke=0, fill=1))
            if e["stroke"]:
                c.setStrokeColor(self.col(e["stroke"], e.get("spot"))); c.setLineWidth(e["sw"] * MM)
                if e["dash"]: c.setDash([d * MM for d in e["dash"]])
                (c.roundRect(x, y, w, h, e["rx"] * MM, stroke=1, fill=0) if e["rx"] else c.rect(x, y, w, h, stroke=1, fill=0))
                c.setDash([])
        elif t == "line":
            c.setStrokeColor(self.col(e["color"])); c.setLineWidth(e["sw"] * MM); c.setLineCap(1)
            c.line(self.X(e["x1"]), self.Y(e["y1"]), self.X(e["x2"]), self.Y(e["y2"]))
        elif t == "circle":
            if e["fill"]: c.setFillColor(self.col(e["fill"]))
            if e["stroke"]: c.setStrokeColor(self.col(e["stroke"])); c.setLineWidth(e["sw"] * MM)
            c.circle(self.X(e["cx"]), self.Y(e["cy"]), e["r"] * MM, stroke=1 if e["stroke"] else 0, fill=1 if e["fill"] else 0)
        elif t == "icon":
            c.setStrokeColor(self.col(e["color"])); c.setFillColor(self.col(e["color"]))
            c.setLineWidth(e["sw"] * MM); c.setLineCap(1); c.setLineJoin(1)
            for part in ICONS[e["name"]]:
                p = self._path(part["d"], e["x"], e["y"], e["s"])
                c.drawPath(p, stroke=0 if part["fill"] else 1, fill=1 if part["fill"] else 0)
        elif t == "logo":
            c.setFillColor(self.col(e["color"]))
            for d in KIT[e["name"]]["paths"]:
                c.drawPath(self._path(d, e["x"], e["y"], e["s"]), stroke=0, fill=1)
        elif t == "text":
            self._text(e)
    def _path(self, d, ox, oy, s):
        c = self.c
        if True:
            if True:
                p = c.beginPath(); cur = None
                for cmd, a in _path_tokens(d):
                    if cmd == "M": cur = (a[0], a[1]); p.moveTo(self.X(ox + a[0] * s), self.Y(oy + a[1] * s))
                    elif cmd == "L": cur = (a[0], a[1]); p.lineTo(self.X(ox + a[0] * s), self.Y(oy + a[1] * s))
                    elif cmd == "H": cur = (a[0], cur[1]); p.lineTo(self.X(ox + a[0] * s), self.Y(oy + cur[1] * s))
                    elif cmd == "V": cur = (cur[0], a[0]); p.lineTo(self.X(ox + cur[0] * s), self.Y(oy + a[0] * s))
                    elif cmd == "C":
                        p.curveTo(self.X(ox + a[0] * s), self.Y(oy + a[1] * s), self.X(ox + a[2] * s), self.Y(oy + a[3] * s),
                                  self.X(ox + a[4] * s), self.Y(oy + a[5] * s)); cur = (a[4], a[5])
                    elif cmd == "Z": p.close()
                return p
    def _text(self, e):
        c = self.c
        if True:
            font = FONTS[e["font"]]["pdf"]; size = e["size"]
            s = shape_arabic(e["text"]) if e["rtl"] else e["text"]
            w = M.width_mm(s, e["font"], size, e["track"])
            x = {"left": e["x"], "center": e["x"] - w / 2, "right": e["x"] - w}[e["align"]]
            c.setFillColor(self.col(e["color"]))
            to = c.beginText(self.X(x), self.Y(e["y"])); to.setFont(font, size)
            if e["track"]: to.setCharSpace(e["track"] * size)
            to.textOut(s); c.drawText(to)
    def page(self, groups, W, H, bleed):
        self.begin(W, H, bleed)
        for g in groups: self.el(g)
        self.c.showPage()
    def save(self): self.c.save()

# --------------------------------------------------------------------------------------------- logo assets
def write_logo_assets(outdir):
    os.makedirs(outdir, exist_ok=True)
    def doc(els, W, H, name, title):
        open(os.path.join(outdir, name), "w").write(svg_doc([group("Logo", els)], W, H, title))
    doc([logo("mark", 0, 0, h=40, color=BURGUNDY)], KIT["mark"]["w"] / KIT["mark"]["h"] * 40, 40, "rova-mark.svg", "Rova mark")
    doc([logo("wordmark", 0, 0, w=60, color=BURGUNDY)], 60, KIT["wordmark"]["h"] / KIT["wordmark"]["w"] * 60, "rova-wordmark.svg", "Rova wordmark")
    doc([logo("sparkle", 0, 0, w=10, color=BURGUNDY)], 10, 10, "rova-sparkle.svg", "Rova sparkle")
    icons_dir = os.path.join(os.path.dirname(outdir), "icons"); os.makedirs(icons_dir, exist_ok=True)
    for name in ICONS:
        els = [icon(name, 12, 12, 24, BURGUNDY)]
        open(os.path.join(icons_dir, f"icon-{name}.svg"), "w").write(svg_doc([group("Icon", els)], 24, 24, f"Rova Skin icon · {name}"))
        els = medallion(name, 12, 12, 10, BURGUNDY, ROSE)
        open(os.path.join(icons_dir, f"medallion-{name}.svg"), "w").write(svg_doc([group("Icon", els)], 24, 24, f"Rova Skin medallion · {name}"))
    els, bottom = skin_lockup(20, 1, 20, 36, BURGUNDY)
    doc(els, 40, bottom + 1.5, "rova-skin-stacked.svg", "Rova Skin lockup, stacked")
    els, bottom = skin_lockup(20, 1, 20, 36, IVORY)
    doc([rect(0, 0, 40, bottom + 1.5, fill=BURGUNDY)] + els, 40, bottom + 1.5, "rova-skin-stacked-on-burgundy.svg", "Rova Skin lockup, stacked, ivory")

# --------------------------------------------------------------------------------------------- previews
def render_png(svg_str, out, dpi=300):
    cairosvg.svg2png(bytestring=svg_str.encode("utf-8"), write_to=out, dpi=dpi)

def contact_sheet(items, out, title):
    """items: list of (png_path, caption, orientation) laid out in two rows (portrait, landscape)."""
    scale = 4.2  # px per mm at sheet scale
    pad, gap, cap_h, head = 70, 34, 64, 150
    rows = {"portrait": [i for i in items if i[2] == "portrait"], "landscape": [i for i in items if i[2] == "landscape"]}
    row_w = {k: sum(int((60 if k == "portrait" else 90) * scale) for _ in v) + gap * (len(v) - 1) for k, v in rows.items()}
    Wpx = max(row_w.values()) + 2 * pad
    Hpx = head + int(90 * scale) + cap_h + gap * 2 + int(60 * scale) + cap_h + pad
    im = Image.new("RGB", (Wpx, Hpx), "#F4EDE5"); d = ImageDraw.Draw(im)
    f_title = ImageFont.truetype(P("fonts", "Gelasio-Regular.ttf"), 54)
    f_sub = ImageFont.truetype(P("fonts", "Syne-Bold.ttf"), 17)
    f_cap = ImageFont.truetype(P("fonts", "Syne-Bold.ttf"), 13)
    f_cap2 = ImageFont.truetype(P("fonts", "Gelasio-Regular.ttf"), 19)
    d.text((pad, 44), title, font=f_title, fill=BURGUNDY.hex)
    d.text((pad, 112), "P O R T R A I T   6 0 × 9 0 M M     ·     L A N D S C A P E   9 0 × 6 0 M M     ·     3 M M  B L E E D ,  5 M M  S A F E  A R E A", font=f_sub, fill="#8A6F6B")
    y = head
    for k in ("portrait", "landscape"):
        x = pad
        for png, caption, _ in rows[k]:
            s = Image.open(png).convert("RGBA")
            w_mm, h_mm = (60, 90) if k == "portrait" else (90, 60)
            s = s.resize((int(w_mm * scale), int(h_mm * scale)), Image.LANCZOS)
            sh = Image.new("RGBA", (s.width + 16, s.height + 16), (0, 0, 0, 0))
            ImageDraw.Draw(sh).rounded_rectangle((8, 10, s.width + 8, s.height + 10), radius=int(3 * scale), fill=(60, 18, 25, 26))
            im.paste(sh, (x - 8, y - 6), sh)
            im.paste(s, (x, y), s)
            l1, l2 = caption
            d.text((x, y + s.height + 12), l1, font=f_cap, fill="#8A6F6B")
            d.text((x, y + s.height + 32), l2, font=f_cap2, fill=BURGUNDY.hex)
            x += s.width + gap
        y += (int(90 * scale) if k == "portrait" else int(60 * scale)) + cap_h + gap
    im.save(out, optimize=True)

# --------------------------------------------------------------------------------------------- main
def main():
    spec = json.load(open(P("spec", "products.json")))
    sizes = spec["sizes_mm"]
    out_svg = {"portrait": P("stickers", "portrait"), "landscape": P("stickers", "landscape")}
    for v in out_svg.values(): os.makedirs(v, exist_ok=True)
    os.makedirs(P("previews"), exist_ok=True)
    pdf = Pdf(P("Rova-Skin-Stickers.pdf"), "Rova Skin · Product Stickers · 6 products × portrait + landscape")
    sheet = []
    manifest = []
    for orient, layout in (("portrait", layout_portrait), ("landscape", layout_landscape)):
        W, H = sizes[orient]["w"], sizes[orient]["h"]
        for p in spec["products"]:
            S = scheme(p["field"])
            groups = layout(p, S, sizes)
            title = f"Rova Skin · {p['step_name'].title()} · {p['name'].title()} · {orient} {W}×{H} mm"
            fname = f"{p['id']}-{W}x{H}.svg"
            open(os.path.join(out_svg[orient], fname), "w", encoding="utf-8").write(svg_doc(groups, W, H, title))
            png = P("previews", f"{p['id']}-{orient}.png")
            render_png(svg_doc(groups, W, H, title, preview=True, rounded=sizes["corner_radius"]), png, dpi=300)
            pdf.page(groups, W, H, sizes["bleed"])
            sheet.append((png, (f"{p['step'] + ' · ' if p.get('step') else ''}{p['step_name']}   ·   {p['field'].upper()} FIELD", p["name"].title()), orient))
            manifest.append(dict(id=p["id"], orientation=orient, svg=f"stickers/{orient}/{fname}", field=p["field"]))
            print(f"  {orient:9s} {fname}")
    pdf.save()
    with open(P("Rova-Skin-Stickers.pdf"), "rb") as src, open(P("Rova-Skin-Stickers.ai"), "wb") as dst: dst.write(src.read())
    write_logo_assets(P("assets", "logo"))
    contact_sheet(sheet, P("previews", "contact-sheet.png"), "Rova Skin  ·  Product Stickers")
    json.dump(manifest, open(P("spec", "manifest.json"), "w"), indent=1)
    print("done:", len(manifest), "stickers")

if __name__ == "__main__":
    main()

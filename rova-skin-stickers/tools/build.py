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
    lock, lock_bottom = skin_lockup(cx, 8.6, 12.0, 22.0, ink)
    g.append(group("Logo", lock))
    y1 = lock_bottom + 4.0
    sp = logo("sparkle", cx - 1.1, y1 - 1.1, w=2.2, color=ln)
    rules = [line(12, y1, cx - 3.2, y1, ln), sp, line(cx + 3.2, y1, W - 12, y1, ln), line(12, 81.0, W - 12, 81.0, ln)]
    g.append(group("Rules", rules))
    lines, hgt = flow(content_items(p), W - 2 * safe - 2)
    body = place_block(lines, hgt, y1 + 3.2, 81.0 - 2.6, cx, "center", ink)
    body.append(text(cx, 85.0, p["size"], "size", ink, align="center", id="size"))
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
    lcx = 16.5
    lock, lock_bottom = skin_lockup(lcx, (H - total) / 2, mark_h, word_w, ink)
    g.append(group("Logo", lock))
    vx = 32.0
    sp = logo("sparkle", vx - 1.1, H / 2 - 1.1, w=2.2, color=ln)
    tx, tw = 37.0, W - safe - 37.0 - 1.0
    rules = [line(vx, 11, vx, H / 2 - 3.2, ln), sp, line(vx, H / 2 + 3.2, vx, H - 11, ln), line(tx, 49.0, W - safe, 49.0, ln)]
    g.append(group("Rules", rules))
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
        elif t == "logo":
            c.setFillColor(self.col(e["color"]))
            s = e["s"]; ox, oy = e["x"], e["y"]
            for d in KIT[e["name"]]["paths"]:
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
                c.drawPath(p, stroke=0, fill=1)
        elif t == "text":
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

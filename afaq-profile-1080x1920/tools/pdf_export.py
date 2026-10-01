#!/usr/bin/env python3
"""Spec → vector PDF with embedded Inter fonts and editable text (ReportLab).

Illustrator opens the result as fully editable artwork (paths, gradients, live point text), so the
same file is shipped twice: `.pdf` and `.ai` (an .ai file is a PDF container; Illustrator opens it
directly, treating it as PDF content). Coordinates are 1 px = 1 pt so artboards read 1920 x 1080 px.
"""
import os
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor

PS = {300: "Inter-Light", 400: "Inter-Regular", 500: "Inter-Medium", 600: "Inter-SemiBold", 700: "Inter-Bold"}
FILES = {300: "Inter-Light.ttf", 400: "Inter-Regular.ttf", 500: "Inter-Medium.ttf", 600: "Inter-SemiBold.ttf", 700: "Inter-Bold.ttf"}

def register_fonts(font_dir):
    for w, name in PS.items():
        path = os.path.join(font_dir, FILES[w])
        if os.path.exists(path) and name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(name, path))

def _tokens(d):
    toks = d.replace(",", " ").split()
    i = 0
    while i < len(toks):
        t = toks[i]
        if t == "M" or t == "L":
            yield t, [float(toks[i + 1]), float(toks[i + 2])]; i += 3
        elif t == "C":
            yield t, [float(v) for v in toks[i + 1:i + 7]]; i += 7
        elif t == "Z":
            yield t, []; i += 1
        else:
            raise ValueError(f"unsupported path token {t}")

class PdfWriter:
    def __init__(self, path, width, height, title, baseline_fn):
        self.W, self.H = width, height
        self.c = canvas.Canvas(path, pagesize=(width, height), initialFontName="Inter-Regular")  # no stray Helvetica reference
        self.c.setTitle(title)
        self.c.setAuthor("AFAQ for Energy & Integrated Business")
        self.baseline = baseline_fn

    def y(self, v):
        return self.H - v

    def path_obj(self, d):
        p = self.c.beginPath()
        for cmd, a in _tokens(d):
            if cmd == "M": p.moveTo(a[0], self.y(a[1]))
            elif cmd == "L": p.lineTo(a[0], self.y(a[1]))
            elif cmd == "C": p.curveTo(a[0], self.y(a[1]), a[2], self.y(a[3]), a[4], self.y(a[5]))
            else: p.close()
        return p

    def fill_with(self, fill, draw_shape, draw_clip):
        """Solid → draw_shape(fill=1). Gradient → clip to the shape and paint the gradient through it."""
        c = self.c
        if isinstance(fill, str):
            c.setFillColor(HexColor(fill)); draw_shape(True)
        else:
            c.saveState()
            draw_clip()
            colors = [HexColor(col) for _, col, _ in fill["stops"]]
            positions = [o for o, _, _ in fill["stops"]]
            c.linearGradient(fill["x1"], self.y(fill["y1"]), fill["x2"], self.y(fill["y2"]), colors, positions=positions, extend=True)
            c.restoreState()

    def el(self, e):
        c = self.c
        t = e["type"]
        if t == "group":
            for ch in e["children"]: self.el(ch)
            return
        op = e.get("opacity", 1)
        c.saveState()
        c.setFillAlpha(op); c.setStrokeAlpha(op)
        if t == "rect":
            x, yb, w, h, r = e["x"], self.y(e["y"] + e["h"]), e["w"], e["h"], e.get("rx") or 0
            if e.get("fill"):
                self.fill_with(e["fill"], lambda f: c.roundRect(x, yb, w, h, r, stroke=0, fill=1),
                               lambda: (lambda p: (p.roundRect(x, yb, w, h, r), c.clipPath(p, stroke=0, fill=0)))(c.beginPath()))
            if e.get("stroke"):
                c.setStrokeColor(HexColor(e["stroke"])); c.setLineWidth(e["sw"] or 1); c.roundRect(x, yb, w, h, r, stroke=1, fill=0)
        elif t == "circle":
            cx, cy, r = e["cx"], self.y(e["cy"]), e["r"]
            if e.get("fill"):
                self.fill_with(e["fill"], lambda f: c.circle(cx, cy, r, stroke=0, fill=1),
                               lambda: (lambda p: (p.circle(cx, cy, r), c.clipPath(p, stroke=0, fill=0)))(c.beginPath()))
            if e.get("stroke"):
                c.setStrokeColor(HexColor(e["stroke"])); c.setLineWidth(e["sw"] or 1); c.circle(cx, cy, r, stroke=1, fill=0)
        elif t == "path":
            if e.get("fill"):
                self.fill_with(e["fill"], lambda f: c.drawPath(self.path_obj(e["d"]), stroke=0, fill=1),
                               lambda: c.clipPath(self.path_obj(e["d"]), stroke=0, fill=0))
            if e.get("stroke"):
                c.setStrokeColor(HexColor(e["stroke"])); c.setLineWidth(e["sw"] or 1)
                c.setLineCap({"round": 1, "butt": 0, "square": 2}.get(e.get("cap", "round"), 1))
                c.setLineJoin({"round": 1, "miter": 0, "bevel": 2}.get(e.get("join", "round"), 1))
                c.drawPath(self.path_obj(e["d"]), stroke=1, fill=0)
        elif t == "text":
            size, lh, ls = e["size"], e["lh"], e.get("ls") or 0
            font = PS[e["weight"]]
            c.setFillColor(HexColor(e["color"]))
            b = self.baseline(size, lh)
            for i, line in enumerate(e["lines"]):
                width = pdfmetrics.stringWidth(line, font, size) + ls * size * max(len(line) - 1, 0)
                if e["align"] == "right": x = e["x"] + e["w"] - width
                elif e["align"] == "center": x = e["x"] + e["w"] / 2 - width / 2
                else: x = e["x"]
                to = c.beginText(x, self.y(e["y"] + b + i * lh))
                to.setFont(font, size)
                if ls: to.setCharSpace(ls * size)
                to.textOut(line)
                c.drawText(to)
        c.restoreState()

    def page(self, elements):
        for e in elements: self.el(e)
        self.c.showPage()

    def save(self):
        self.c.save()

def write_pdf(slides, width, height, path, title, font_dir, baseline_fn):
    register_fonts(font_dir)
    w = PdfWriter(path, width, height, title, baseline_fn)
    for s in slides: w.page(s["elements"])
    w.save()
    ai = os.path.splitext(path)[0] + ".ai"
    with open(path, "rb") as src, open(ai, "wb") as dst: dst.write(src.read())
    return path, ai

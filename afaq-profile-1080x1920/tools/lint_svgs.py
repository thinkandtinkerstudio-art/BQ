#!/usr/bin/env python3
"""Import-safety lint for the page/asset SVGs (Figma + Illustrator).

Fails on anything that is known to import as black fills, broken masks or rasters:
<style>/class/CSS vars, currentColor, <mask>, <clipPath>, <use>/<symbol>, <filter>, <image>,
<foreignObject>, transform attributes, relative/arc path commands, text without explicit font
attributes or fill, missing fills, duplicate ids, wrong page size.
"""
import re, sys, glob, os
import xml.etree.ElementTree as ET

NS = "{http://www.w3.org/2000/svg}"
FORBIDDEN_TAGS = {"style", "mask", "clipPath", "use", "symbol", "filter", "image", "foreignObject", "pattern", "script", "switch", "marker"}
ALLOWED_TAGS = {"svg", "defs", "linearGradient", "stop", "g", "rect", "circle", "path", "text"}
PATH_RE = re.compile(r"^[MLCZ0-9\s\.\-]+$")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

def lint(path, expect_size=None):
    errs = []
    raw = open(path, encoding="utf-8").read()
    if "class=" in raw: errs.append("class attribute present")
    if "var(" in raw or "currentColor" in raw: errs.append("CSS variable / currentColor present")
    root = ET.fromstring(raw)
    if expect_size and (root.get("width"), root.get("height"), root.get("viewBox")) != (str(expect_size[0]), str(expect_size[1]), f"0 0 {expect_size[0]} {expect_size[1]}"):
        errs.append(f"size mismatch: {root.get('width')}x{root.get('height')} viewBox={root.get('viewBox')}")
    ids = {}
    grad_ids = {g.get("id") for g in root.iter(NS + "linearGradient")}
    for el in root.iter():
        tag = el.tag.replace(NS, "")
        if tag in FORBIDDEN_TAGS: errs.append(f"forbidden element <{tag}>")
        elif tag not in ALLOWED_TAGS: errs.append(f"unexpected element <{tag}>")
        if el.get("transform") is not None: errs.append(f"transform attribute on <{tag} id={el.get('id')}>")
        if el.get("style") is not None: errs.append(f"style attribute on <{tag} id={el.get('id')}>")
        i = el.get("id")
        if i:
            if i in ids: errs.append(f"duplicate id {i}")
            ids[i] = 1
            if " " in i: errs.append(f"id with space: {i}")
        if tag in ("rect", "circle", "path"):
            fill = el.get("fill")
            if fill is None: errs.append(f"<{tag} id={i}> has no explicit fill")
            elif fill.startswith("url("):
                if fill[5:-1] not in grad_ids: errs.append(f"<{tag} id={i}> references missing gradient {fill}")
            elif fill != "none" and not HEX_RE.match(fill): errs.append(f"<{tag} id={i}> non-hex fill {fill}")
            if fill == "none" and el.get("stroke") is None: errs.append(f"<{tag} id={i}> invisible (fill none, no stroke)")
            st = el.get("stroke")
            if st and not HEX_RE.match(st): errs.append(f"<{tag} id={i}> non-hex stroke {st}")
        if tag == "path":
            d = el.get("d", "")
            if not PATH_RE.match(d): errs.append(f"<path id={i}> uses commands other than absolute M/L/C/Z")
        if tag == "text":
            for a in ("font-family", "font-size", "font-weight", "fill"):
                if el.get(a) is None: errs.append(f"<text id={i}> missing {a}")
            if el.get("font-family") != "Inter": errs.append(f"<text id={i}> font-family {el.get('font-family')}")
            if not (el.text or "").strip(): errs.append(f"<text id={i}> empty")
            if len(el): errs.append(f"<text id={i}> has child elements (tspan) — keep one <text> per line")
    counts = {"text": len(list(root.iter(NS + "text"))), "path": len(list(root.iter(NS + "path"))),
              "rect": len(list(root.iter(NS + "rect"))), "circle": len(list(root.iter(NS + "circle"))),
              "gradients": len(grad_ids)}
    return errs, counts

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/home/user/BQ/afaq-profile-1080x1920"
    total = 0
    for f in sorted(glob.glob(os.path.join(out, "pages", "*.svg"))):
        errs, counts = lint(f, (1080, 1920))
        total += len(errs)
        print(("OK  " if not errs else "FAIL"), os.path.relpath(f, out), counts)
        for e in errs: print("     -", e)
    for f in sorted(glob.glob(os.path.join(out, "assets", "**", "*.svg"), recursive=True)):
        errs, counts = lint(f)
        total += len(errs)
        if errs:
            print("FAIL", os.path.relpath(f, out)); [print("     -", e) for e in errs]
    print(f"\n{'ALL CLEAN' if total == 0 else str(total) + ' problem(s)'}")
    sys.exit(1 if total else 0)

if __name__ == "__main__":
    main()

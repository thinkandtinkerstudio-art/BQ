#!/usr/bin/env python3
"""Import-safety lint for the page/asset SVGs (Figma + Illustrator).

Fails on anything that is known to import as black fills, broken masks or rasters:
<style>/class/CSS vars, currentColor, <mask>, <clipPath>, <use>/<symbol>, <filter>, <image>,
<foreignObject>, transform attributes, relative/arc path commands, text without explicit font
attributes or fill, missing fills, duplicate ids, wrong page size.
"""
import re, sys, glob, os, json
import xml.etree.ElementTree as ET

NS = "{http://www.w3.org/2000/svg}"
FORBIDDEN_TAGS = {"style", "mask", "clipPath", "use", "symbol", "filter", "image", "foreignObject", "pattern", "script", "switch", "marker"}
ALLOWED_TAGS = {"svg", "defs", "linearGradient", "stop", "g", "rect", "circle", "path", "text"}
PATH_RE = re.compile(r"^[MLCZ0-9\s\.\-]+$")
HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

def lint(path, expect_size=None, ps_names=False):
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
            fam = el.get("font-family")
            ok = fam in ("Inter-Light", "Inter-Regular", "Inter-Medium", "Inter-SemiBold") if ps_names else fam == "Inter"
            if not ok: errs.append(f"<text id={i}> font-family {fam}")
            if not (el.text or "").strip(): errs.append(f"<text id={i}> empty")
            if len(el): errs.append(f"<text id={i}> has child elements (tspan) — keep one <text> per line")
    counts = {"text": len(list(root.iter(NS + "text"))), "path": len(list(root.iter(NS + "path"))),
              "rect": len(list(root.iter(NS + "rect"))), "circle": len(list(root.iter(NS + "circle"))),
              "gradients": len(grad_ids)}
    return errs, counts

def bounds_lint(path):
    """Everything except ribbons must stay on the canvas; text must stay inside the 72 px margins."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from deck import text_width
    errs = []
    root = ET.fromstring(open(path, encoding="utf-8").read())
    W, H = int(root.get("width")), int(root.get("height"))
    M = 96 if W > H else 72
    def pb(d, pad):
        nums = [float(t) for t in re.sub(r"[MLCZ]", " ", d).split()]
        return min(nums[0::2]) - pad, min(nums[1::2]) - pad, max(nums[0::2]) + pad, max(nums[1::2]) + pad
    for el in root.iter():
        tag = el.tag.replace(NS, ""); i = el.get("id", "")
        if i.startswith(("Ribbon", "Deco")):
            continue
        if tag == "rect":
            b = (float(el.get("x")), float(el.get("y")), float(el.get("x")) + float(el.get("width")), float(el.get("y")) + float(el.get("height")))
        elif tag == "circle":
            cx, cy, r = (float(el.get(a)) for a in ("cx", "cy", "r")); b = (cx - r, cy - r, cx + r, cy + r)
        elif tag == "path":
            b = pb(el.get("d"), float(el.get("stroke-width", 0)) / 2)
        elif tag == "text":
            size = float(el.get("font-size")); wt = int(el.get("font-weight")); ls = float(el.get("letter-spacing", 0)) / size
            wdt = text_width(el.text or "", size, wt, ls); ax = float(el.get("x")); anchor = el.get("text-anchor", "start")
            x0 = ax if anchor == "start" else (ax - ls * size - wdt if anchor == "end" else ax - wdt / 2)
            x1 = x0 + wdt
            if x0 < M - 2 or x1 > W - M + 2:
                errs.append(f"<text id={i}> runs outside the 72px margins: {round(x0)}..{round(x1)}")
            continue
        else:
            continue
        if b[0] < -0.5 or b[1] < -0.5 or b[2] > W + 0.5 or b[3] > H + 0.5:
            errs.append(f"<{tag} id={i}> leaves the canvas: {tuple(round(v) for v in b)}")
    return errs

def figma_scripts_lint(out):
    """The embedded SPEC in figma/slides/*.js must match spec/deck-spec.json (same slide names, same element counts)."""
    errs = []
    for sub in ("", "landscape"):
        errs += _figma_scripts_lint(os.path.join(out, sub) if sub else out)
    return errs

def _figma_scripts_lint(out):
    errs = []
    if not os.path.exists(os.path.join(out, "spec", "deck-spec.json")):
        return errs
    spec = json.load(open(os.path.join(out, "spec", "deck-spec.json")))
    def count(els):
        return sum(count(e["children"]) if e["type"] == "group" else 1 for e in els)
    for i, s in enumerate(spec["slides"]):
        f = os.path.join(out, "figma", "slides", f"slide-{i + 1:02d}.js")
        if not os.path.exists(f):
            errs.append(f"missing {f}"); continue
        src = open(f, encoding="utf-8").read()
        m = re.search(r"const SPEC = (\{.*?\});\n", src, flags=re.S)
        emb = json.loads(m.group(1))
        if emb["slides"][0]["name"] != s["name"] or count(emb["slides"][0]["elements"]) != count(s["elements"]):
            errs.append(f"{os.path.basename(f)} is out of sync with spec/deck-spec.json")
        if len(src) > 50000:
            errs.append(f"{os.path.basename(f)} exceeds the 50k use_figma limit ({len(src)} chars)")
    return errs

def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "/home/user/BQ/afaq-profile-1080x1920"
    total = 0
    page_sets = [(os.path.join(out, "pages"), (1080, 1920)), (os.path.join(out, "pages-illustrator"), (1080, 1920)),
                 (os.path.join(out, "landscape", "pages"), (1920, 1080)), (os.path.join(out, "landscape", "pages-illustrator"), (1920, 1080))]
    for folder, size in page_sets:
        for f in sorted(glob.glob(os.path.join(folder, "*.svg"))):
            errs, counts = lint(f, size, ps_names="pages-illustrator" in f)
            errs += bounds_lint(f)
            total += len(errs)
            print(("OK  " if not errs else "FAIL"), os.path.relpath(f, out), counts)
            for e in errs: print("     -", e)
    for f in []:
        errs, counts = lint(f)
        total += len(errs)
        print(("OK  " if not errs else "FAIL"), os.path.relpath(f, out), counts)
        for e in errs: print("     -", e)
    for f in sorted(glob.glob(os.path.join(out, "assets", "**", "*.svg"), recursive=True)):
        errs, counts = lint(f)
        total += len(errs)
        if errs:
            print("FAIL", os.path.relpath(f, out)); [print("     -", e) for e in errs]
    fe = figma_scripts_lint(out)
    total += len(fe)
    for e in fe: print("FAIL figma:", e)
    print(f"\n{'ALL CLEAN' if total == 0 else str(total) + ' problem(s)'}")
    sys.exit(1 if total else 0)

if __name__ == "__main__":
    main()

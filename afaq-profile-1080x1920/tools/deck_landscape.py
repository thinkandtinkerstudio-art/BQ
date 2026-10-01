#!/usr/bin/env python3
"""Landscape (1920x1080) edition of the AFAQ deck, built from the same brand kit as deck.py.

Writes landscape/pages, landscape/pages-illustrator, landscape/spec, landscape/figma, and the
editable-vector PDF/AI files for BOTH orientations (tools/pdf_export.py).
"""
import json, os
import deck as D
from deck import (T, R, C, PATH, LINE, G, LIN, P, lockup, ribbon, dark_ribbon_fill, photo_slot, icon,
                  rounded_polygon, svg_of, write, slim, text_width, baseline, STYLE_NAMES, ASC, DESC)
from pdf_export import write_pdf

ROOT = D.OUT
OUT = os.path.join(ROOT, "landscape")
W, H, M = 1920, 1080, 96
CW = W - 2 * M          # 1728
FOOT_Y = 1000
BOTTOM = 960

# ---------------------------------------------------------------- shared parts (landscape metrics)
def header(dark, eyebrow_color=None, eyebrow_opacity=None):
    col = P["cream"] if dark else P["teal_ink"]
    sub = eyebrow_color or (P["cream"] if dark else P["muted"])
    lock, _ = lockup(M, 56, 48, col)
    eyebrow = T("Eyebrow", W - M - 420, 70, 420, "Corporate Profile 2026", 14, 500, sub, lh=20, ls=0.22, align="right",
                case="upper", opacity=eyebrow_opacity if eyebrow_opacity is not None else (0.85 if dark else 1.0))
    return G("Header", [lock, eyebrow])

def footer(section, n, dark, color=None, rule_opacity=None, text_opacity=None):
    col = color or (P["cream"] if dark else P["muted"])
    rule = LINE("Footer-Rule", M, FOOT_Y, W - M, FOOT_Y, color or (P["cream"] if dark else P["line"]), 1,
                opacity=rule_opacity if rule_opacity is not None else (0.25 if dark else 1.0))
    top = text_opacity if text_opacity is not None else (0.75 if dark else 1.0)
    return G("Footer", [rule,
                        T("Footer-Section", M, 1018, 700, section, 15, 400, col, lh=20, opacity=top),
                        T("Footer-Page", W - M - 200, 1018, 200, f"{n:02d} / 08", 15, 500, col, lh=20, align="right", opacity=top)])

def title(text, dark, y=190, size=64, color=None, w=1100):
    return T("Title", M, y, w, text, size, 300, color or (P["cream"] if dark else P["teal"]), lh=round(size * 1.1), ls=-0.02)

def subtitle(text, dark, y, w=1000, color=None, opacity=None):
    return T("Subtitle", M, y, w, text, 22, 400, color or (P["cream"] if dark else P["muted"]), lh=32,
             opacity=opacity if opacity is not None else (0.85 if dark else 1.0))

# ---------------------------------------------------------------- slides
def slide_cover():
    els = [R("Background", 0, 0, W, H, P["cream"])]
    lock, _ = lockup(M, 96, 96, P["teal_ink"])
    els.append(lock)
    els.append(T("Eyebrow", M, 292, 600, "Corporate Profile 2026", 16, 500, P["muted"], lh=22, ls=0.22, case="upper"))
    head = T("Headline", M, 340, 880, "AFAQ for Energy\n& Integrated Business", 80, 300, P["teal"], lh=88, ls=-0.025)
    els.append(head)
    y = 340 + head["h"] + 36
    els.append(R("Accent-Rule", M, y, 64, 6, P["orange"], rx=3))
    slog = T("Slogan", M, y + 24, 880, "Innovating today, sustaining tomorrow", 34, 300, P["teal"], lh=42)
    els.append(slog)
    els.append(T("Scope", M, y + 24 + slog["h"] + 16, 760, "Solar power and energy storage in the Sultanate of Oman", 22, 400, P["muted"], lh=32))
    px, py, pw, ph = 1056, 96, 768, 760
    notch = {"corner": "tr", "w": 248, "h": 104, "r": 20}
    els.append(photo_slot("Photo-Hero", px, py, pw, ph, 36, notch))
    tab_x, tab_y, tab_w, tab_h = px + pw - 232, py, 232, 90
    els.append(G("Label-Tab", [
        R("Label-Tab-Shape", tab_x, tab_y, tab_w, tab_h, P["orange"], rx=20),
        T("Label-Tab-Text", tab_x + 24, tab_y + 16, tab_w - 48, "SOLAR\nSTORAGE\nELECTRICAL", 13, 500, P["teal_ink"], lh=19, ls=0.18),
    ]))
    pts = [(-60, 900), (300, 920), (560, 840), (900, 860), (1240, 890), (1500, 980), (1980, 900)]
    els.append(ribbon("Ribbon", pts, 80))
    return {"name": "01 Cover", "bg": P["cream"], "elements": els}

def slide_about():
    dark = True
    els = [R("Background", 0, 0, W, H, P["teal"]), header(dark)]
    t = title("About AFAQ", dark)
    els.append(t)
    els.append(R("Accent-Rule", M, 190 + t["h"] + 18, 72, 6, P["lime"], rx=3))
    y = 190 + t["h"] + 18 + 6 + 36
    paras = [
        "AFAQ for Energy & Integrated Business is an Omani company based in Muscat. It works in solar power, energy storage and the electrical systems that go with them.",
        "The company designs photovoltaic systems, supplies their components, installs them and brings them into operation, at sizes ranging from building systems to project plants.",
        "AFAQ works directly with facility owners, and with contractors and developers inside their own projects.",
    ]
    for i, p in enumerate(paras):
        el = T(f"Body-{i + 1}", M, y, 820, p, 23, 400, P["cream"], lh=35, opacity=0.9)
        els.append(el)
        y += el["h"] + 22
    px, py, pw, ph = 1016, 160, 808, 760
    notch = {"corner": "bl", "w": 300, "h": 136, "r": 20}
    els.append(photo_slot("Photo-Site", px, py, pw, ph, 36, notch, dark=True, art="storage"))
    tab_w, tab_h = 284, 120
    tab_x, tab_y = px, py + ph - tab_h
    els.append(G("Services-Tab", [
        R("Services-Tab-Shape", tab_x, tab_y, tab_w, tab_h, P["lime"], rx=20),
        T("Services-Tab-Text", tab_x + 24, tab_y + 18, tab_w - 48, "SOLAR\nSTORAGE\nELECTRICAL\nENGINEERING", 13, 500, P["teal"], lh=20, ls=0.18),
    ]))
    els.append(footer("About AFAQ", 2, dark))
    return {"name": "02 About AFAQ", "bg": P["teal"], "elements": els}

def slide_components():
    dark = False
    els = [R("Background", 0, 0, W, H, P["cream"]), header(dark)]
    t = title("System components", dark)
    els.append(t)
    sub = subtitle("A photovoltaic system is built from four components. AFAQ holds a direct supply agreement with a main supplier for each.", dark, 190 + t["h"] + 16)
    els.append(sub)
    comps = [
        ("01", "PV modules", "Selected according to the mounting area available and the conditions on site.", "Main suppliers", "AACE · Ronma", "pv-module"),
        ("02", "Battery energy storage", "Sized on the loads to be covered and the autonomy required.", "Main supplier", "Goshin", "battery"),
        ("03", "Inverters and power conversion", "Selected according to the array configuration and the connection requirements of the grid operator.", "Main supplier", "Star Charge", "inverter"),
        ("04", "Plant infrastructure", "Mounting structures, foundations, DC and AC cabling, and connection and protection panels, specified to suit the site.", None, None, "infrastructure"),
    ]
    y0 = 190 + t["h"] + 16 + sub["h"] + 44
    gap = 24
    cw = (CW - gap) / 2
    ch = (BOTTOM - y0 - gap) / 2
    for i, (num, name, note, lab, sup, ic) in enumerate(comps):
        x = M + (i % 2) * (cw + gap)
        y = y0 + (i // 2) * (ch + gap)
        kids = [R("Card-Shape", x, y, cw, ch, P["white"], rx=24),
                T("Number", x + 36, y + 28, 80, num, 20, 600, P["orange_deep"], lh=26),
                C("Icon-Disc", x + cw - 36 - 34, y + 28 + 34, 34, P["lime"]),
                icon("Icon", ic, x + cw - 36 - 34 - 20, y + 28 + 34 - 20, 40, P["teal"]),
                T("Card-Title", x + 36, y + 62, 620, name, 26, 600, P["teal"], lh=34)]
        note_el = T("Card-Note", x + 36, y + 104, 620, note, 19, 400, P["muted"], lh=28)
        kids.append(note_el)
        if lab:
            ly = y + 104 + note_el["h"] + 12
            kids.append(T("Supplier-Label", x + 36, ly, 400, lab, 12, 500, P["muted"], lh=16, ls=0.16, case="upper"))
            kids.append(T("Supplier", x + 36, ly + 20, 600, sup, 19, 500, P["teal"], lh=26))
        els.append(G(f"Card-{num}", kids))
    els.append(footer("System components", 3, dark))
    return {"name": "03 System components", "bg": P["cream"], "elements": els}

def slide_scope():
    els = [R("Background", 0, 0, W, H, P["lime"]), header(False, eyebrow_color=P["teal"], eyebrow_opacity=0.8)]
    t = title("Scope of work", False)
    els.append(t)
    sub = subtitle("The project sets the scope, from supply alone to full operation.", False, 190 + t["h"] + 16, color=P["teal"], opacity=0.85)
    els.append(sub)
    steps = [
        ("01", "Study and design", "Load analysis and consumption data, a site survey, system sizing and placement, and the expected annual yield.", "A report covering system capacity, expected annual yield and estimated cost."),
        ("02", "Supply", "PV modules, batteries, inverters and electrical equipment, with manufacturer warranties.", "A component list with specifications, source and warranty terms."),
        ("03", "Installation and connection", "Installation, electrical works, and grid-tied, off-grid or hybrid connection.", "A working system and a testing and commissioning record."),
        ("04", "Operation and monitoring", "Performance monitoring and maintenance under an operation and maintenance contract.", "A performance report comparing actual output against the design figure."),
    ]
    gap = 32
    colw = (CW - 3 * gap) / 4
    # shared heights so the four columns align
    titles = [T("m", 0, 0, colw, s[1], 28, 600, "#000000", lh=36) for s in steps]
    bodies = [T("m", 0, 0, colw, s[2], 20, 400, "#000000", lh=30) for s in steps]
    delivs = [T("m", 0, 0, colw - 48, s[3], 18, 400, "#000000", lh=26) for s in steps]
    th, bh, dh = max(x["h"] for x in titles), max(x["h"] for x in bodies), max(x["h"] for x in delivs)
    box_h = 40 + dh + 18
    block_h = 72 + th + 10 + bh + 16 + box_h
    sub_end = 190 + t["h"] + 16 + sub["h"]
    y0 = round(sub_end + max(48, (BOTTOM - sub_end - block_h) / 2))
    conns = []
    for i, (num, name, body, deliv) in enumerate(steps):
        x = M + i * (colw + gap)
        cx, cy = x + 24, y0 + 24
        kids = [C("Node", cx, cy, 24, P["teal"]),
                T("Node-Number", cx - 24, cy - 11, 48, num, 16, 600, P["lime"], lh=22, align="center"),
                T("Step-Title", x, y0 + 72, colw, name, 28, 600, P["teal"], lh=36),
                T("Step-Body", x, y0 + 72 + th + 10, colw, body, 20, 400, P["teal"], lh=30, opacity=0.85)]
        by = y0 + 72 + th + 10 + bh + 16
        kids.append(R("Deliverable-Box", x, by, colw, box_h, P["cream"], rx=16))
        kids.append(T("Deliverable-Label", x + 24, by + 16, 300, "Deliverable", 12, 500, P["orange_deep"], lh=16, ls=0.16, case="upper"))
        kids.append(T("Deliverable-Text", x + 24, by + 40, colw - 48, deliv, 18, 400, P["teal"], lh=26))
        els.append(G(f"Step-{num}", kids))
        if i < 3:
            conns.append(LINE(f"Connector-{i + 1}", cx + 32, cy, x + colw + gap + 24 - 32, cy, P["teal"], 2, opacity=0.35))
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
    y = 190 + t["h"] + 60
    gap = 32
    cw = (CW - gap) / 2
    ch, tab_w, tab_h = 400, 150, 44
    for i, (num, name, body, ic) in enumerate(cards):
        x = M + i * (cw + gap)
        tab = PATH("Tab-Fill", rounded_polygon(
            [(x, y), (x + tab_w, y), (x + tab_w, y + tab_h), (x + tab_w + 20, y + tab_h), (x + tab_w + 20, y + tab_h + 2), (x, y + tab_h + 2)],
            [22, 22, 20, 0, 0, 0]), fill=P["lime"])
        body_shape = PATH("Card-Body", rounded_polygon([(x, y + tab_h), (x + cw, y + tab_h), (x + cw, y + ch), (x, y + ch)], [0, 28, 28, 28]), fill=P["teal_mid"])
        tt = T("Card-Title", x + 40, y + 100, cw - 200, name, 30, 600, P["cream"], lh=38)
        kids = [tab, body_shape,
                T("Number", x, y + 10, tab_w, num, 18, 600, P["teal"], lh=24, align="center"),
                tt,
                T("Card-Body-Text", x + 40, y + 100 + tt["h"] + 14, cw - 200, body, 22, 400, P["cream"], lh=34, opacity=0.85),
                icon("Icon", ic, x + cw - 40 - 64, y + 100, 64, P["lime"], sw=3.6)]
        els.append(G(f"Card-{num}", kids))
    pts = [(-60, 820), (300, 810), (560, 880), (900, 870), (1240, 860), (1500, 800), (1980, 830)]
    els.append(ribbon("Ribbon", pts, 66, teal_fill=dark_ribbon_fill(pts)))
    els.append(footer("Ways of working", 5, dark))
    return {"name": "05 Ways of working", "bg": P["teal"], "elements": els}

def slide_uses():
    dark = False
    els = [R("Background", 0, 0, W, H, P["cream"]), header(dark)]
    t = title("Where the systems are used", dark, w=1300)
    els.append(t)
    sub = subtitle("The pattern of consumption shapes the system more than the type of business does.", dark, 190 + t["h"] + 16)
    els.append(sub)
    blocks = [
        ("Sites that consume\nduring the day", "Offices, retail centres, hotels, factories, schools and residential compounds. Their heaviest load falls within sunlight hours.", "sun"),
        ("Sites with continuous loads", "Hospitals, cold stores, production lines and data centres. The system works alongside the backup already in place, cutting generator running hours and fuel use.", "continuous"),
        ("Sites away from the grid", "Farms, irrigation pumps, camps and work sites that run on diesel.", "off-grid"),
        ("Projects under construction", "Contractors and developers delivering the energy scope within a live project.", "construction"),
    ]
    y0 = 190 + t["h"] + 16 + sub["h"] + 44
    gap = 24
    cw = (CW - 3 * gap) / 4
    ch = 460
    titles = [T("m", 0, 0, cw - 64, n, 22, 600, "#000000", lh=30) for n, _, _ in blocks]
    th = max(x["h"] for x in titles)
    for i, (name, body, ic) in enumerate(blocks):
        x = M + i * (cw + gap)
        kids = [R("Card-Shape", x, y0, cw, ch, P["white"], rx=24),
                C("Icon-Disc", x + 32 + 36, y0 + 32 + 36, 36, P["lime"]),
                icon("Icon", ic, x + 32 + 36 - 20, y0 + 32 + 36 - 20, 40, P["teal"]),
                T("Card-Title", x + 32, y0 + 124, cw - 64, name, 22, 600, P["teal"], lh=30),
                T("Card-Body", x + 32, y0 + 124 + th + 12, cw - 64, body, 17, 400, P["muted"], lh=26)]
        els.append(G(f"Card-{i + 1}", kids))
    pts = [(-60, 880), (300, 870), (560, 915), (900, 905), (1240, 900), (1500, 865), (1980, 885)]
    els.append(ribbon("Ribbon", pts, 50))
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
    y = 190 + t["h"] + 44
    colw = 980
    for i, (name, body, ic) in enumerate(items):
        kids = [T("Number", M, y + 5, 50, f"{i + 1:02d}", 17, 600, P["lime"], lh=22),
                icon("Icon", ic, M + colw - 36, y, 36, P["lime"], sw=2.2)]
        tt = T("Item-Title", M + 64, y, colw - 64 - 56, name, 26, 600, P["cream"], lh=32)
        kids.append(tt)
        b = T("Item-Body", M + 64, y + tt["h"] + 6, colw - 64 - 56, body, 18, 400, P["cream"], lh=27, opacity=0.8)
        kids.append(b)
        ly = y + tt["h"] + 6 + b["h"] + 16
        if i < len(items) - 1:
            kids.append(LINE("Divider", M, ly, M + colw, ly, P["cream"], 1, opacity=0.15))
        els.append(G(f"Item-{i + 1:02d}", kids))
        y = ly + 17
    px = M + colw + 96
    els.append(photo_slot("Photo-Strip", px, 190 + t["h"] + 44, W - M - px, BOTTOM - (190 + t["h"] + 44), 28, dark=True, art="grid"))
    els.append(footer("What AFAQ brings", 7, dark))
    return {"name": "07 What AFAQ brings", "bg": P["teal"], "elements": els}

def slide_contact():
    dark = True
    els = [R("Background", 0, 0, W, H, P["teal"]), header(dark)]
    slog = T("Slogan", M, 190, 900, "Innovating today,\nsustaining tomorrow", 64, 300, P["lime"], lh=72, ls=-0.02)
    els.append(slog)
    y = 190 + slog["h"] + 40
    els.append(T("Contact-Title", M, y, 600, "Contact", 22, 500, P["cream"], lh=30, opacity=0.7))
    y += 30 + 28
    rows = [("Phone", "+968 9190 7789", "phone"), ("Email", "afaq@gmail.com", "mail"), ("Address", "Al Khuwair, behind Zakher Mall, Muscat", "pin")]
    for lab, val, ic in rows:
        kids = [C("Icon-Disc", M + 28, y + 28, 28, P["lime"]),
                icon("Icon", ic, M + 28 - 14, y + 28 - 14, 28, P["teal"], sw=2),
                T("Label", M + 80, y, 500, lab, 13, 500, P["cream"], lh=18, ls=0.16, case="upper", opacity=0.6),
                T("Value", M + 80, y + 22, 760, val, 26, 500, P["cream"], lh=34)]
        els.append(G(f"Contact-{lab}", kids))
        y += 56 + 36
    lock, _ = lockup(1200, 300, 120, P["cream"], P["lime"])
    els.append(lock)
    pts = [(-60, 760), (300, 790), (560, 700), (900, 720), (1240, 740), (1500, 860), (1980, 800)]
    els.append(ribbon("Ribbon", pts, 84, teal_fill=dark_ribbon_fill(pts)))
    els.append(footer("AFAQ for Energy & Integrated Business", 8, dark))
    return {"name": "08 Contact", "bg": P["teal"], "elements": els}

SLIDES = [slide_cover, slide_about, slide_components, slide_scope, slide_ways, slide_uses, slide_brings, slide_contact]

def write_figma_scripts(spec, out):
    builder_path = os.path.join(ROOT, "figma", "figma-build.js")
    body = open(builder_path, encoding="utf-8").read().split("// eslint-disable-next-line")[0]
    slides = [{"name": s["name"], "bg": s["bg"], "elements": [slim(e) for e in s["elements"]]} for s in spec["slides"]]
    for i, s in enumerate(slides):
        one = {"canvas": spec["canvas"], "slides": [s]}
        write(os.path.join(out, "figma", "slides", f"slide-{i + 1:02d}.js"),
              f"// use_figma script — builds slide {s['name']} as a native 1920x1080 frame on the current page.\n"
              f"// Generated by tools/deck_landscape.py from the same spec as landscape/pages/*.svg\n"
              f"const SPEC = {json.dumps(one, separators=(',', ':'))};\n{body}\nreturn await buildDeck(SPEC);\n")
    write(os.path.join(out, "figma", "scripter-build-all.js"),
          f"// Scripter plugin: paste everything and run. Builds all 8 landscape slides to the right of existing content.\n"
          f"const SPEC = {json.dumps({'canvas': spec['canvas'], 'slides': slides}, separators=(',', ':'))};\n{body}\nconst result = await buildDeck(SPEC);\nconsole.log(result);\n")

def main():
    spec = {"canvas": {"width": W, "height": H}, "font": {"family": "Inter", "styles": STYLE_NAMES, "metrics": {"ascent": ASC, "descent": DESC}},
            "palette": P, "slides": []}
    for i, fn in enumerate(SLIDES):
        s = fn()
        spec["slides"].append(s)
        fname = f"{i + 1:02d}-{s['name'][3:].lower().replace(' ', '-')}.svg"
        write(os.path.join(OUT, "pages", fname), svg_of(s["elements"], W, H, s["name"]))
        write(os.path.join(OUT, "pages-illustrator", fname), svg_of(s["elements"], W, H, s["name"], ps_names=True))
        print("wrote landscape/pages/" + fname)
    write(os.path.join(OUT, "spec", "deck-spec.json"), json.dumps(spec, indent=1))
    write_figma_scripts(spec, OUT)
    pdf, ai = write_pdf(spec["slides"], W, H, os.path.join(OUT, "AFAQ-Corporate-Profile-1920x1080.pdf"),
                        "AFAQ Corporate Profile (1920x1080)", D.FONT_DIR, baseline)
    print("wrote", os.path.relpath(pdf, ROOT), "and", os.path.relpath(ai, ROOT))
    # portrait edition as PDF/AI too, from deck.py's own slides
    pslides = [fn() for fn in D.SLIDES]
    pdf, ai = write_pdf(pslides, D.W, D.H, os.path.join(ROOT, "AFAQ-Corporate-Profile-1080x1920.pdf"),
                        "AFAQ Corporate Profile (1080x1920)", D.FONT_DIR, baseline)
    print("wrote", os.path.relpath(pdf, ROOT), "and", os.path.relpath(ai, ROOT))

if __name__ == "__main__":
    main()

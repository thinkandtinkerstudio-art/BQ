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

# ---------------------------------------------------------------- shared parts (landscape metrics, layout v2 = client's board)
from deck import (wordmark, services_list, lockup_with_services, orange_label, notch_outline, box_ribbon, rect_path, LIME_PALE_BG, CARD_GREY)
M = 80
CW = W - 2 * M          # 1760
FOOT_Y = 1000
BOTTOM = 960

def eyebrow(num, label, dark=False, on_lime=False, x=M, y=72):
    pill_fill = P["teal"] if on_lime else P["lime"]
    num_col = P["lime"] if on_lime else P["teal"]
    lab_col = P["cream"] if dark else (P["teal"] if on_lime else P["muted"])
    return G("Eyebrow", [R("Eyebrow-Pill", x, y, 46, 24, pill_fill, rx=12),
                         T("Eyebrow-Number", x, y + 2, 46, num, 11, 600, num_col, lh=20, align="center"),
                         T("Eyebrow-Label", x + 60, y + 3, 700, label, 11, 500, lab_col, lh=18, ls=0.22, case="upper", opacity=0.75 if dark else 1.0)])

def footer(section, n, dark, on_lime=False):
    col = P["cream"] if dark else P["teal"]
    op = 0.7 if dark else 0.8
    rule_col = P["cream"] if dark else (P["teal"] if on_lime else P["line"])
    return G("Footer", [LINE("Footer-Rule", M, FOOT_Y, W - M, FOOT_Y, rule_col, 1, opacity=0.2 if (dark or on_lime) else 1.0),
                        wordmark(M, 1022, 16, col, name="Footer-Wordmark"),
                        LINE("Footer-Divider", M + 100, 1020, M + 100, 1040, col, 1, opacity=0.35),
                        T("Footer-Profile", M + 116, 1022, 400, "Corporate Profile 2026", 10, 500, col, lh=16, ls=0.22, case="upper", opacity=op),
                        T("Footer-Section", W - M - 520, 1022, 480, f"{section}   |   {n:02d}", 10, 500, col, lh=16, ls=0.22, case="upper", align="right", opacity=op)])

def title(text, dark, y=112, size=84, color=None, w=820):
    return T("Title", M, y, w, text, size, 300, color or (P["cream"] if dark else P["teal"]), lh=round(size * 1.02), ls=-0.03)

# ---------------------------------------------------------------- slides
def slide_cover():
    els = [R("Background", 0, 0, W, H, P["teal"])]
    lock, _ = lockup(M, 80, 56, P["cream"])
    els.append(lock)
    head = T("Headline", M, 250, 820, "AFAQ for Energy\n& Integrated\nBusiness.", 88, 300, P["cream"], lh=92, ls=-0.03)
    els.append(head)
    y = 250 + head["h"] + 30
    slog = T("Slogan", M, y, 820, "Innovating today, sustaining tomorrow", 36, 300, P["lime"], lh=44)
    els.append(slog)
    els.append(T("Scope", M, y + slog["h"] + 18, 760, "Solar power and energy storage in the Sultanate of Oman", 19, 400, P["cream"], lh=28, opacity=0.7))
    els.append(photo_slot("Photo-Hero", 960, 80, 880, 900, 36, {"corner": "tr", "w": 200, "h": 140, "r": 28}, dark=False))
    els.append(G("Profile-Tab", [R("Profile-Tab-Shape", W - M - 132, 80, 132, 100, P["orange"], rx=14),
                                 T("Profile-Tab-Text", W - M - 132 + 20, 80 + 24, 112, "CORPORATE\nPROFILE\n2026", 10, 500, P["cream"], lh=16, ls=0.16)]))
    pts = [(640, 1140), (820, 1040), (1040, 940), (1300, 880), (1560, 840), (1760, 780), (1980, 680)]
    els.append(ribbon("Ribbon", pts, 190))
    els.append(services_list(M, 880, P["cream"], size=12, lh=18))
    return {"name": "01 Cover", "bg": P["teal"], "elements": els}

def slide_about():
    els = [R("Background", 0, 0, W, H, P["cream"]), eyebrow("01", "About AFAQ")]
    t = title("About AFAQ.", False)
    els.append(t)
    y = 112 + t["h"] + 30
    p1 = T("Body-1", M, y, 780, "AFAQ for Energy & Integrated Business is an Omani company based in Muscat. It works in solar power, energy storage and the electrical systems that go with them.", 25, 400, P["teal"], lh=37)
    els.append(p1)
    y += p1["h"] + 30
    cw = 370
    p2 = T("Body-2", M, y, cw, "The company designs photovoltaic systems, supplies their components, installs them and brings them into operation, at sizes ranging from building systems to project plants.", 16, 400, P["muted"], lh=25)
    p3 = T("Body-3", M + cw + 40, y, cw, "AFAQ works directly with facility owners, and with contractors and developers inside their own projects.", 16, 400, P["muted"], lh=25)
    els += [p2, p3]
    px, py, pw, ph = 960, 80, 880, 880
    els.append(photo_slot("Photo-Array", px, py, pw, ph, 36, dark=False, art="solar", sun="right"))
    panel_w, panel_h = 440, 340
    els.append(G("Statement-Panel", [R("Statement-Shape", px, py, panel_w, panel_h, P["lime"], rx=36),
                                     T("Statement-Text", px + 40, py + 36, panel_w - 70, "Energy.\nEngineered.", 60, 300, P["teal"], lh=64, ls=-0.03),
                                     lockup_with_services(px + 40, py + 36 + 128 + 48, 38, P["teal"])]))
    els.append(orange_label(px + pw - 32 - 124, py + 32, w=124, h=96))
    els.append(box_ribbon("Ribbon", px, px + pw, py + ph, 90))
    els.append(footer("About AFAQ", 2, False))
    return {"name": "02 About AFAQ", "bg": P["cream"], "elements": els}

def slide_components():
    els = [R("Background", 0, 0, W, H, P["cream"]), eyebrow("02", "System components")]
    t = title("System components.", False, size=72, w=820)
    els.append(t)
    sub = T("Subtitle", M, 112 + t["h"] + 26, 540, "A photovoltaic system is built from four components. AFAQ holds a direct supply agreement with a main supplier for each.", 20, 400, P["teal"], lh=30, opacity=0.85)
    els.append(sub)
    py = 112 + t["h"] + 26 + sub["h"] + 36
    els.append(photo_slot("Photo-Plant", M, py, 820, BOTTOM - py, 32, dark=False, art="grid"))
    els.append(box_ribbon("Ribbon", M, M + 820, BOTTOM, 70, rel=(0.3, -0.5, 0.4, 0.1, -0.4, -0.9, -0.7)))
    comps = [
        ("01", "PV modules", "Selected according to the mounting area available and the conditions on site.", "Main suppliers", "AACE · Ronma", "pv-module"),
        ("02", "Battery energy storage", "Sized on the loads to be covered and the autonomy required.", "Main supplier", "Goshin", "battery"),
        ("03", "Inverters and power conversion", "Selected according to the array configuration and the connection requirements of the grid operator.", "Main supplier", "Star Charge", "inverter"),
        ("04", "Plant infrastructure", "Mounting structures, foundations, DC and AC cabling, and connection and protection panels, specified to suit the site.", None, None, "infrastructure"),
    ]
    gx, gy, gap = 960, 80, 24
    cw = (W - M - gx - gap) / 2
    ch = (BOTTOM - gy - gap) / 2
    for i, (num, name, note, lab, sup, ic) in enumerate(comps):
        x = gx + (i % 2) * (cw + gap)
        y = gy + (i // 2) * (ch + gap)
        dark_card = (i == 3)
        fill = P["teal"] if dark_card else CARD_GREY
        shape = (PATH("Card-Shape", rect_path(x, y, cw, ch, 26, {"corner": "br", "w": 140, "h": 76, "r": 20}), fill=fill) if dark_card
                 else R("Card-Shape", x, y, cw, ch, fill, rx=26))
        tcol = P["cream"] if dark_card else P["teal"]
        bcol = P["cream"] if dark_card else P["muted"]
        kids = [shape, T("Number", x + 30, y + 30, 200, num, 52, 300, tcol, lh=56, ls=-0.02),
                C("Icon-Disc", x + cw - 30 - 26, y + 30 + 26, 26, P["lime"]),
                icon("Icon", ic, x + cw - 30 - 26 - 13, y + 30 + 26 - 13, 26, P["teal"], sw=2.1)]
        tt = T("Card-Title", x + 30, y + 104, cw - 60, name, 22, 400, tcol, lh=28)
        kids.append(tt)
        kids.append(T("Card-Note", x + 30, y + 104 + tt["h"] + 8, cw - 60, note, 14, 400, bcol, lh=21, opacity=0.8 if dark_card else 1.0))
        if lab:
            ly = y + ch - 30 - 20 - 18 - 16
            kids.append(LINE("Card-Divider", x + 30, ly - 16, x + cw - 30, ly - 16, P["teal"], 1, opacity=0.15))
            kids.append(T("Supplier-Label", x + 30, ly, 300, lab, 10, 500, bcol, lh=15, ls=0.18, case="upper"))
            kids.append(T("Supplier", x + 30, ly + 18, cw - 60, sup, 16, 500, tcol, lh=22))
        els.append(G(f"Card-{num}", kids))
    els.append(footer("System components", 3, False))
    return {"name": "03 System components", "bg": P["cream"], "elements": els}

def slide_scope():
    els = [R("Background", 0, 0, W, H, P["cream"]), eyebrow("03", "Scope of work")]
    t = title("Scope of work.", False)
    els.append(t)
    sub = T("Subtitle", M, 112 + t["h"] + 26, 620, "The project sets the scope, from supply alone to full operation.", 20, 400, P["teal"], lh=30, opacity=0.85)
    els.append(sub)
    rpts = [(1380, -60), (1560, 40), (1700, 180), (1800, 300), (1880, 380), (1940, 430), (1990, 470)]
    els.insert(1, ribbon("Ribbon", rpts, 100))
    steps = [
        ("01", "Study and design", "Load analysis and consumption data, a site survey, system sizing and placement, and the expected annual yield.", "a report covering system capacity, expected annual yield and estimated cost.", "clipboard"),
        ("02", "Supply", "PV modules, batteries, inverters and electrical equipment, with manufacturer warranties.", "a component list with specifications, source and warranty terms.", "boxes"),
        ("03", "Installation and connection", "Installation, electrical works, and grid-tied, off-grid or hybrid connection.", "a working system and a testing and commissioning record.", "infrastructure"),
        ("04", "Operation and monitoring", "Performance monitoring and maintenance under an operation and maintenance contract.", "a performance report comparing actual output against the design figure.", "inverter"),
    ]
    gap = 32
    colw = (CW - 3 * gap) / 4
    titles = [T("m", 0, 0, colw - 40, s[1], 24, 400, "#000000", lh=30) for s in steps]
    bodies = [T("m", 0, 0, colw, s[2], 15, 400, "#000000", lh=23) for s in steps]
    delivs = [T("m", 0, 0, colw - 40, s[3], 14, 400, "#000000", lh=21) for s in steps]
    th, bh, dh = max(x["h"] for x in titles), max(x["h"] for x in bodies), max(x["h"] for x in delivs)
    box_h = 16 + 21 + 6 + dh + 16
    sub_end = 112 + t["h"] + 26 + sub["h"]
    block_h = 84 + th + 10 + bh + 18 + box_h
    y0 = round(sub_end + max(70, (BOTTOM - sub_end - block_h) / 2))
    for i, (num, name, body, deliv, ic) in enumerate(steps):
        x = M + i * (colw + gap)
        cx, cy = x + 30, y0 + 30
        kids = [C("Node", cx, cy, 30, P["lime"]),
                T("Node-Number", cx - 30, cy - 12, 60, num, 15, 600, P["teal"], lh=24, align="center"),
                icon("Icon", ic, x, y0 + 84, 26, P["teal"], sw=2),
                T("Step-Title", x + 38, y0 + 82, colw - 40, name, 24, 400, P["teal"], lh=30),
                T("Step-Body", x, y0 + 84 + th + 10, colw, body, 15, 400, P["muted"], lh=23)]
        by = y0 + 84 + th + 10 + bh + 18
        kids.append(R("Deliverable-Box", x, by, colw, box_h, LIME_PALE_BG, rx=16))
        kids.append(PATH("Deliverable-Check", f"M {x + 22} {by + 27} L {x + 28} {by + 33} L {x + 40} {by + 21}", stroke=P["lime_deep"], sw=2.2))
        kids.append(T("Deliverable-Label", x + 52, by + 16, 200, "Deliverable:", 14, 600, P["teal"], lh=21))
        kids.append(T("Deliverable-Text", x + 20, by + 16 + 21 + 6, colw - 40, deliv, 14, 400, P["teal"], lh=21))
        els.append(G(f"Step-{num}", kids))
        if i < 3:
            els.append(LINE(f"Connector-{i + 1}", cx + 36, cy, x + colw + gap + 30 - 36, cy, P["lime_deep"], 2, opacity=0.5))
    els.append(footer("Scope of work", 4, False))
    return {"name": "04 Scope of work", "bg": P["cream"], "elements": els}

def slide_ways():
    els = [R("Background", 0, 0, W, H, P["lime"]), eyebrow("04", "Ways of working", on_lime=True)]
    t = title("Ways of\nworking.", False)
    els.append(t)
    cards = [("01", "Supply and installation for projects", "One party responsible for design, supply, installation and commissioning.", "clipboard", True),
             ("02", "Component supply", "Supply to the specification and quantities of the project, for contractors and installation companies.", "boxes", False)]
    gap = 32
    cw = (CW - gap) / 2
    y, ch = 420, 330
    for i, (num, name, body, ic, notched) in enumerate(cards):
        x = M + i * (cw + gap)
        shape = (PATH("Card-Shape", rect_path(x, y, cw, ch, 32, {"corner": "tl", "w": 200, "h": 150, "r": 28}), fill=P["teal"]) if notched
                 else R("Card-Shape", x, y, cw, ch, P["teal"], rx=32))
        tt = T("Card-Title", x + 236, y + 40, cw - 236 - 110, name, 32, 300, P["cream"], lh=38)
        kids = [shape, T("Number", x + 36, y + 32, 160, num, 56, 300, P["teal"] if notched else P["lime"], lh=62, ls=-0.02), tt,
                T("Card-Body-Text", x + 236, y + 40 + tt["h"] + 16, cw - 236 - 110, body, 18, 400, P["cream"], lh=27, opacity=0.8),
                C("Icon-Disc", x + cw - 36 - 28, y + 40 + 28, 28, P["lime"]),
                icon("Icon", ic, x + cw - 36 - 28 - 13, y + 40 + 28 - 13, 26, P["teal"], sw=2.1)]
        els.append(G(f"Card-{num}", kids))
    els.append(notch_outline(1480, 790, 480, 400, P["teal"], sw=52))
    els.append(lockup_with_services(M, 860, 52, P["teal"]))
    els.append(footer("Ways of working", 5, False, on_lime=True))
    return {"name": "05 Ways of working", "bg": P["lime"], "elements": els}

def slide_uses():
    els = [R("Background", 0, 0, W, H, P["cream"]), eyebrow("05", "Where the systems are used")]
    t = title("Where the\nsystems are used.", False, size=78)
    els.append(t)
    px, py, pw = M, 112 + t["h"] + 36, 860
    ph = BOTTOM - py
    sub = T("Statement", px + 36, py + 34, pw - 72, "The pattern of consumption shapes the system more than the type of business does.", 28, 300, P["teal"], lh=36, ls=-0.02)
    els.append(G("Statement-Panel", [R("Statement-Shape", px, py, pw, ph, P["lime"], rx=32), sub]))
    img_y = py + 34 + sub["h"] + 26
    els.append(photo_slot("Photo-Site", px + 18, img_y, pw - 36, py + ph - 18 - img_y, 24, dark=False, art="solar"))
    els.append(orange_label(px + pw - 18 - 20 - 110, img_y + 20, w=110, h=86, size=9))
    blocks = [
        ("Sites that consume during the day", "Offices, retail centres, hotels, factories, schools and residential compounds. Their heaviest load falls within sunlight hours.", "sun"),
        ("Sites with continuous loads", "Hospitals, cold stores, production lines and data centres. The system works alongside the backup already in place, cutting generator running hours and fuel use.", "continuous"),
        ("Sites away from the grid", "Farms, irrigation pumps, camps and work sites that run on diesel.", "off-grid"),
        ("Projects under construction", "Contractors and developers delivering the energy scope within a live project.", "construction"),
    ]
    gx, gy, gap = 1000, 80, 24
    cw = (W - M - gx - gap) / 2
    ch = (BOTTOM - gy - gap) / 2
    titles = [T("m", 0, 0, cw - 60, n, 21, 400, "#000000", lh=27) for n, _, _ in blocks]
    th = max(x["h"] for x in titles)
    for i, (name, body, ic) in enumerate(blocks):
        x = gx + (i % 2) * (cw + gap)
        y = gy + (i // 2) * (ch + gap)
        kids = [R("Card-Shape", x, y, cw, ch, CARD_GREY, rx=26),
                C("Icon-Disc", x + 30 + 24, y + 30 + 24, 24, P["lime"]),
                icon("Icon", ic, x + 30 + 24 - 12, y + 30 + 24 - 12, 24, P["teal"], sw=2),
                T("Card-Title", x + 30, y + 108, cw - 60, name, 21, 400, P["teal"], lh=27),
                T("Card-Body", x + 30, y + 108 + th + 10, cw - 60, body, 14, 400, P["muted"], lh=21)]
        els.append(G(f"Card-{i + 1}", kids))
    els.append(footer("Where the systems are used", 6, False))
    return {"name": "06 Where the systems are used", "bg": P["cream"], "elements": els}

def slide_brings():
    els = [R("Background", 0, 0, W, H, P["teal"]), eyebrow("06", "What AFAQ brings", dark=True)]
    t = title("What AFAQ\nbrings.", True)
    els.append(t)
    px, py, pw = M, 112 + t["h"] + 36, 900
    ph = BOTTOM - py
    els.append(photo_slot("Photo-Storage", px, py, pw, ph, 32, {"corner": "tl", "w": 170, "h": 120, "r": 26}, dark=True, art="storage"))
    els.append(orange_label(px, py, w=144, h=96, size=9))
    els.append(box_ribbon("Ribbon", px, px + pw, py + ph, 90, teal_fill=dark_ribbon_fill([(px, 0), (px + pw, 0)])))
    items = [
        ("Supply from a factory in Oman", "AACE modules are manufactured in Oman, which shortens supply time compared with importing.", "factory"),
        ("Warranty handled inside Oman", "AFAQ processes module warranty claims locally, without sending them to a manufacturer abroad.", "shield"),
        ("In-country value", "Modules made in Oman support local content requirements in tenders and government projects.", "badge"),
        ("Direct supply agreements", "Written agreements with module, battery and inverter suppliers, covering availability and manufacturer warranties.", "document"),
        ("Delivery team", "An engineering team for design and supervision, and a field crew for installation and commissioning.", "team"),
    ]
    lx, ly0 = 1040, 110
    lw = W - M - lx
    row_h = (BOTTOM - ly0) / len(items)
    for i, (name, body, ic) in enumerate(items):
        ry = round(ly0 + i * row_h)
        kids = [icon("Icon", ic, lx, ry + 4, 22, P["lime"], sw=1.9),
                T("Item-Title", lx + 40, ry, 290, name, 21, 400, P["cream"], lh=27),
                T("Item-Body", lx + 360, ry + 3, lw - 360, body, 13, 400, P["cream"], lh=20, opacity=0.7)]
        if i < len(items) - 1:
            kids.append(LINE("Divider", lx, round(ry + row_h - 14), W - M, round(ry + row_h - 14), P["cream"], 1, opacity=0.12))
        els.append(G(f"Item-{i + 1:02d}", kids))
    els.append(footer("What AFAQ brings", 7, True))
    return {"name": "07 What AFAQ brings", "bg": P["teal"], "elements": els}

def slide_contact():
    els = [R("Background", 0, 0, W, H, P["cream"]), eyebrow("07", "Contact")]
    t = title("Contact.", False)
    els.append(t)
    rows = [("Phone", "+968 9190 7789", "phone"), ("Email", "afaq@gmail.com", "mail"), ("Address", "Al Khuwair, behind Zakher Mall, Muscat", "pin")]
    y = 112 + t["h"] + 60
    for i, (lab, val, ic) in enumerate(rows):
        kids = [C("Icon-Disc", M + 28, y + 34, 28, P["lime"]),
                icon("Icon", ic, M + 28 - 12, y + 34 - 12, 24, P["teal"], sw=2),
                T("Label", M + 84, y + 6, 400, lab, 11, 500, P["muted"], lh=16, ls=0.2, case="upper"),
                T("Value", M + 84, y + 26, 760, val, 32, 400, P["teal"], lh=40)]
        if i < len(rows) - 1:
            kids.append(LINE("Divider", M, y + 98, M + 800, y + 98, P["line"], 1))
        els.append(G(f"Contact-{lab}", kids))
        y += 126
    els.append(lockup_with_services(M, 850, 52, P["teal"]))
    px, py, pw, ph = 960, 80, 880, 880
    els.append(photo_slot("Photo-Farm", px, py, pw, ph, 36, dark=False, art="solar"))
    els.append(box_ribbon("Ribbon", px, px + pw, py + ph, 100))
    els.append(footer("Contact", 8, False))
    return {"name": "08 Contact", "bg": P["cream"], "elements": els}

def slide_back():
    els = [R("Background", 0, 0, W, H, P["teal"])]
    lock, _ = lockup(M, 80, 64, P["cream"])
    els.append(lock)
    a = [(820, -60), (960, 120), (1120, 380), (1300, 520), (1500, 560), (1700, 480), (1980, 300)]
    b = [(760, 1140), (900, 980), (1080, 760), (1300, 600), (1520, 560), (1740, 640), (1980, 820)]
    c = [(1000, -60), (1080, 160), (1200, 420), (1360, 700), (1540, 900), (1760, 1000), (1980, 1140)]
    els.append(ribbon("Ribbon-A", a, 130, teal_fill=dark_ribbon_fill(a)))
    els.append(ribbon("Ribbon-B", b, 120, teal_fill=dark_ribbon_fill(b)))
    els.append(ribbon("Ribbon-C", c, 110, teal_fill=dark_ribbon_fill(c)))
    slog = T("Slogan", M, 520, 760, "Innovating today,\nsustaining tomorrow.", 76, 300, P["cream"], lh=80, ls=-0.03)
    els.append(slog)
    els.append(T("Company", M, 520 + slog["h"] + 20, 700, "AFAQ for Energy & Integrated Business", 22, 400, P["cream"], lh=30, opacity=0.8))
    els.append(services_list(M, 900, P["cream"], size=12, lh=18))
    return {"name": "09 Back cover", "bg": P["teal"], "elements": els}

SLIDES = [slide_cover, slide_about, slide_components, slide_scope, slide_ways, slide_uses, slide_brings, slide_contact, slide_back]

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
          f"// Scripter plugin: paste everything and run. Builds all landscape slides to the right of existing content.\n"
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

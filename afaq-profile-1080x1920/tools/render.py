#!/usr/bin/env python3
"""Render every SVG in the given pages folder to PNG (size read from the SVG), plus a contact sheet."""
import glob, os, re, subprocess, sys
from PIL import Image

def chrome():
    env = os.environ.get("CHROME")
    if env: return env
    c = sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
    return c[-1] if c else "chromium"

def render(pages_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    files = sorted(glob.glob(os.path.join(pages_dir, "*.svg")))
    procs, sizes = [], {}
    for f in files:
        head = open(f, encoding="utf-8").read(600)
        w = int(re.search(r'<svg[^>]*\swidth="(\d+)"', head).group(1)); h = int(re.search(r'<svg[^>]*\sheight="(\d+)"', head).group(1))
        out = os.path.join(out_dir, os.path.basename(f)[:-4] + ".png")
        sizes[out] = (w, h)
        procs.append(subprocess.Popen([chrome(), "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                                       "--force-device-scale-factor=1", f"--window-size={w},{h + 180}", f"--screenshot={out}", "file://" + os.path.abspath(f)],
                                      stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
    for p in procs: p.wait(timeout=120)
    thumbs = []
    for out, (w, h) in sizes.items():
        im = Image.open(out).convert("RGB")
        if im.size != (w, h): im = im.crop((0, 0, w, h)); im.save(out)
        thumbs.append(im)
    if thumbs:
        w, h = thumbs[0].size
        tw = 360 if w < h else 480
        th = round(h * tw / w)
        cols = 4
        rows = (len(thumbs) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * tw + (cols + 1) * 24, rows * th + (rows + 1) * 24), (232, 232, 220))
        for i, t in enumerate(thumbs):
            sheet.paste(t.resize((tw, th), Image.LANCZOS), (24 + (i % cols) * (tw + 24), 24 + (i // cols) * (th + 24)))
        sheet.save(os.path.join(out_dir, "contact-sheet.png"))
    print(f"rendered {len(files)} pages → {out_dir}")

if __name__ == "__main__":
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pages = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, "pages")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(pages), "previews")
    render(pages, out)

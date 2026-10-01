#!/bin/bash
# Render page SVGs to 1080x1920 PNG previews with headless Chromium (Inter must be installed, see fonts/).
CH=$(ls -d /opt/pw-browsers/chromium-*/chrome-linux/chrome 2>/dev/null | head -1)
CH=${CHROME:-$CH}
OUT=${DECK_OUT:-/home/user/BQ/afaq-profile-1080x1920}
mkdir -p "$OUT/previews"
for f in "$OUT"/pages/*.svg; do
  b=$(basename "$f" .svg)
  # headless viewport loses ~85px to window chrome, so render taller and crop to 1920 afterwards
  timeout 90 "$CH" --headless=new --no-sandbox --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
    --window-size=1080,2100 --screenshot="$OUT/previews/$b.png" "file://$f" >/dev/null 2>&1 &
done
wait
python3 - "$OUT/previews" <<'PY'
import sys, glob, os
from PIL import Image
d = sys.argv[1]
files = sorted(glob.glob(os.path.join(d, "0*.png")))
for f in files:
    im = Image.open(f).convert("RGB")
    if im.size[1] != 1920:
        im = im.crop((0, 0, 1080, 1920))
        im.save(f)
thumbs = [Image.open(f).convert("RGB").resize((360, 640), Image.LANCZOS) for f in files]
sheet = Image.new("RGB", (4 * 360 + 5 * 24, 2 * 640 + 3 * 24), (232, 232, 220))
for i, t in enumerate(thumbs):
    sheet.paste(t, (24 + (i % 4) * 384, 24 + (i // 4) * 664))
sheet.save(os.path.join(d, "contact-sheet.png"))
print("rendered", len(files), "pages +", "contact-sheet.png")
PY

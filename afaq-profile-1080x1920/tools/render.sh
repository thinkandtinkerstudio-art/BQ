#!/bin/bash
# Render page SVGs to PNG previews with headless Chromium (Inter must be installed, see fonts/).
HERE=$(cd "$(dirname "$0")" && pwd)
python3 "$HERE/render.py" "$HERE/../pages" "$HERE/../previews"
[ -d "$HERE/../landscape/pages" ] && python3 "$HERE/render.py" "$HERE/../landscape/pages" "$HERE/../landscape/previews"

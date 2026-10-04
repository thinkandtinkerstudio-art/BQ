# Rova Skin · Product Stickers (Illustrator)

ستة منتجات × اتجاهين = ١٢ استيكر، كلها فيكتور ونصوص حيّة قابلة للتعديل في Illustrator.

| # | Step | Product | Field colour | Size |
|---|------|---------|--------------|------|
| 01 | RENEW | The Renewal · Overnight Peel | Deep burgundy | 10 g |
| 02 | REPAIR | Cica Recovery Cream | Rose tint | 50 ml |
| 03 | CORRECT | The Corrector · Brightening Cream | Ivory | 50 ml |
| 04 | HYDRATE | The Hydrator · Barrier Moisturizer Cream | Deep burgundy | 50 ml |
| 05 | GLOW | The Glow · Radiance Serum | Rose tint | 30 ml |
| — | GIFT | Lip Gloss (ملمع شفاه) | Ivory | 5 ml |

Every product comes as **portrait 60 × 90 mm** and **landscape 90 × 60 mm**, 3 mm bleed, 5 mm safe area, 3 mm rounded corners.
Preview: `previews/contact-sheet.png`.

## ملخص بالعربي

- `Rova-Skin-Stickers.ai` — ملف واحد فيه ١٢ artboard (٦ بالطول + ٦ بالعرض). افتحه في Illustrator واختار **All pages** في نافذة الاستيراد. الألوان CMYK بقيم البراند، وخط القص موجود كـ spot colour اسمه `CutContour`.
- `stickers/portrait/` و `stickers/landscape/` — كل استيكر كملف SVG منفصل بنصوص حيّة (Georgia / Syne Bold / Amiri). افتحه مباشرة في Illustrator (File → Open) — الوحدة مليمتر والـ artboard بمقاس القص والبليد مرسوم خارجه.
- `fonts/` — ثبّت Syne-Bold و Amiri قبل ما تفتح الملفات. Georgia موجودة في ويندوز وماك.
- `spec/products.json` — نصوص المنتجات؛ عدّل وشغّل `python3 tools/build.py` يعيد توليد كل الملفات.
- الاسم العربي لكل منتج (نوع المنتج: المقشر، كريم السيكا، كريم التفتيح، المرطب، سيروم النضارة، ملمع شفاه) مكتوب بخط Amiri Bold مع كاشيدة (تطويل) عشان يبقى أعرض. النصوص في `spec/products.json` والكاشيدة حرف تطويل عادي (ـ) تقدر تزوده أو تقلله. الجروب اسمه `Arabic` لو عايز تشيله.

## Files

```
Rova-Skin-Stickers.ai / .pdf   12 artboards (pages 1–6 portrait, 7–12 landscape), CMYK, CutContour dieline
stickers/portrait/*.svg        6 × 60×90 mm, live text, 1 unit = 1 mm
stickers/landscape/*.svg       6 × 90×60 mm
assets/logo/                   Rova mark, ROVA wordmark, sparkle, "ROVA SKIN" stacked lockups (vector, from the brand PDF)
previews/                      300 dpi PNG of every sticker + contact sheet
fonts/                         Syne-Bold, Amiri-Bold (+ Regular), Gelasio (OFL) — Georgia is a system font and is not shipped
spec/products.json             the copy for the six products, field colour per product, sizes
tools/build.py                 generator (spec → SVG / PDF / AI / PNG);  tools/extract_logo.py pulled the logo vectors
```

## Opening in Illustrator

**SVG (recommended for editing).** File → Open any file in `stickers/`. Units are millimetres, the artboard is the trim size,
and the 3 mm bleed is drawn outside the artboard (set Document Setup → Bleed 3 mm to see it). Groups are named
`Background`, `Watermark`, `Logo`, `Rules`, `Text`, `Arabic`, `Dieline`. Text stays live in Georgia, Georgia Italic,
Syne Bold and Amiri Bold; install the fonts in `fonts/` first. The `Dieline` group holds the trim outline (`CutContour`, magenta)
and the dashed safe area (cyan) and is not meant to print: delete it or move it to a non-printing layer.

**AI / PDF (one file, 12 artboards).** `Rova-Skin-Stickers.ai` is a PDF-compatible file; Illustrator opens it directly.
In the Import dialog choose *All pages* so each sticker becomes an artboard. Each page carries a MediaBox of trim + 3 mm bleed
and a TrimBox of the trim size. Colours are CMYK with the brand values (deep burgundy 0/70/58/76, ivory 0/7/13/6,
rose tint 0/12/17/26). The dieline is a stroke in the spot colour `CutContour`, the convention most cutters and printers
use. Georgia text is embedded with metric-compatible stand-in glyphs (Gelasio) under the names *Georgia* and *Georgia Italic*,
so Illustrator switches to your installed Georgia on open with no reflow. Arabic in the PDF is stored as shaped glyphs
(fine for print and preview); to edit the Arabic text, use the SVG files, where it is a normal Arabic string.

## Design rules applied (from the Rova colour guide and brand presentation)

- Three colours only. Fields rotate deep burgundy → rose tint → ivory across the range (burgundy 01/04, rose 02/05, ivory 03/06),
  as the colour guide asks for stickers "in all three colours".
- Text is always a solid colour: ivory on deep burgundy, deep burgundy on ivory and on rose tint. Rose tint is used for lines only.
- The mark as a watermark bleeding off the bottom-right corner at 8–10 % (the "pattern and watermark tone").
- Georgia for the product name (caps, tracked) and the human lines (descriptor and benefits in italic); Syne Bold, letter-spaced
  and small, for labels and facts (step, actives, size). Middle dots `·` replace the bullets in the brief.
- `ROVA SKIN` lockup = the ROVA wordmark with SKIN set like the BEAUTY CLINIC descriptor; the mark sits above it, as in the vertical label version.
- Arabic product-type line in Amiri Bold with kashida (tatweel) stretches so the Naskh line reads as wide as the Latin name above it.
- Nothing but the watermark crosses the 5 mm safe area.

## Regenerate

```
pip install reportlab pymupdf cairosvg fonttools arabic-reshaper python-bidi Pillow
python3 tools/build.py
```

Sizes, bleed, safe area and corner radius are in `spec/products.json` → `sizes_mm`; change them and rebuild. To add a product,
add an entry (fields: `step`, `step_name`, `arabic`, `name`, `descriptor`, `actives`, `benefits`, `benefits_style` caps|italic,
`size`, `field` burgundy|rose|ivory).

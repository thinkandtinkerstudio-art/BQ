# Grano · Classic Natural Granola 250 g — carton artwork on the client dieline

> **ملخص بالعربي**
>
> - ده التصميم كله مبني **على ملف الداي كت بتاعك بالظبط** (`dieline/dieline-original.ai`، أرت بورد 500 × 350 مم، علبة 130 × 60 × 200 مم). كل بانل في مكانه على الداي كت: الغراء، الوش، الجنب الأزرق، الظهر، الجنب البرتقالي، غطاء التاك فوق، فلابات التراب، والفلابات اللي تحت بالكاروهات.
> - **ملف الإليستريتور:** `Grano-Granola-Box.ai` (ومعاه `.pdf` بنفس المحتوى بالظبط). افتحه من Illustrator → File → Open. كل حاجة فيكتور قابلة للتعديل: الأشكال Paths، النصوص **Live** (مش Outlines)، والداي كت على طبقات منفصلة بألوان Spot اسمها **Dieline-Cut** و **Dieline-Crease** مع Overprint.
> - **الطبقات (من فوق لتحت):** `DIELINE - Window cut (optional)` → `DIELINE - Cut` → `DIELINE - Crease` → `NOTES (delete before print)` → `TEXT` → `LOGO` → `ILLUSTRATIONS` → `PHOTO-PLACEHOLDER` → `GINGHAM` → `BACKGROUND`. (الطبقات محفوظة كـ PDF Layers؛ لو إليستريتور فتحها كجروبات بدل طبقات، كل جروب اسمه اسم الطبقة — Release to Layers وخلاص.)
> - **الخطوط:** ثبّت الخطوط اللي في فولدر `fonts/` قبل ما تفتح الملف (Fredoka Bold، Fraunces Black، Poppins Regular/Medium/SemiBold/Bold/ExtraBold — كلها رخصة OFL مجانية). اللوجو "Grano" مرسوم **Outlines** (مش محتاج خط)، وعليه الورقتين فوق الـ a والورقة جوه الـ o زي الرسمة.
> - **صورة الجرانولا:** الشباك اللي في السلة فيه رسمة فيكتور مؤقتة (طبقة `PHOTO-PLACEHOLDER`). حط صورة المنتج الحقيقية: File → Place الصورة → حطها تحت شكل `Window-Clip` → حدد الاتنين → Object → Clipping Mask → Make، وامسح الرسمة المؤقتة.
> - **الشباك في الداي كت:** التصميم فيه شباك شفاف في الوش (زي الرسمة)، فحطيت خط قص للشباك على طبقة منفصلة `DIELINE - Window cut (optional)`. لو مش عايز شباك فعلي في العلبة، امسح الطبقة دي بس.
> - **الباركود** EAN-13 مؤقت (الرقم `6 224001 234569` صحيح الـ checksum بس مش رقمك) — استبدله برقم GS1 بتاعك. **القيم الغذائية** منقولة من الرسمة المرجعية؛ راجعها مع التحليل المعملي قبل الطباعة.
> - **البليد** 3 مم موجود حوالين كل خطوط القص. `NOTES` طبقة إرشادية (أسماء البانلات والمقاسات) امسحها قبل الطباعة.
> - نسخة SVG (`Grano-Granola-Box.svg`) بنفس المحتوى وبجروبات بأسماء الطبقات، لو حابب تفتحها في Figma أو إليستريتور.
> - **كل الملفات في ملف واحد:** `Grano-Granola-Box-package.zip`.

---

## What's inside

| File / folder | Contents |
|---|---|
| `Grano-Granola-Box.ai` | The deliverable. A PDF-compatible Illustrator file: 1 artboard = the client's dieline page (1417.32 × 992.126 pt = 500 × 350 mm). Editable paths, live point text (fonts embedded as subsets), 10 named layers (PDF optional-content groups), spot-colour dieline with overprint, 3 mm bleed, ArtBox = dieline bounds. |
| `Grano-Granola-Box.pdf` | Byte-identical copy of the `.ai` for proofing / sending to the printer. |
| `Grano-Granola-Box.svg` | Same artwork as SVG: one `<g id="…">` per layer, PostScript font names (`Poppins-SemiBold`, `Fraunces-Black`…), clip paths for the gingham and the photo window. Opens in Illustrator and Figma. |
| `Grano-Granola-Box-swatches.ase` | Illustrator swatch library: the 20 brand/illustration colours + the two spot colours `Dieline-Cut` and `Dieline-Crease`. Window → Swatches → menu → Open Swatch Library → Other Library. |
| `Grano-Granola-Box-package.zip` | Everything below in one download. |
| `dieline/dieline-original.ai` | The client's dieline exactly as received (untouched). `reference-design.png` is the design brief. |
| `fonts/` | Fredoka Bold, Fraunces Black (static instances cut from the Google Fonts variable files), Poppins Regular / Medium / SemiBold / Bold / ExtraBold. All SIL Open Font License (`OFL-*.txt`). Install before opening the `.ai`. |
| `previews/` | `Grano-Granola-Box-preview.png` (110 dpi) and `Grano-Granola-Box-300dpi.png`. |
| `tools/build.py` | The generator (scene → PDF/AI via ReportLab + PyMuPDF, SVG, ASE, previews, zip). `tools/dieline_paths.json` is the cut/crease geometry extracted from the client's `.ai`. |

## Dieline map (from the client's file)

| Panel | Position on the artboard (pt, top-left origin) | Size |
|---|---|---|
| Glue flap | x 147.6 → 193.0, y 261 → 827 | 16 × 200 mm |
| Front (window + basket) | x 193.0 → 561.5, y 260 → 827 | 130 × 200 mm |
| Side A (blue, nine ingredients) | x 561.5 → 731.6 | 60 × 200 mm |
| Back (copy, nutrition, barcode) | x 731.6 → 1100.1 | 130 × 200 mm |
| Side B (orange, "Brighter days start here.") | x 1100.1 → 1268.7 | 60 × 200 mm |
| Tuck lid + tongue (over the front) | y 35.3 → 260, crease at y 92 | 130 × 79 mm |
| Dust flaps (top of both sides), bottom flaps (all panels) | as cut in the dieline | gingham on the bottom flaps |

Cut lines are the spot colour **Dieline-Cut** (CMYK 0/57/98/0, same orange as the client file), creases are **Dieline-Crease** (CMYK 0/100/100/0). Both strokes are 0.75 pt with overprint on, each on its own layer, so the printer can drop them or use them for the die. The photo window cut sits on `DIELINE - Window cut (optional)` — delete that layer if the carton has no window.

## Open in Adobe Illustrator

1. Install the fonts in `fonts/`.
2. File → Open → `Grano-Granola-Box.ai`. Illustrator reads it as PDF content: every shape is a path, gradients are not used (flat colours only), the logo is outlined, all other text is live. If the fonts are not installed Illustrator substitutes them but keeps the text editable.
3. Layers: the file carries PDF layers in this order — `DIELINE - Window cut (optional)`, `DIELINE - Cut`, `DIELINE - Crease`, `NOTES (delete before print)`, `TEXT`, `LOGO`, `ILLUSTRATIONS`, `PHOTO-PLACEHOLDER (replace with granola photo)`, `GINGHAM`, `BACKGROUND`. If your Illustrator version flattens PDF layers into one, open the `.svg` instead: the same groups come in named, then Layers panel menu → Release to Layers (Sequence).
4. Product photo: File → Place the photo, Object → Arrange → Send Backward until it sits under the `Window-Clip` shape (the 246 × 174 pt rounded rectangle at x 254, y 538), select both, Object → Clipping Mask → Make, then delete the vector granola placeholder.
5. Swatches: load `Grano-Granola-Box-swatches.ase`.
6. Before print: delete `NOTES (delete before print)`, replace the EAN-13 placeholder and the batch/date fields, confirm the nutrition table against the lab report, keep the two dieline layers as non-printing or as the die file, per the printer's instructions. Export with bleed 3 mm (the art already extends 3 mm beyond every cut).

## Design system

| Token | Hex | Use |
|---|---|---|
| Cream | `#FCEFD6` | Front and back panel background |
| Cream Deep | `#F6DFB9` | Basket body |
| Orange | `#F88E51` | Lid, glue flap, dust flaps, side B |
| Orange Deep | `#DF6A2E` | Back headline, column leaf marks |
| Orange Pale | `#FCD9BE` | Pale leaves on the orange panels |
| Blue | `#8AAEED` | Side A background |
| Blue Mid / Dark / Light | `#5283D4` / `#4D70B3` / `#B4C8EE` | Basket rim, handle, gingham |
| Navy | `#081D57` | Logo and all text |
| Gold / Gold Deep / Amber / Honey | `#F3C978` / `#D99E4B` / `#E9A161` / `#F2A93B` | Oat sprigs, almonds, honey |
| Green / Green Deep | `#7E9A4B` / `#5C7A3A` | Leaves, pumpkin seeds |
| Wood / Wood Dark / Brown | `#A15820` / `#5F290D` / `#8B4A1C` | Honey dipper, pecans, cinnamon |

Type: logo = Fredoka Bold outlined (leaf sprig on the *a*, leaf counter in the *o*); headlines = Fraunces Black (soft, opsz 144); eyebrows and labels = Poppins SemiBold / Bold with 8–14 % tracking; body = Poppins Regular 7.2–8.6 pt; nutrition table = Poppins 5.6 pt.

## Rebuild

```bash
pip install reportlab pymupdf fonttools shapely
python3 tools/build.py        # writes .ai/.pdf/.svg/.ase, previews/, and the package zip
```

Every element is defined in `tools/build.py` (`build_scene()`): panel copy, layout, illustrations and the dieline geometry, so text or colour changes can also be made there and regenerated.

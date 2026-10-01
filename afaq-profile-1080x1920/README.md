# AFAQ Corporate Profile — editable vector deck (1080 × 1920 and 1920 × 1080)

> **ملخص بالعربي**
>
> - ده إعادة بناء كاملة للبروفايل (8 صفحات) بمقاس **1080 × 1920** بنفس جرافيكس البراند (AFQ): اللايم، التيل الغامق، الكريمي، البرتقالي، الريبون بثلاث طبقات، التابات المدوّرة، اللوجو المرسوم فيكتور، والأيقونات.
> - **الخلفيات مش هتطلع سودة**: كل شكل ليه لون صريح (hex) جوه الـ SVG، مفيش CSS ولا `<style>` ولا متغيرات ولا transform.
> - **مفيش ماسكات خالص**: مكان الصورة شكل واحد اسمه `Photo-…__set-image-fill` — تختاره في فيجما وتعمله Fill → Image وتحذف جروب `Placeholder-Art`. دي أنظف طريقة من الماسك ومش بتضرب.
> - **النصوص كلها قابلة للتعديل** (`<text>`، خط Inter) والأشكال كلها فيكتور، مفيش حاجة Raster.
> - **فيجما**: اسحب الـ 8 ملفات من `pages/` جوه الملف ده: <https://www.figma.com/design/ccLJTZvL8LndrWwdwVXDsu> (ملف فاضي اتعمل لك). كل صفحة بتدخل كـ Frame 1080×1920 بطبقات أصلية (Rect / Vector / Text) بأسماء مرتبة.
> - الحساب خلّص **حد استخدام Figma MCP الشهري (Starter plan)** من أول أمر كتابة، فمقدرتش أرسم جواه مباشرة من هنا. بدل ما تستنى: الملف `figma/scripter-build-all.js` يبني الـ 8 صفحات **Native** جوه فيجما (Text حقيقي بـ paragraphs) عن طريق بلجن Scripter في أقل من دقيقة — الخطوات تحت.
> - **نسخة بالعرض 1920 × 1080** جاهزة في فولدر `landscape/` (نفس الـ 8 صفحات بتوزيع landscape للبريزينتيشن).
> - **ملف إليستريتور**: `landscape/AFAQ-Corporate-Profile-1920x1080.ai` (و `.pdf` بنفس المحتوى). افتحه من Illustrator → File → Open، وفي شاشة استيراد الـ PDF اختار **All** عشان الـ 8 صفحات تدخل كـ 8 Artboards. النصوص Live وقابلة للتعديل (ثبّت خط Inter من `fonts/` الأول)، والأشكال كلها Paths والتدرجات Native.
> - **إليستريتور (SVG)**: أو افتح ملفات `pages-illustrator/` (نفس الصفحات بس بأسماء الخطوط PostScript عشان الأوزان تتظبط)، وثبّت خط Inter من فولدر `fonts/` الأول.
> - ملاحظة: اللوجو في الـ boards بتاعتك مكتوب **AFQ** (ثلاث حروف) فمشيت عليه حرفيًا، والاسم الكامل "AFAQ for Energy & Integrated Business" موجود في النصوص. لو عايز اللوجو AFAQ قولّي.

---

## What's inside

| Folder | Contents |
|---|---|
| `pages/` | One SVG per page, `01-cover.svg` … `08-contact.svg`, each exactly **1080 × 1920**. Inline hex fills only, editable `<text>` (font-family `Inter`), absolute `M/L/C/Z` paths, no masks, no clipPath, no CSS, no transforms, no rasters. **Use these for Figma.** |
| `landscape/` | The **1920 × 1080 (landscape) edition**: `pages/`, `pages-illustrator/`, `previews/`, `spec/`, `figma/` (same structure as the root), plus `AFAQ-Corporate-Profile-1920x1080.ai` and `.pdf`. |
| `AFAQ-Corporate-Profile-1080x1920.ai` / `.pdf` | Portrait edition as an editable vector Illustrator/PDF file (8 pages = 8 artboards). |
| `pages-illustrator/` | The same eight pages with PostScript font names (`Inter-Light`, `Inter-Regular`, `Inter-Medium`, `Inter-SemiBold`) so Illustrator resolves every weight. **Use these for Illustrator.** |
| `previews/` | PNG render of each page, `contact-sheet.png`, and `deck-preview.pdf` (8 pages at 1080 × 1920 px). |
| `assets/logo/` | AFQ wordmark and "ENERGY. ENGINEERED." lockup in teal / cream / lime / white. |
| `assets/graphics/` | Three-layer ribbon (lime + teal underside + orange edge), ribbon-on-dark, lime-only ribbon, tab panels, photo-slot shapes with a notch at each corner, dark photo slots with the three placeholder scenes. |
| `assets/icons/` | 18 stroke icons (48-grid) used in the deck + `_icon-sheet.svg`. |
| `assets/palette/` | `afaq-palette.svg` sheet, `afaq-palette.ase` (Illustrator swatches), `palette.json`. |
| `fonts/` | Inter Light / Regular / Medium / Semi Bold (SIL OFL). Install before opening in Illustrator. |
| `figma/` | `figma-build.js` (Plugin-API builder), `scripter-build-all.js` (paste-and-run, all 8 slides), `slides/slide-0X.js` (one self-contained script per slide for the Figma MCP `use_figma` tool, each under 50 k chars). |
| `spec/deck-spec.json` | The single source of truth: every element, position, size, colour and text of every page. |
| `tools/` | `deck.py` (spec → SVG + assets + JSON + Figma scripts), `render.sh` (SVG → PNG), `lint_svgs.py` (import-safety, bounds and spec-sync checks). |
| `source/` | The original PDF, the complete extracted copy (`extracted-text.md`), and your three brand boards. |

## Import into Figma

**Option A — drag & drop (works today).**
1. Open <https://www.figma.com/design/ccLJTZvL8LndrWwdwVXDsu> (or any file).
2. Drag the eight files from `pages/` onto the canvas. Each becomes a `Frame` 1080 × 1920 whose children are native rectangles, vectors and text layers, named after the layer ids (`Header`, `Title`, `Card-01`, `Ribbon-Lime`, `Photo-Hero__set-image-fill` …). The ribbons intentionally run 60 px past both page edges; the page frame clips them.
3. Text imports as Inter 300/400/500/600 (Inter ships with Figma). Multi-line paragraphs arrive **one text layer per line** (grouped, e.g. `Body-1`), because that is the only form both Figma and Illustrator position identically. For real paragraph text nodes use Option B.
4. Photos: select the shape `…__set-image-fill` → Fill → **Image** → choose a photo (Fill/Crop) → delete the sibling group `Placeholder-Art`. The notch and rounded corners stay intact — no mask involved.

**Option B — native build with real paragraph text (recommended once).**
1. In Figma: Resources → Plugins → search **Scripter** → run it.
2. Open `figma/scripter-build-all.js`, copy everything, paste into Scripter, press Run.
3. All eight frames appear to the right of existing content: paragraphs are single auto-height text nodes, gradients are Figma gradients, and every vector goes through Figma's own SVG importer (exact geometry).

**Option C — Figma MCP (`use_figma`).** Each `figma/slides/slide-0X.js` is a self-contained script. The account's Starter-plan MCP quota was exhausted on 1 Oct 2026, so this path resumes when the quota resets or the plan is upgraded.

## Import into Adobe Illustrator

**Option A — the .ai file (whole deck, 8 artboards).**
1. Install the four fonts in `fonts/` (or any Inter build).
2. File → Open `landscape/AFAQ-Corporate-Profile-1920x1080.ai` (portrait: `AFAQ-Corporate-Profile-1080x1920.ai`). In the "PDF Import Options" dialog set the page range to **All** so every page becomes its own artboard (Illustrator 2020 or later; older versions open one page at a time). Illustrator treats the file as PDF content: every shape is an editable path, gradients are native, and all text is live point text in Inter Light/Regular/Medium/Semi Bold. The `.pdf` next to it is byte-identical and opens the same way.
3. The file has no layer names (PDF has no layers); if you want named layers, use Option B.

**Option B — one SVG per page (named layers).**
1. Install the four fonts in `fonts/` (or any Inter build).
2. File → Open any `pages-illustrator/*.svg` (landscape: `landscape/pages-illustrator/*.svg`). The artboard is 1080 × 1920; groups come in named; text stays live point text; paths are editable with round caps/joins; gradients are native.
3. Swatches: Window → Swatches → menu → Open Swatch Library → Other Library → `assets/palette/afaq-palette.ase`.
4. Photos: File → Place the photo, then send it **behind** the slot shape (Object → Arrange → Send Backward until it sits directly under `Photo-…__set-image-fill`), select both, Object → Clipping Mask → Make (Ctrl/Cmd + 7). The slot shape must be on top; its gradient fill is removed automatically. Then delete the `Placeholder-Art` group.
5. Export: the ribbons run 60 px past the artboard on both sides on purpose. Export with File → Export → Export As… and tick **Use Artboards** (or Export for Screens); do not use "fit to artwork bounds".

## Design system

| Token | Value | Use |
|---|---|---|
| Lime | `#C8FB5F` | Accent, ribbons, tabs, badges, icon discs |
| Teal | `#053C45` | Dark backgrounds, titles on light |
| Teal Ink | `#03343D` | Wordmark on light, text on orange |
| Teal Mid / Soft | `#0E5560` / `#1F7580` | Cards and ribbon underside on dark pages |
| Cream | `#F5F4EB` | Light backgrounds |
| White | `#FFFFFF` | Cards on light |
| Orange | `#FD7E25` | Label blocks, sun, accent rule, ribbon edge (shapes only) |
| Orange Deep | `#B04C0E` | Accent text on white / cream (passes WCAG AA) |
| Charcoal | `#202C28` | Panel silhouettes |
| Muted | `#5A7175` | Secondary text on light |

Type (Inter): page title Light 76/84, letter-spacing −2 %; cover headline Light 92/100; card/step heading Semi Bold 32/40 (28/36 in half-width cards); body Regular 21–26 at ~1.45 line-height; labels Medium 13–18 uppercase, tracking +16–22 %; tagline tracked to the wordmark width. Page margin 72 px, content width 936 px, footer rule at y = 1800, content ends by y = 1744.

## Regenerate

```bash
pip install pillow fonttools reportlab
python3 tools/deck.py           # portrait: pages/, pages-illustrator/, assets/, spec/, figma/
python3 tools/deck_landscape.py # landscape/ (pages, spec, figma) + the .ai/.pdf files for both orientations
python3 tools/lint_svgs.py     # import-safety, on-canvas bounds, text-in-margins and spec↔Figma-script sync (must print ALL CLEAN)
bash tools/render.sh           # previews/ (needs Chromium; set CHROME=/path/to/chrome)
```

Edit copy, colours or layout in `tools/deck.py` (portrait) or `tools/deck_landscape.py` (landscape), one function per slide, and re-run; the SVGs, the Figma scripts and the JSON spec stay in sync because they all come from the same spec. Placeholder art is asserted to stay inside its photo slot at build time.

## Notes on the source

- The PDF (`source/AFAQ_Corporate_Profile_English.pdf`) is a Chrome "print to PDF" of a web page at US Letter (612 × 792 pt, 7 pages). Long lines were clipped at the right edge in the PDF; the copy here is the complete text from the page source (`source/extracted-text.md`), reproduced verbatim.
- The PDF contains **no embedded raster images** — both photo areas are empty placeholders — so there was nothing to extract; the deck provides proper photo slots instead.
- The PDF used IBM Plex Sans and a navy/green scheme. Per your request the deck follows the AFQ brand boards instead (geometric sans, lime/teal/cream/orange, ribbons and tab panels) and is laid out at 1080 × 1920.
- Only two strings come from the boards rather than the PDF: "ENERGY. ENGINEERED." (tagline) and the services list "SOLAR / STORAGE / ELECTRICAL / ENGINEERING" in the label tabs. The "Deliverable:" sentences are shown as a label plus the sentence; everything else is the PDF copy word for word.

## Open questions

1. **Wordmark AFQ vs AFAQ.** The boards spell the mark AFQ; the copy says AFAQ. The deck follows the boards. Say the word and the second A is added to the lockup.
2. **Slogan punctuation.** The PDF has no full stop after "Innovating today, sustaining tomorrow"; the boards end headlines with one. The deck keeps the PDF.
3. **Photos.** Replace the three placeholder scenes (solar array, battery cabinets, transmission line) with real site photography when available; the slots are ready for image fills.

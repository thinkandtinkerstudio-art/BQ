# AFAQ Corporate Profile — 1080 × 1920 editable vector deck

> **ملخص بالعربي**
>
> - ده إعادة بناء كاملة للبروفايل (8 صفحات) بمقاس **1080 × 1920** بنفس جرافيكس البراند (AFQ): اللايم، التيل الغامق، الكريمي، البرتقالي، الريبون، التابات المدوّرة، والأيقونات.
> - **الخلفيات مش هتطلع سودة**: كل شكل ليه لون صريح (hex) جوه الـ SVG، مفيش CSS ولا `<style>` ولا متغيرات.
> - **مفيش ماسكات خالص**: مكان الصورة شكل واحد اسمه `Photo-…__set-image-fill` — تختاره في فيجما أو إليستريتور وتعمله Image Fill وتحذف جروب `Placeholder-Art`. دي أنظف طريقة من الماسك ومش بتضرب.
> - **النصوص كلها قابلة للتعديل** (`<text>`، خط Inter) والأشكال كلها فيكتور، مفيش حاجة Raster.
> - **فيجما**: اسحب الـ 8 ملفات من `pages/` جوه الملف ده: <https://www.figma.com/design/ccLJTZvL8LndrWwdwVXDsu> (ملف فاضي اتعمل لك). كل صفحة بتدخل كـ Frame 1080×1920 بطبقات أصلية (Rect / Vector / Text).
> - الحساب خلّص **حد استخدام Figma MCP الشهري (Starter plan)** من أول أمر كتابة، فمقدرتش أرسم جواه مباشرة. بدل ما تستنى: الملف `figma/scripter-build-all.js` يبني الـ 8 صفحات **Native** في فيجما (Text حقيقي بـ paragraphs وليس سطر‑سطر) عن طريق بلجن Scripter في أقل من دقيقة — الخطوات تحت.
> - ملاحظة: اللوجو في الـ boards بتاعتك مكتوب **AFQ** (ثلاث حروف) فمشيت عليه، والاسم الكامل "AFAQ for Energy & Integrated Business" موجود في النصوص. لو عايزه AFAQ قولّي.

---

## What's inside

| Folder | Contents |
|---|---|
| `pages/` | One SVG per page, `01-cover.svg` … `08-contact.svg`, each exactly **1080 × 1920**. Inline hex fills only, editable `<text>`, absolute `M/L/C/Z` paths, no masks, no clipPath, no CSS, no transforms, no rasters. |
| `previews/` | PNG renders of each page (Chromium + Inter) and `contact-sheet.png`. |
| `assets/logo/` | AFQ wordmark + "ENERGY. ENGINEERED." lockup in teal / cream / lime / white. |
| `assets/graphics/` | Ribbon (lime-teal-orange and lime-only), tab panels, photo-slot shapes with a notch at each corner, plain photo slot. |
| `assets/icons/` | 18 stroke icons (48-grid) used in the deck + `_icon-sheet.svg`. |
| `assets/palette/` | `afaq-palette.svg` sheet, `afaq-palette.ase` (Illustrator swatches), `palette.json`. |
| `fonts/` | Inter Light / Regular / Medium / Semi Bold (SIL OFL). Install before opening in Illustrator. |
| `figma/` | `figma-build.js` (Plugin-API builder), `scripter-build-all.js` (paste-and-run), `slides/slide-0X.js` (one script per slide for the Figma MCP `use_figma` tool). |
| `spec/deck-spec.json` | The single source of truth: every element, position, size, colour and text of every page. |
| `tools/` | `deck.py` (spec → SVG + assets + JSON), `render.sh` (SVG → PNG), `lint_svgs.py` (import-safety checks). |
| `source/` | The original PDF, the full extracted copy (`extracted-text.md`), and your three brand boards. |

## Import into Figma

**Option A — drag & drop (works today).**
1. Open <https://www.figma.com/design/ccLJTZvL8LndrWwdwVXDsu> (or any file).
2. Drag the eight files from `pages/` onto the canvas. Each becomes a `Frame` 1080 × 1920 whose children are native rectangles, vectors and text layers, named after the layer ids (`Header`, `Title`, `Card-01`, `Ribbon-Lime`, `Photo-Hero__set-image-fill` …).
3. Text imports as Inter 300/400/500/600 (Inter ships with Figma). Multi-line paragraphs arrive **one text layer per line** (grouped, e.g. `Body-1`), because that is the only form both Figma and Illustrator position identically.
4. Photos: select the shape `…__set-image-fill` → Fill → **Image** → choose a photo (Fill/Crop) → delete the sibling group `Placeholder-Art`. The notch and rounded corners stay intact — no mask involved.

**Option B — native build with real paragraph text (recommended once).**
1. In Figma: Resources → Plugins → search **Scripter** → run it.
2. Open `figma/scripter-build-all.js`, copy everything, paste into Scripter, press Run.
3. All eight frames appear to the right of existing content, with paragraphs as single auto-height text nodes, gradients as Figma gradients, and every vector imported through Figma's own SVG importer (exact geometry).

**Option C — Figma MCP (`use_figma`).** Each `figma/slides/slide-0X.js` is a self-contained script under the tool's 50 k-character limit. The account's Starter-plan MCP quota was exhausted on 1 Oct 2026, so this path resumes when the quota resets or the plan is upgraded.

## Import into Adobe Illustrator

1. Install the four fonts in `fonts/` (or any Inter build).
2. File → Open any `pages/*.svg`. The artboard is 1080 × 1920; groups come in named; text stays live point text; paths are editable with round caps/joins; gradients are native.
3. Swatches: Window → Swatches → menu → Open Swatch Library → Other Library → `assets/palette/afaq-palette.ase`.
4. Photos: select `Photo-…__set-image-fill`, then Object → Clipping Mask → Make with a placed image on top of it, or simply use it as the clipping shape. Delete `Placeholder-Art` afterwards.

## Design system

| Token | Value | Use |
|---|---|---|
| Lime | `#C8FB5F` | Accent, ribbons, tabs, badges |
| Teal | `#053C45` | Dark backgrounds, titles on light |
| Teal Ink | `#03343D` | Wordmark on light |
| Teal Mid | `#0E5560` | Cards on dark |
| Cream | `#F5F4EB` | Light backgrounds |
| White | `#FFFFFF` | Cards on light |
| Orange | `#FD7E25` / `#D9641A` | Labels, sun, accent rule / accent text |
| Charcoal | `#202C28` | Panel silhouettes |
| Muted | `#5A7175` | Secondary text on light |

Type (Inter): page title Light 76/84, letter-spacing −2 %; cover headline Light 92/100; card heading Semi Bold 28–36; body Regular 21–26 at 1.45–1.55 line-height; labels Medium 13–18 uppercase, tracking +16–30 %. Page margin 72 px, content width 936 px, footer rule at y = 1800.

## Regenerate

```bash
pip install pillow fonttools
python3 tools/deck.py          # rewrites pages/, assets/, spec/
python3 tools/lint_svgs.py     # import-safety checks (must print ALL CLEAN)
bash tools/render.sh           # previews/ (needs Chromium; set CHROME=/path/to/chrome)
```

Edit copy, colours or layout in `tools/deck.py` (one function per slide) and re-run; the SVGs, the Figma scripts and the JSON spec stay in sync because they all come from the same spec.

## Notes on the source

- The PDF (`source/AFAQ_Corporate_Profile_English.pdf`) is a Chrome "print to PDF" of a web page at US Letter (612 × 792 pt, 7 pages). Long lines were clipped at the right edge in the PDF; the copy here is the complete text from the page source (`source/extracted-text.md`).
- The PDF contains **no embedded raster images** — both photo areas are empty placeholders — so there was nothing to extract; the deck provides proper photo slots instead.
- The PDF used IBM Plex Sans and a navy/green scheme. Per your request the deck follows the AFQ brand boards instead (Inter-style geometric sans, lime/teal/cream/orange, ribbons and tab panels) and is laid out at 1080 × 1920.

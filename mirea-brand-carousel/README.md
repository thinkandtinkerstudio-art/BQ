# MIREA — Brand Guidelines Carousel (Figma plugin, 11 × 1305 × 1631)

> **ملخص بالعربي**
>
> - ده **Figma plugin** بيبني كاروسيل Brand Guidelines لبراند **MIREA** (Eau de Parfum) من **11 سلايد بمقاس 1305 × 1631** (بوست إنستجرام 4:5)، بنفس هوية الباكدجينج اللي بعتّه: الرملي، الكاكاو، الروز، الأزرق الباودر، اللوحات الكلاسيكية، البلاكة بالزوايا المقصوصة، النجمة ✦، والـ manifesto الرأسي.
> - اللوجوهات الخمسة (Stacked, Horizontal, Symbol, Round seal, Oval badge) **متسحوبة فيكتور من ملف الـ PDF بتاعك** بنفس النقط، مش معاد رسمها. البالِت بنفس قيم الـ hex بالظبط من artboard الألوان.
> - **الخط**: الكاروسيل مظبوط على **Condor Extended** (Bold للعناوين والووردمارك، Regular للـ descriptors والـ labels) و**Syne** للنصوص. البلجن بيدوّر على Condor Extended المثبّت على جهازك ويستخدمه؛ لو مش مثبّت بيكتب تحذير أصفر ويستخدم بديل مؤقت (Archivo Expanded / Syncopate / Inter). **ثبّت Condor Extended قبل ما تشغّل البلجن.** صور المعاينة في `previews/` مرسومة ببديل مفتوح (Archivo بعرض 125%) لأن Condor خط مرخّص مش معانا هنا.
> - **لوجو الاستوديو**: مش مبعوت في الرسالة، فالسلايد 01 و11 عليهم placeholder كتابي ("THINK & TINKER STUDIO" — غيّر النص من شباك البلجن). من شباك البلجن اختار ملف **SVG أو PNG** للوجو الاستوديو وهو هيتحط مكانه تلقائيًا ويتلوّن بلون البراند.
> - **ريفرنس "الشنطة"**: مش موجود في الرسالة ولا في الريبو، فمقدرتش أطابقه حرفيًا. التقسيم هنا كاروسيل brand-guidelines إيديتوريال: Cover ← The brand ← Logo ← Logo system ← Logo rules ← Colour ← Typography ← Graphic elements ← Packaging ← Art direction ← Closing. ابعت الريفرنس وأنا أعيد توزيع السلايدات عليه؛ كل التوزيع في ملف واحد (`src/scene.ts`).
> - **التشغيل (Figma Desktop)**: Plugins ‹ Development ‹ **Import plugin from manifest…** واختار `figma-plugin/mirea-brand-guidelines/manifest.json`، وبعدين Plugins ‹ Development ‹ **MIREA Brand Guidelines Carousel** ‹ **Build carousel**. البلجن بيعمل صفحة `MIREA — Brand Guidelines (1305×1631)` ويبني الـ 11 فريم جنب بعض. إعادة التشغيل آمنة (بيستبدل الفريمات اللي بنفس الاسم بس).
> - **الصور** (اللوحات الأربعة ورندر الدايلاينز الأربعة) البلجن بيحمّلها من GitHub وقت التشغيل (الخيار شغّال افتراضيًا). لو مفيش إنترنت، أماكن الصور بتطلع فريمات متقطعة اسمها `Photo — … — replace fill with image`: اختارها و Fill ← Image.
> - **نسخة في مكتبة حساب Figma**: نفس البلجن متضاف في حسابك (team "Abdulrahman Taha's team") باسم **MIREA Brand Guidelines Carousel** — رابط التجربة في آخر الملف ده.
> - **التصدير**: اختار الـ 11 فريم ← Export ← PNG ‹ 1x (1305 × 1631) أو JPG.
> - **التحميل**: `downloads/mirea-brand-guidelines-plugin.zip` (البلجن بس) و `downloads/mirea-brand-carousel-complete.zip` (كل حاجة).

---

## What it is

A Figma plugin that builds the MIREA brand-guidelines carousel — **11 frames, 1305 × 1631 px** (Instagram 4:5 post) — as native, editable Figma layers (frames, rectangles, vectors and real text), using the brand's own assets:

| # | Slide | Content |
|---|---|---|
| 01 | Cover | Box-front composition: the painting, the notched ivory plaque with eyebrow / symbol / wordmark / sparkle, vertical manifesto, cocoa band with the horizontal lockup and the studio credit |
| 02 | The brand | "Every moment leaves a trace." — story, the three pillars (Moments. Opportunities. Choices.), the tagline rule |
| 03 | The logo | Primary lockup on a plaque with callouts; the symbol and the wordmark explained |
| 04 | Logo system | Five lockups extracted from the PDF: stacked, horizontal, symbol, round seal, oval badge — with use cases |
| 05 | Logo rules | Clear space (x = cap height of M), minimum sizes, four approved colour versions |
| 06 | Colour palette | 5 primaries + 5 neutral tints with HEX / RGB / CMYK (conversions) and roles, proportion rule |
| 07 | Typography | Condor Extended specimen, weights, usage; Syne as secondary; hierarchy table (dark slide) |
| 08 | Graphic elements | The sparkle divider, the vertical manifesto, the plaque, the eyebrow — each demonstrated |
| 09 | Packaging | The four dielines (Milano 01 sand / blue, Floral rose / muse) with captions and the 50 ml spec line |
| 10 | Art direction | The four paintings with captions, imagery rules and four "do" bullets |
| 11 | Closing | "Memories in the making." on espresso, symbol, credit line and studio logo |

Every element of every slide is defined once in `src/scene.ts` (positions, sizes, colours, copy) and rendered twice: to HTML/PNG previews by Chromium (`previews/`) and to Figma layers by the plugin (`figma-plugin/`). Change the copy or layout in `src/brand.ts` / `src/scene.ts` and run `npm run all`.

## Folder map

| Path | Contents |
|---|---|
| `figma-plugin/mirea-brand-guidelines/` | **The plugin** — `manifest.json`, `code.js` (compiled), `code.ts` (bundled source), `ui.html`. Import this folder's manifest in Figma Desktop. |
| `assets/logo/` | The five MIREA logos as clean SVG (absolute M/L/C/Z paths, 4× PDF points), extracted from `mira.pdf` pages 2–6, plus `logo-manifest.json`. Fill `#6A4937` as in the artboards; the plugin recolours them. |
| `assets/images/` | The four paintings from the packaging PDF (1600 px JPEG): `balustrade`, `arches`, `muse`, `clouds`. |
| `assets/packaging/` | Dieline renders: the four "Casa de Perfumes" assets (`milano-01-sand`, `floral-rose-balustrade`, `milano-01-blue`, `floral-rose-muse`) and the four "Eau de Parfum" artboards (`edp-*`). |
| `previews/` | PNG of each slide at 1305 × 1631 and `contact-sheet.png`. Display face is a stand-in (see Fonts). |
| `src/` | `brand.ts` (tokens, copy, palette), `scene.ts` (slide builder), `figma-main.ts` (plugin sandbox), `ui.html` (plugin window), `logos.gen.ts` (generated from `assets/logo`). |
| `tools/` | `extract_logos.js` (PDF→SVG cleanup), `gen_logos_ts.js`, `build_plugin.js` (bundle + `tsc`), `render_preview.js` (Chromium previews), `mock_figma_test.js` (smoke test against a mock Plugin API). |
| `build/mcp/` | The account-library version of the plugin (`code.ts` + `ui.html`). Same design code; the five logo SVGs are downloaded from this repository at run time instead of being embedded (the local plugin embeds them). |
| `fonts/` | Syne and Archivo (SIL OFL) — used **only** for the previews. Condor Extended is not included (licensed). |
| `downloads/` | Zips of the plugin and of the whole package. |

## Fonts

- **Condor Extended** (Lost Type) — primary. Wordmark & headlines **Bold**, descriptors / labels / manifesto **Regular**, uppercase, +10…+26 % tracking. The plugin looks for any installed family whose name contains "Condor" and "Ext" (also "Condor" with "Extended …" styles) and reports what it found in the log. If it is not installed the log turns yellow and a stand-in is used (Archivo Expanded → Syncopate → Inter); text boxes are sized for Condor Extended, so install it and run again.
- **Syne** — secondary (body, captions). Available in Figma as a Google Font; nothing to install.
- Preview PNGs use Archivo at 125 % width as an open stand-in for Condor Extended, so line breaks may differ slightly from the Figma result.

## Running the plugin

1. Figma Desktop → **Plugins ‹ Development ‹ Import plugin from manifest…** → `figma-plugin/mirea-brand-guidelines/manifest.json`.
2. **Plugins ‹ Development ‹ MIREA Brand Guidelines Carousel.**
3. In the window: slides (`1-11`), page name, studio name / handle / edition label, **Studio logo** (SVG or PNG — replaces the typographic placeholder on slides 01 and 11; SVGs are tinted to the brand colour), **Images** (downloaded from GitHub; the base URL points at this repository branch).
4. **Build carousel.** Each step logs green / yellow / red; **Copy log** copies it for a bug report.
5. Export: select the frames → Export → PNG 1× (1305 × 1631).

Re-running replaces only frames with the same names on that page. Relaunch button: select any built frame → "Rebuild the MIREA carousel".

### Account-library version

The identical plugin is published to the Figma account library (plan: *Abdulrahman Taha's team*) under the name **MIREA Brand Guidelines Carousel**. Open a new design file with it ready to run:

<https://www.figma.com/file/new?try-tool-resource-content-id=bc0888f3-2b43-4bc8-89c1-abaf56262057&try-tool-resource-type=gen_tool&type=design&mode=design>

(Add the same two `try-tool-…` query parameters to any existing file URL to open it there.) This version downloads the logo vectors and the images from the Base URL shown in its window, so it needs internet access; the local plugin above embeds the logos.

## Brand facts used

- Palette (from the palette artboard): Cocoa `#7B5A41`, Sand `#E1C9AE`, Dusty Rose `#B96E64`, Powder Blue `#B9CAD0`, Espresso `#342B25`; tints Ivory `#F9F8F3`, Linen `#EAE6D6`, Nude `#ECD4B8`, Oat `#B8A47D`, Camel `#93744D`. CMYK values on slide 06 are arithmetic conversions, not press values.
- The logo artboards use `#6A4937` for the logo; the carousel sets logos in palette Cocoa `#7B5A41` for consistency with the colour slide. Change `COLORS.cocoa` or the fill in `logo()` if you prefer the artboard brown.
- Copy on the boxes (eyebrow, manifesto, "Every moment leaves a trace.", story, 50 ml · 1.7 fl.oz, Made in Egypt, Milano 01 / Floral, Casa de Perfumes) is reproduced as written; the guideline explanations are new.

## Regenerate

```bash
npm install                 # typescript, @figma/plugin-typings, playwright (Chromium is pre-installed here)
npm run build               # logos → src/logos.gen.ts, compile scene for Node, bundle + compile the plugin
npm test                    # smoke test of code.js against a mock Figma API
npm run preview             # previews/*.png with Chromium
```

To re-extract the logos from a new PDF: `pdftocairo -svg -f N -l N file.pdf page.svg`, then `node tools/extract_logos.js <dir> assets/logo`.

## Open items

1. **Bag-brand reference carousel** — not received; the slide structure here is an editorial brand-guidelines sequence. Send the reference and the layout can be re-flowed to match it (one file: `src/scene.ts`).
2. **Studio logo** — not received; typographic placeholder "THINK & TINKER STUDIO" on slides 01 and 11, replaceable from the plugin window.
3. **Condor Extended** must be installed on the computer that runs the plugin.

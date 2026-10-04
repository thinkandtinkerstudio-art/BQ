// ─────────────────────────────────────────────────────────────────────────────
// Figma plugin — sandbox side. Builds the MIREA brand-guidelines carousel
// (11 frames, 1305 × 1631) from the shared scene (brand.ts + scene.ts).
// ─────────────────────────────────────────────────────────────────────────────
const PANEL_WIDTH = 440;
const RELAUNCH_COMMAND = '__RELAUNCH_COMMAND__';
const FRAME_GAP = 120;

type StudioLogoMsg = { kind: 'svg'; text: string } | { kind: 'png'; bytes: Uint8Array; width: number; height: number } | null;
interface BuildMessage {
  slides: number[];
  studioName: string;
  studioHandle: string;
  edition: string;
  pageName: string;
  studioLogo: StudioLogoMsg;
  images: { [key: string]: Uint8Array };
  logos?: { [id: string]: string }; // SVG text per logo id — only used by builds that load the logo artwork at run time
}
type UiMessage =
  | { type: 'resize'; height: number }
  | { type: 'build'; options: BuildMessage }
  | { type: 'close' };

interface ResolvedFonts { display: FontName; displayBold: FontName; body: FontName; bodyMedium: FontName; bodyBold: FontName }
interface Ctx { fonts: ResolvedFonts; images: { [key: string]: string }; parent: PageNode }

let building = false;

function post(msg: { [key: string]: unknown }): void {
  try { figma.ui.postMessage(msg); } catch (e) { /* UI closed */ }
}
function log(step: string, status: 'run' | 'done' | 'warn' | 'error', detail?: string): void {
  post({ type: 'log', step, status, detail: detail || '' });
}
function errText(e: unknown): string {
  if (e instanceof Error) return e.message;
  return String(e);
}
function tick(): Promise<void> { return new Promise((resolve) => setTimeout(resolve, 0)); }

// ── colours ──────────────────────────────────────────────────────────────────
function hexToRgb(hex: string): RGB {
  const h = hex.replace('#', '');
  return { r: parseInt(h.slice(0, 2), 16) / 255, g: parseInt(h.slice(2, 4), 16) / 255, b: parseInt(h.slice(4, 6), 16) / 255 };
}
function solid(hex: string, opacity?: number): SolidPaint {
  const p: SolidPaint = { type: 'SOLID', color: hexToRgb(hex) };
  return opacity == null ? p : Object.assign({}, p, { opacity });
}

// ── fonts ────────────────────────────────────────────────────────────────────
async function resolveFonts(): Promise<ResolvedFonts> {
  const all = await figma.listAvailableFontsAsync();
  const names: FontName[] = all.map((f) => f.fontName);
  const lower = (s: string) => s.toLowerCase();
  function pick(familyTest: (fam: string, style: string) => boolean, stylePrefs: RegExp[]): FontName | null {
    const cands = names.filter((n) => familyTest(lower(n.family), lower(n.style)));
    for (const re of stylePrefs) {
      const hit = cands.filter((n) => re.test(lower(n.style)));
      if (hit.length) return hit[0];
    }
    return null;
  }
  // 1. Condor Extended — family "Condor Extended" (styles Regular/Bold…) or family "Condor" with "Extended …" styles.
  const isCondorExt = (fam: string, style: string) => fam.indexOf('condor') >= 0 && (fam.indexOf('ext') >= 0 || style.indexOf('ext') >= 0);
  const notItalic = (re: RegExp) => new RegExp('^(?!.*italic)(?!.*oblique)' + re.source);
  const display =
    pick(isCondorExt, [/^(extended )?regular$/, /regular/, /book/, /medium/, /light/].map(notItalic)) ||
    pick((f) => f === 'archivo', [/expanded regular/, /expanded medium/, /semiexpanded regular/].map(notItalic)) ||
    pick((f) => f === 'syncopate', [/regular/]) ||
    { family: 'Inter', style: 'Regular' };
  const displayBold =
    pick(isCondorExt, [/^(extended )?bold$/, /bold/, /semi ?bold/, /black/, /heavy/, /medium/].map(notItalic)) ||
    pick((f) => f === 'archivo', [/expanded bold/, /expanded semi ?bold/, /expanded black/].map(notItalic)) ||
    pick((f) => f === 'syncopate', [/bold/]) ||
    { family: 'Inter', style: 'Bold' };
  const body = pick((f) => f === 'syne', [/^regular$/]) || { family: 'Inter', style: 'Regular' };
  const bodyMedium = pick((f) => f === 'syne', [/^medium$/, /semi ?bold/, /^regular$/]) || { family: 'Inter', style: 'Medium' };
  const bodyBold = pick((f) => f === 'syne', [/^bold$/, /extra ?bold/, /semi ?bold/]) || { family: 'Inter', style: 'Bold' };
  const fonts: ResolvedFonts = { display, displayBold, body, bodyMedium, bodyBold };
  const keys: (keyof ResolvedFonts)[] = ['display', 'displayBold', 'body', 'bodyMedium', 'bodyBold'];
  for (const k of keys) {
    try { await figma.loadFontAsync(fonts[k]); }
    catch (e) {
      const fb: FontName = { family: 'Inter', style: k === 'displayBold' || k === 'bodyBold' ? 'Bold' : k === 'bodyMedium' ? 'Medium' : 'Regular' };
      await figma.loadFontAsync(fb);
      fonts[k] = fb;
      log('Fonts', 'warn', k + ': ' + fonts[k].family + ' could not be loaded, using Inter.');
    }
  }
  const condorOk = fonts.display.family.toLowerCase().indexOf('condor') >= 0 && fonts.displayBold.family.toLowerCase().indexOf('condor') >= 0;
  log('Fonts', condorOk ? 'done' : 'warn',
    'Display: ' + fonts.display.family + ' ' + fonts.display.style + ' / ' + fonts.displayBold.style +
    '  ·  Body: ' + fonts.body.family + ' ' + fonts.body.style + ' / ' + fonts.bodyBold.style +
    (condorOk ? '' : '  —  Condor Extended is not installed on this computer, so a stand-in is used. Install Condor Extended and run again.'));
  return fonts;
}

// ── page ─────────────────────────────────────────────────────────────────────
async function getPage(name: string): Promise<PageNode> {
  const existing = figma.root.children.filter((p) => p.name === name)[0];
  if (existing) { await existing.loadAsync(); await figma.setCurrentPageAsync(existing); return existing; }
  try {
    const page = figma.createPage();
    page.name = name;
    await figma.setCurrentPageAsync(page);
    log('Page', 'done', 'Created page "' + name + '".');
    return page;
  } catch (e) {
    log('Page', 'warn', 'Could not add a page (' + errText(e) + '). Building on the current page instead.');
    return figma.currentPage;
  }
}

// ── node builders ────────────────────────────────────────────────────────────
function applyStroke(node: RectangleNode | EllipseNode, n: SRect | SEllipse): void {
  if (!n.stroke) return;
  node.strokes = [solid(n.stroke)];
  node.strokeWeight = n.strokeW || 1;
  node.strokeAlign = 'INSIDE';
  if ('dash' in n && n.dash) node.dashPattern = n.dash;
}
function buildRect(n: SRect): RectangleNode {
  const r = figma.createRectangle();
  r.name = n.name;
  r.resize(Math.max(0.01, n.w), Math.max(0.01, n.h));
  r.fills = n.fill ? [solid(n.fill)] : [];
  if (n.radius) r.cornerRadius = n.radius;
  applyStroke(r, n);
  if (n.opacity != null) r.opacity = n.opacity;
  return r;
}
function buildEllipse(n: SEllipse): EllipseNode {
  const e = figma.createEllipse();
  e.name = n.name;
  e.resize(Math.max(0.01, n.w), Math.max(0.01, n.h));
  e.fills = n.fill ? [solid(n.fill)] : [];
  applyStroke(e, n);
  if (n.opacity != null) e.opacity = n.opacity;
  return e;
}
function buildText(n: SText, fonts: ResolvedFonts): TextNode {
  const t = figma.createText();
  t.name = n.name;
  t.fontName = fonts[n.font];
  t.characters = n.text;
  t.fontSize = n.size;
  t.lineHeight = { value: n.lh, unit: 'PIXELS' };
  t.letterSpacing = { value: n.ls || 0, unit: 'PERCENT' };
  t.textAlignHorizontal = n.align === 'center' ? 'CENTER' : n.align === 'right' ? 'RIGHT' : 'LEFT';
  if (n.rotate) t.textAutoResize = 'WIDTH_AND_HEIGHT'; // rotated labels never wrap
  else { t.textAutoResize = 'HEIGHT'; t.resize(n.w, n.lh); }
  t.fills = [solid(n.fill)];
  if (n.opacity != null) t.opacity = n.opacity;
  return t;
}
function placeText(t: TextNode, n: SText): void {
  if (!n.rotate) { t.x = n.x; t.y = n.y; return; }
  // Rotate around the centre of the (unrotated) box, like the preview's CSS transform.
  const cx = n.x + n.w / 2, cy = n.y + n.h / 2, w = t.width, th = t.height;
  if (n.rotate === -90) t.relativeTransform = [[0, 1, cx - th / 2], [-1, 0, cy + w / 2]];
  else t.relativeTransform = [[0, -1, cx + th / 2], [1, 0, cy - w / 2]];
}
function buildSvg(n: SSvg): FrameNode {
  const f = figma.createNodeFromSvg(n.svg);
  f.name = n.name;
  if (f.width > 0) f.rescale(n.w / f.width);
  if (n.opacity != null) f.opacity = n.opacity;
  return f;
}
function buildImage(n: SImage, ctx: Ctx): SceneNode {
  const hash = ctx.images[n.src];
  const r = figma.createRectangle();
  r.resize(Math.max(1, n.w), Math.max(1, n.h));
  if (n.radius) r.cornerRadius = n.radius;
  if (hash) {
    r.name = n.name;
    r.fills = [{ type: 'IMAGE', scaleMode: 'FILL', imageHash: hash }];
    if (n.opacity != null) r.opacity = n.opacity;
    return r;
  }
  // Placeholder: replace the fill with the image (Fill → Image).
  r.name = 'Photo — ' + n.src + ' — replace fill with image';
  r.fills = [solid(COLORS.linen)];
  r.strokes = [solid(COLORS.oat)];
  r.strokeWeight = 1;
  r.dashPattern = [10, 8];
  return r;
}

async function buildSlide(sl: Slide, ctx: Ctx, x: number): Promise<FrameNode> {
  const frame = figma.createFrame();
  frame.name = sl.name;
  frame.resize(SLIDE_W, SLIDE_H);
  frame.fills = [solid(sl.bg)];
  frame.clipsContent = true;
  frame.x = x; frame.y = 0;
  ctx.parent.appendChild(frame);
  let i = 0;
  for (const n of sl.nodes) {
    let node: SceneNode;
    if (n.t === 'rect') node = buildRect(n);
    else if (n.t === 'ellipse') node = buildEllipse(n);
    else if (n.t === 'text') node = buildText(n, ctx.fonts);
    else if (n.t === 'svg') node = buildSvg(n);
    else node = buildImage(n, ctx);
    frame.appendChild(node);
    if (n.t === 'text') placeText(node as TextNode, n);
    else { node.x = n.x; node.y = n.y; }
    if (++i % 12 === 0) await tick();
  }
  try { frame.setRelaunchData({ [RELAUNCH_COMMAND]: 'Rebuild the MIREA carousel' }); } catch (e) { /* optional */ }
  return frame;
}

function svgRatio(svg: string): number {
  const vb = svg.match(/viewBox\s*=\s*"([^"]+)"/i);
  if (vb) { const p = vb[1].trim().split(/[\s,]+/).map(Number); if (p.length === 4 && p[3] > 0) return p[2] / p[3]; }
  const w = svg.match(/\swidth\s*=\s*"([\d.]+)/i), h = svg.match(/\sheight\s*=\s*"([\d.]+)/i);
  if (w && h && Number(h[1]) > 0) return Number(w[1]) / Number(h[1]);
  return 0;
}
/** Make an arbitrary SVG single-colour so it can be tinted (sand on cocoa etc.). */
function monochromeSvg(svg: string): string {
  return svg
    .replace(/fill\s*=\s*"(?!none)[^"]*"/gi, 'fill="currentColor"')
    .replace(/stroke\s*=\s*"(?!none)[^"]*"/gi, 'stroke="currentColor"')
    .replace(/fill\s*:\s*(?!none)[^;"']+/gi, 'fill:currentColor')
    .replace(/stroke\s*:\s*(?!none)[^;"']+/gi, 'stroke:currentColor');
}

async function build(m: BuildMessage): Promise<void> {
  const t0 = Date.now();
  // Logo artwork: embedded in the local build; downloaded by the plugin window in the account-library build.
  if (m.logos) for (const id of Object.keys(m.logos)) if (LOGOS[id] && m.logos[id]) LOGOS[id].svg = m.logos[id];
  const missing = Object.keys(LOGOS).filter((id) => !LOGOS[id].svg);
  if (missing.length) {
    log('Logos', 'error', 'The logo artwork could not be loaded (' + missing.join(', ') + '). Check the Base URL / internet connection and try again.');
    post({ type: 'done' });
    return;
  }
  log('Logos', 'done', Object.keys(LOGOS).length + ' lockups ready' + (LOGO_RUNTIME ? ' (downloaded)' : ' (embedded)') + '.');
  log('Fonts', 'run', 'Looking for Condor Extended and Syne…');
  const fonts = await resolveFonts();

  log('Page', 'run', '');
  const parent = await getPage(m.pageName || 'MIREA — Brand Guidelines (1305×1631)');
  log('Page', 'done', 'Building on "' + parent.name + '".');

  // images
  const images: { [key: string]: string } = {};
  const keys = Object.keys(m.images || {});
  if (keys.length) {
    log('Images', 'run', keys.length + ' file(s) received from the plugin window…');
    for (const k of keys) {
      try { images[k] = figma.createImage(m.images[k]).hash; }
      catch (e) { log('Images', 'warn', k + ': ' + errText(e)); }
      await tick();
    }
    log('Images', 'done', Object.keys(images).length + ' of ' + keys.length + ' placed as image fills.');
  } else {
    log('Images', 'warn', 'No images received — photo slots are placeholders. Select a slot and set its Fill to Image.');
  }

  // studio logo
  const opts: Partial<BuildOptions> = { studioName: m.studioName || DEFAULT_OPTIONS.studioName, studioHandle: m.studioHandle || '', edition: m.edition || DEFAULT_OPTIONS.edition };
  if (m.studioLogo && m.studioLogo.kind === 'svg') {
    opts.studioLogoSvg = monochromeSvg(m.studioLogo.text);
    opts.studioLogoRatio = svgRatio(m.studioLogo.text) || 3;
    log('Studio logo', 'done', 'SVG received — placed on the cover and the closing slide, tinted to the brand colour.');
  } else if (m.studioLogo && m.studioLogo.kind === 'png') {
    try {
      images['studio-logo'] = figma.createImage(m.studioLogo.bytes).hash;
      opts.studioLogoImageRatio = m.studioLogo.width > 0 && m.studioLogo.height > 0 ? m.studioLogo.width / m.studioLogo.height : 3;
      log('Studio logo', 'done', 'Bitmap received — placed on the cover and the closing slide.');
    } catch (e) { log('Studio logo', 'warn', errText(e)); }
  } else {
    log('Studio logo', 'warn', 'No logo file — a typographic placeholder ("' + opts.studioName + '") is used. Replace the layer named "Studio logo — placeholder".');
  }

  const ctx: Ctx = { fonts, images, parent };
  const slides = buildSlides(opts);
  const wanted = slides.filter((s, i) => m.slides.indexOf(i + 1) >= 0);
  const built: FrameNode[] = [];
  for (const sl of wanted) {
    const idx = slides.indexOf(sl);
    log(sl.name, 'run', '');
    // idempotent: remove a previous build of the same slide on this page
    for (const old of parent.children.filter((c) => c.name === sl.name && c.type === 'FRAME')) old.remove();
    try {
      const f = await buildSlide(sl, ctx, idx * (SLIDE_W + FRAME_GAP));
      built.push(f);
      log(sl.name, 'done', sl.nodes.length + ' layers');
    } catch (e) {
      log(sl.name, 'error', errText(e));
    }
    await tick();
  }
  if (built.length) {
    figma.currentPage.selection = built;
    figma.viewport.scrollAndZoomIntoView(built);
  }
  log('Done', 'done', built.length + ' slide(s) in ' + ((Date.now() - t0) / 1000).toFixed(1) + ' s. Export: select the frames → Export → PNG 1× (1305 × 1631).');
  post({ type: 'done' });
}

figma.showUI(__html__, { width: PANEL_WIDTH, height: 720, themeColors: true });
try { figma.root.setRelaunchData({ [RELAUNCH_COMMAND]: 'Build the MIREA brand-guidelines carousel' }); } catch (e) { /* optional */ }

figma.ui.onmessage = async (message: UiMessage) => {
  if (message.type === 'resize') {
    figma.ui.resize(PANEL_WIDTH, Math.max(320, Math.min(900, Math.round(message.height))));
    return;
  }
  if (message.type === 'close') {
    if (!building) figma.closePlugin();
    return;
  }
  if (message.type === 'build') {
    if (building) return;
    building = true;
    try { await build(message.options); }
    catch (e) { log('Build', 'error', errText(e)); post({ type: 'done' }); }
    building = false;
  }
};

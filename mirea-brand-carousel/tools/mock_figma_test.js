// Smoke-test the compiled plugin outside Figma with a minimal mock of the Plugin API.
// It catches runtime errors in the sandbox logic (message handling, scene → node mapping, transforms).
const fs = require('fs'); const path = require('path'); const vm = require('vm');
const code = fs.readFileSync(path.join(__dirname, '..', 'figma-plugin', 'mirea-brand-guidelines', 'code.js'), 'utf8');
let created = 0, texts = 0, svgs = 0, imagesCreated = 0; const logs = []; let uiMessages = [];
function node(type) {
  const n = { type, id: String(++created), name: '', x: 0, y: 0, width: 100, height: 100, children: [], fills: [], strokes: [], opacity: 1, removed: false,
    resize(w, h) { this.width = w; this.height = h; }, rescale(k) { this.width *= k; this.height *= k; },
    appendChild(c) { this.children.push(c); c.parent = this; }, remove() { this.removed = true; },
    setRelaunchData() {}, get relativeTransform() { return this._rt; }, set relativeTransform(v) { this._rt = v; } };
  if (type === 'TEXT') { Object.defineProperty(n, 'characters', { set(v) { this._c = v; this.width = Math.min(this.width, v.length * 10); this.height = 20; }, get() { return this._c; } }); }
  return n;
}
const fonts = [
  { fontName: { family: 'Condor Extended', style: 'Regular' } }, { fontName: { family: 'Condor Extended', style: 'Bold' } }, { fontName: { family: 'Condor Extended', style: 'Bold Italic' } },
  { fontName: { family: 'Syne', style: 'Regular' } }, { fontName: { family: 'Syne', style: 'Medium' } }, { fontName: { family: 'Syne', style: 'Bold' } }, { fontName: { family: 'Inter', style: 'Regular' } },
];
const page = Object.assign(node('PAGE'), { name: 'Page 1', loadAsync: async () => {} });
const figma = {
  ui: { postMessage(m) { uiMessages.push(m); if (m.type === 'log') logs.push(m); }, resize() {}, onmessage: null },
  root: { children: [page], setRelaunchData() {} },
  currentPage: page,
  viewport: { center: { x: 0, y: 0 }, scrollAndZoomIntoView() {} },
  showUI() {}, closePlugin() {}, notify() {},
  listAvailableFontsAsync: async () => fonts,
  loadFontAsync: async (f) => { if (!fonts.some((x) => x.fontName.family === f.family && x.fontName.style === f.style)) throw new Error('font missing ' + f.family + ' ' + f.style); },
  createPage() { const p = Object.assign(node('PAGE'), { loadAsync: async () => {} }); this.root.children.push(p); return p; },
  setCurrentPageAsync: async (p) => { figma.currentPage = p; },
  createFrame: () => node('FRAME'), createRectangle: () => node('RECTANGLE'), createEllipse: () => node('ELLIPSE'),
  createText: () => { texts++; return node('TEXT'); },
  createNodeFromSvg: (svg) => { if (!/^<svg/.test(svg)) throw new Error('bad svg'); svgs++; const f = node('FRAME'); const m = svg.match(/width="([\d.]+)" height="([\d.]+)"/); f.width = +m[1]; f.height = +m[2]; return f; },
  createImage: (bytes) => { if (!(bytes instanceof Uint8Array) || !bytes.length) throw new Error('bad bytes'); imagesCreated++; return { hash: 'h' + imagesCreated }; },
};
const ctx = { figma, __html__: '<html></html>', setTimeout, console, Uint8Array };
vm.createContext(ctx);
vm.runInContext(code, ctx);
(async () => {
  const images = {}; for (const k of ['balustrade', 'arches', 'muse', 'clouds', 'pack-milano-sand', 'pack-floral-rose', 'pack-milano-blue', 'pack-floral-muse']) images[k] = new Uint8Array([1, 2, 3]);
  await figma.ui.onmessage({ type: 'build', options: { slides: [1,2,3,4,5,6,7,8,9,10,11], pageName: 'MIREA — test', studioName: 'THINK & TINKER STUDIO', studioHandle: '@x', edition: 'EDITION 01 — 2026',
    studioLogo: { kind: 'svg', text: '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 100"><rect fill="#000" width="300" height="100"/></svg>' }, images } });
  // second run with no images / png logo, to exercise the placeholders and the idempotent rebuild
  await figma.ui.onmessage({ type: 'build', options: { slides: [1, 11], pageName: 'MIREA — test', studioName: 'ONEWORD', studioHandle: '', edition: '', studioLogo: { kind: 'png', bytes: new Uint8Array([9]), width: 400, height: 100 }, images: {} } });
  const errors = logs.filter((l) => l.status === 'error');
  const built = figma.currentPage.children.filter((c) => !c.removed);
  console.log('frames on page:', built.length, built.map((f) => f.name + ':' + f.children.length).join(' | '));
  console.log('texts', texts, 'svgs', svgs, 'images', imagesCreated, 'uiMessages', uiMessages.length);
  for (const l of logs.filter((l) => l.status !== 'run' && l.status !== 'done')) console.log(l.status.toUpperCase(), l.step, '—', l.detail);
  const sample = built[0].children.find((c) => c.name === 'Manifesto L');
  console.log('rotated text transform sample:', JSON.stringify(sample && sample.relativeTransform));
  if (errors.length) { console.error('ERRORS', errors); process.exit(1); }
  if (built.length !== 11) { console.error('expected 11 frames after idempotent rebuild'); process.exit(1); }
  console.log('MOCK TEST OK');
})().catch((e) => { console.error(e); process.exit(1); });

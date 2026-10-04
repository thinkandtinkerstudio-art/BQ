// Render every slide of the scene to HTML (previews/html) and PNG (previews/) with Chromium.
// The display face is a stand-in (Archivo, 125 % width) because Condor Extended is a licensed
// font that is not shipped here; the Figma plugin uses the real Condor Extended on your machine.
const fs = require('fs'); const path = require('path');
const { chromium } = require('playwright');
const S = require('../build/scene.node.js');
const ROOT = path.resolve(__dirname, '..');
const OUT = path.join(ROOT, 'previews'); const HTML = path.join(OUT, 'html');
fs.mkdirSync(HTML, { recursive: true });
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const FONT_CSS = {
  display: "font-family:'Archivo';font-weight:400;font-stretch:125%;",
  displayBold: "font-family:'Archivo';font-weight:700;font-stretch:125%;",
  body: "font-family:'Syne';font-weight:400;",
  bodyMedium: "font-family:'Syne';font-weight:500;",
  bodyBold: "font-family:'Syne';font-weight:700;",
};
function nodeHtml(n) {
  const op = n.opacity != null ? `opacity:${n.opacity};` : '';
  const box = `left:${n.x}px;top:${n.y}px;width:${n.w}px;`;
  if (n.t === 'rect') {
    const st = n.stroke ? `border:${n.strokeW || 1}px ${n.dash ? 'dashed' : 'solid'} ${n.stroke};box-sizing:border-box;` : '';
    return `<div class="n" style="${box}height:${n.h}px;background:${n.fill || 'transparent'};border-radius:${n.radius || 0}px;${st}${op}"></div>`;
  }
  if (n.t === 'ellipse') {
    const st = n.stroke ? `border:${n.strokeW || 1}px solid ${n.stroke};box-sizing:border-box;` : '';
    return `<div class="n" style="${box}height:${n.h}px;background:${n.fill || 'transparent'};border-radius:50%;${st}${op}"></div>`;
  }
  if (n.t === 'text') {
    const ls = n.ls ? `letter-spacing:${n.ls / 100}em;` : '';
    const rot = n.rotate ? `height:${n.h}px;white-space:nowrap;transform:rotate(${n.rotate}deg);transform-origin:50% 50%;` : '';
    return `<div class="n t" style="${box}${rot}${FONT_CSS[n.font]}font-size:${n.size}px;line-height:${n.lh}px;${ls}color:${n.fill};text-align:${n.align || 'left'};${op}">${esc(n.text)}</div>`;
  }
  if (n.t === 'svg') return `<div class="n s" style="${box}height:${n.h}px;${op}">${n.svg}</div>`;
  if (n.t === 'image') {
    const file = S.IMAGE_FILES[n.src];
    const src = file ? 'file://' + path.join(ROOT, file) : '';
    if (!src) return `<div class="n" style="${box}height:${n.h}px;background:#EAE6D6;${op}"></div>`;
    return `<div class="n" style="${box}height:${n.h}px;border-radius:${n.radius || 0}px;background:url('${src}') center/cover no-repeat;${op}"></div>`;
  }
  return '';
}
function slideHtml(sl) {
  return `<!doctype html><html><head><meta charset="utf-8"><style>
@font-face{font-family:'Syne';src:url('file://${ROOT}/fonts/Syne[wght].ttf');font-weight:400 800;}
@font-face{font-family:'Archivo';src:url('file://${ROOT}/fonts/Archivo[wdth,wght].ttf');font-weight:100 900;font-stretch:62% 125%;}
html,body{margin:0;padding:0}
#slide{position:relative;width:${S.SLIDE_W}px;height:${S.SLIDE_H}px;overflow:hidden;background:${sl.bg}}
.n{position:absolute;display:block}
.t{white-space:pre-wrap;word-wrap:break-word;-webkit-font-smoothing:antialiased}
.s svg{width:100%;height:100%;display:block}
</style></head><body><div id="slide">${sl.nodes.map(nodeHtml).join('\n')}</div></body></html>`;
}
(async () => {
  const only = process.argv[2]; // optional slide id filter
  const slides = S.buildSlides();
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: S.SLIDE_W, height: S.SLIDE_H }, deviceScaleFactor: 1 });
  for (const sl of slides) {
    if (only && sl.id !== only) continue;
    const htmlPath = path.join(HTML, sl.id + '.html');
    fs.writeFileSync(htmlPath, slideHtml(sl));
    await page.goto('file://' + htmlPath);
    await page.evaluate(() => document.fonts.ready);
    await page.waitForTimeout(120);
    await page.screenshot({ path: path.join(OUT, sl.id + '.png') });
    console.log('rendered', sl.id);
  }
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });

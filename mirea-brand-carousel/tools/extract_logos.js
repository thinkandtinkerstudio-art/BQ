// Extract the MIREA logo artwork from the client's PDF (rendered to SVG by pdftocairo)
// into clean, tightly-cropped SVG files with absolute M/L/C/Z path data only.
// usage: node tools/extract_logos.js <dir-with-mira-pN.svg> <out-dir>
const fs = require('fs');
const path = require('path');
const [,, inDir, outDir] = process.argv;
const BG = 'rgb(88.201904%, 78.987122%, 68.304443%)'; // sand artboard background
const PAGES = {
  'mira-p3.svg': { id: 'mark',       name: 'Symbol (laurel muse)' },
  'mira-p2.svg': { id: 'stacked',    name: 'Primary lockup (stacked)' },
  'mira-p4.svg': { id: 'horizontal', name: 'Horizontal lockup' },
  'mira-p5.svg': { id: 'seal',       name: 'Round seal' },
  'mira-p6.svg': { id: 'badge',      name: 'Oval badge (ESTD 2026)' },
};
function parsePath(d) {
  const tokens = d.match(/[MLCZ]|-?\d*\.?\d+(?:e-?\d+)?/g);
  const cmds = []; let i = 0;
  while (i < tokens.length) {
    const t = tokens[i++];
    if (t === 'M' || t === 'L') cmds.push({ c: t, p: [+tokens[i++], +tokens[i++]] });
    else if (t === 'C') cmds.push({ c: 'C', p: [+tokens[i++], +tokens[i++], +tokens[i++], +tokens[i++], +tokens[i++], +tokens[i++]] });
    else if (t === 'Z') cmds.push({ c: 'Z', p: [] });
    else throw new Error('unexpected token ' + t);
  }
  return cmds;
}
function bbox(cmds, b) {
  let cur = null;
  for (const k of cmds) {
    if (k.c === 'M' || k.c === 'L') { cur = k.p; add(b, cur[0], cur[1]); }
    else if (k.c === 'C') {
      const [x0, y0] = cur; const [x1, y1, x2, y2, x3, y3] = k.p;
      for (let t = 0; t <= 1; t += 1 / 16) {
        const mt = 1 - t;
        const x = mt*mt*mt*x0 + 3*mt*mt*t*x1 + 3*mt*t*t*x2 + t*t*t*x3;
        const y = mt*mt*mt*y0 + 3*mt*mt*t*y1 + 3*mt*t*t*y2 + t*t*t*y3;
        add(b, x, y);
      }
      cur = [x3, y3];
    }
  }
}
function add(b, x, y) { b.x0 = Math.min(b.x0, x); b.y0 = Math.min(b.y0, y); b.x1 = Math.max(b.x1, x); b.y1 = Math.max(b.y1, y); }
function emit(cmds, dx, dy, s) {
  const f = (v) => +(v * s).toFixed(3);
  return cmds.map(k => {
    if (k.c === 'Z') return 'Z';
    const out = [];
    for (let i = 0; i < k.p.length; i += 2) out.push(f(k.p[i] - dx), f(k.p[i + 1] - dy));
    return k.c + out.join(' ');
  }).join(' ');
}
const manifest = {};
for (const [file, meta] of Object.entries(PAGES)) {
  const svg = fs.readFileSync(path.join(inDir, file), 'utf8');
  const paths = [];
  const re = /<path([^>]*)\/>/g; let m;
  while ((m = re.exec(svg))) {
    const attrs = m[1];
    if (/clip-rule/.test(attrs)) continue;
    const fill = (attrs.match(/fill="([^"]*)"/) || [])[1];
    if (!fill || fill === BG || fill === 'none') continue;
    const d = attrs.match(/d="([^"]*)"/)[1];
    const rule = (attrs.match(/fill-rule="([^"]*)"/) || [, 'nonzero'])[1];
    paths.push({ cmds: parsePath(d), rule, fill });
  }
  const b = { x0: Infinity, y0: Infinity, x1: -Infinity, y1: -Infinity };
  for (const p of paths) bbox(p.cmds, b);
  // scale so that the artwork is at 4x the PDF point size (crisper numbers, no tiny decimals)
  const S = 4;
  const w = +((b.x1 - b.x0) * S).toFixed(2), h = +((b.y1 - b.y0) * S).toFixed(2);
  const body = paths.map(p => `  <path fill-rule="${p.rule}" fill="#6A4937" d="${emit(p.cmds, b.x0, b.y0, S)}"/>`).join('\n');
  const out = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}">\n${body}\n</svg>\n`;
  fs.writeFileSync(path.join(outDir, `mirea-${meta.id}.svg`), out);
  manifest[meta.id] = { name: meta.name, width: w, height: h, paths: paths.length, file: `mirea-${meta.id}.svg` };
  console.log(meta.id.padEnd(11), w, 'x', h, paths.length, 'paths', 'fills:', [...new Set(paths.map(p => p.fill))].length);
}
fs.writeFileSync(path.join(outDir, 'logo-manifest.json'), JSON.stringify(manifest, null, 2));

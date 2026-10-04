// ─────────────────────────────────────────────────────────────────────────────
// Scene model + slide builder. Pure data: every slide is a list of primitives
// (rect / ellipse / text / svg / image) in absolute 1305 × 1631 coordinates.
// Both renderers (HTML preview, Figma plugin) consume this list.
// ─────────────────────────────────────────────────────────────────────────────
interface SNodeBase { t: string; name: string; x: number; y: number; w: number; h: number; opacity?: number }
interface SRect extends SNodeBase { t: 'rect'; fill?: string; radius?: number; stroke?: string; strokeW?: number; dash?: number[] }
interface SEllipse extends SNodeBase { t: 'ellipse'; fill?: string; stroke?: string; strokeW?: number }
interface SText extends SNodeBase {
  t: 'text'; text: string; font: FontRole; size: number; lh: number; ls?: number; fill: string;
  align?: 'left' | 'center' | 'right'; rotate?: 0 | -90 | 90;
}
interface SSvg extends SNodeBase { t: 'svg'; svg: string }
interface SImage extends SNodeBase { t: 'image'; src: string; radius?: number; label: string }
type SNode = SRect | SEllipse | SText | SSvg | SImage;
interface Slide { id: string; name: string; bg: string; nodes: SNode[] }

interface BuildOptions {
  studioName: string;      // typographic fallback when no studio logo is supplied
  studioHandle: string;    // optional, e.g. "@studio" — hidden when empty
  studioLogoSvg: string;   // optional SVG string of the studio logo
  studioLogoRatio: number; // width / height of the supplied logo (0 when none)
  studioLogoImageRatio: number; // width / height when the studio logo is a bitmap (0 when none)
  edition: string;         // e.g. "EDITION 01 — 2026"
}
const DEFAULT_OPTIONS: BuildOptions = {
  studioName: 'THINK & TINKER STUDIO',
  studioHandle: '',
  studioLogoSvg: '',
  studioLogoRatio: 0,
  studioLogoImageRatio: 0,
  edition: 'EDITION 01 — 2026',
};

// ── geometry helpers ─────────────────────────────────────────────────────────
const KAPPA = 0.5523;
function f2(v: number): string { return String(Math.round(v * 100) / 100); }
/** Rectangle with concave (notched) corners — the packaging plaque. Local coords 0..w / 0..h. */
function plaquePath(w: number, h: number, r: number): string {
  const k = KAPPA * r;
  return [
    `M${f2(r)} 0`, `L${f2(w - r)} 0`,
    `C${f2(w - r)} ${f2(k)} ${f2(w - k)} ${f2(r)} ${f2(w)} ${f2(r)}`,
    `L${f2(w)} ${f2(h - r)}`,
    `C${f2(w - k)} ${f2(h - r)} ${f2(w - r)} ${f2(h - k)} ${f2(w - r)} ${f2(h)}`,
    `L${f2(r)} ${f2(h)}`,
    `C${f2(r)} ${f2(h - k)} ${f2(k)} ${f2(h - r)} 0 ${f2(h - r)}`,
    `L0 ${f2(r)}`,
    `C${f2(k)} ${f2(r)} ${f2(r)} ${f2(k)} ${f2(r)} 0`, 'Z',
  ].join(' ');
}
/** Four-point sparkle with concave sides, centred in a size × size box. */
function sparklePath(size: number): string {
  const c = size / 2, r = size / 2, p = r * 0.18;
  return `M${f2(c)} 0 C${f2(c)} ${f2(c - p)} ${f2(c + p)} ${f2(c)} ${f2(size)} ${f2(c)} ` +
    `C${f2(c + p)} ${f2(c)} ${f2(c)} ${f2(c + p)} ${f2(c)} ${f2(size)} ` +
    `C${f2(c)} ${f2(c + p)} ${f2(c - p)} ${f2(c)} 0 ${f2(c)} ` +
    `C${f2(c - p)} ${f2(c)} ${f2(c)} ${f2(c - p)} ${f2(c)} 0 Z`;
}
function svgWrap(w: number, h: number, body: string): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${f2(w)}" height="${f2(h)}" viewBox="0 0 ${f2(w)} ${f2(h)}">${body}</svg>`;
}
function logoSvg(id: string, fill: string): string {
  return LOGOS[id].svg.split(LOGO_FILL).join(fill);
}

// ── node factories ───────────────────────────────────────────────────────────
function rect(name: string, x: number, y: number, w: number, h: number, fill?: string, extra?: Partial<SRect>): SRect {
  const n: SRect = { t: 'rect', name, x, y, w, h, fill };
  if (extra) Object.assign(n, extra);
  return n;
}
function text(name: string, x: number, y: number, w: number, s: string, font: FontRole, size: number, lh: number, fill: string, extra?: Partial<SText>): SText {
  const n: SText = { t: 'text', name, x, y, w, h: lh, text: s, font, size, lh, fill, align: 'left' };
  if (extra) Object.assign(n, extra);
  return n;
}
function svgNode(name: string, x: number, y: number, w: number, h: number, svg: string): SSvg {
  return { t: 'svg', name, x, y, w, h, svg };
}
function image(name: string, x: number, y: number, w: number, h: number, src: string, radius?: number): SImage {
  return { t: 'image', name, x, y, w, h, src, radius, label: name };
}
function logo(name: string, id: string, x: number, y: number, h: number, fill: string): SSvg {
  const a = LOGOS[id]; const w = h * a.w / a.h;
  return svgNode(name, x, y, w, h, logoSvg(id, fill));
}
function plaque(name: string, x: number, y: number, w: number, h: number, fill: string, r?: number): SSvg {
  const rr = r == null ? Math.min(28, w * 0.08) : r;
  return svgNode(name, x, y, w, h, svgWrap(w, h, `<path fill="${fill}" d="${plaquePath(w, h, rr)}"/>`));
}
function sparkle(name: string, cx: number, cy: number, size: number, fill: string): SSvg {
  return svgNode(name, cx - size / 2, cy - size / 2, size, size, svgWrap(size, size, `<path fill="${fill}" d="${sparklePath(size)}"/>`));
}
/** hairline — sparkle — hairline divider, centred on (cx, cy) with total width w. */
function divider(name: string, cx: number, cy: number, w: number, lineColor: string, starColor: string, starSize?: number): SNode[] {
  const s = starSize || 22, gap = 18, lw = (w - s) / 2 - gap;
  return [
    rect(name + ' / line L', cx - w / 2, cy - 0.5, lw, 1, lineColor),
    sparkle(name + ' / sparkle', cx, cy, s, starColor),
    rect(name + ' / line R', cx + w / 2 - lw, cy - 0.5, lw, 1, lineColor),
  ];
}
function vertical(name: string, x: number, yTop: number, len: number, s: string, size: number, fill: string, dir: -90 | 90, ls?: number): SText {
  // box before rotation: width = len (along the text), height = size*1.3; rotated around its centre
  const h = Math.round(size * 1.3);
  const cx = x + h / 2, cy = yTop + len / 2;
  return text(name, cx - len / 2, cy - h / 2, len, s, 'display', size, h, fill, { align: 'center', rotate: dir, ls: ls == null ? 22 : ls });
}

// ── recurring furniture ──────────────────────────────────────────────────────
function chrome(index: number, section: string, ink: string, muted: string): SNode[] {
  const nn = (index < 10 ? '0' : '') + index;
  return [
    text('Header / brand', MARGIN, 64, 600, 'MIREA — BRAND GUIDELINES', 'display', 16, 20, ink, { ls: 26 }),
    text('Header / page', SLIDE_W - MARGIN - 300, 64, 300, nn + ' / ' + SLIDE_COUNT, 'display', 16, 20, ink, { ls: 26, align: 'right' }),
    rect('Header / rule', MARGIN, 98, SLIDE_W - 2 * MARGIN, 1, muted),
    rect('Footer / rule', MARGIN, SLIDE_H - 98, SLIDE_W - 2 * MARGIN, 1, muted),
    text('Footer / eyebrow', MARGIN, SLIDE_H - 84, 600, COPY.eyebrow, 'display', 14, 20, muted, { ls: 30 }),
    text('Footer / section', SLIDE_W - MARGIN - 500, SLIDE_H - 84, 500, section, 'display', 14, 20, muted, { ls: 30, align: 'right' }),
  ];
}
function eyebrowTitle(num: string, label: string, title: string, y: number, ink: string, accent: string, titleSize?: number, width?: number): SNode[] {
  const w = width || SLIDE_W - 2 * MARGIN;
  const ts = titleSize || 72;
  return [
    text('Section number', MARGIN, y, 200, num, 'display', 18, 24, accent, { ls: 24 }),
    text('Section label', MARGIN + 70, y, 600, label, 'display', 18, 24, ink, { ls: 24 }),
    text('Title', MARGIN, y + 54, w, title, 'displayBold', ts, Math.round(ts * 1.06), ink, { ls: 2 }),
  ];
}
function studioLogo(o: BuildOptions, x: number, y: number, h: number, fill: string, align: 'left' | 'right' | 'center'): SNode[] {
  if (o.studioLogoSvg) {
    const ratio = o.studioLogoRatio > 0 ? o.studioLogoRatio : 3;
    const w = h * ratio;
    const xx = align === 'right' ? x - w : align === 'center' ? x - w / 2 : x;
    return [svgNode('Studio logo', xx, y, w, h, o.studioLogoSvg.split('currentColor').join(fill))];
  }
  if (o.studioLogoImageRatio > 0) {
    const w = h * o.studioLogoImageRatio;
    const xx = align === 'right' ? x - w : align === 'center' ? x - w / 2 : x;
    return [image('Studio logo', xx, y, w, h, 'studio-logo')];
  }
  // Typographic placeholder — replace with the studio's own logo (plugin UI → "Studio logo").
  const words = o.studioName.trim().split(/\s+/);
  const main = words.length > 1 ? words.slice(0, -1).join(' ') : o.studioName;
  const sub = words.length > 1 ? words[words.length - 1] : '';
  const w = 520;
  const xx = align === 'right' ? x - w : align === 'center' ? x - w / 2 : x;
  const size = Math.round(h * 0.5), lh1 = Math.round(size * 1.1);
  const out: SNode[] = [text('Studio logo — placeholder (replace)', xx, y, w, main, 'displayBold', size, lh1, fill, { ls: 12, align })];
  if (sub) out.push(text('Studio logo — placeholder line 2', xx, y + lh1 + 4, w, sub, 'display', Math.round(size * 0.6), Math.round(size * 0.8), fill, { ls: 34, align }));
  return out;
}

// ── slides ───────────────────────────────────────────────────────────────────
function buildSlides(opt?: Partial<BuildOptions>): Slide[] {
  const o: BuildOptions = Object.assign({}, DEFAULT_OPTIONS, opt || {});
  const C = COLORS;
  const slides: Slide[] = [];
  const CW = SLIDE_W - 2 * MARGIN; // 1125

  // 01 — Cover: the box front, as a poster ────────────────────────────────────
  {
    const n: SNode[] = [];
    n.push(image('Cover painting — clouds', 0, 0, SLIDE_W, SLIDE_H, 'clouds'));
    n.push(rect('Cover tint', 0, 0, SLIDE_W, SLIDE_H, C.sand, { opacity: 0.12 }));
    // vertical manifesto on both sides, like the box
    n.push(vertical('Manifesto L', 118, 300, 1030, COPY.manifesto, 24, C.ivory, -90));
    n.push(vertical('Manifesto R', SLIDE_W - 118 - 32, 300, 1030, COPY.manifesto, 24, C.ivory, 90));
    // plaque
    const pw = 560, ph = 700, px = (SLIDE_W - pw) / 2, py = 470;
    n.push(plaque('Plaque', px, py, pw, ph, C.ivory, 30));
    n.push(text('Plaque / eyebrow', px, py + 78, pw, COPY.eyebrow, 'display', 15, 20, C.cocoa, { ls: 32, align: 'center' }));
    n.push(logo('Plaque / symbol', 'mark', px + pw / 2 - 72, py + 128, 160, C.cocoa));
    n.push(text('Plaque / wordmark', px, py + 318, pw, COPY.brand, 'displayBold', 96, 96, C.espresso, { ls: 6, align: 'center' }));
    n.push(...divider('Plaque / divider', px + pw / 2, py + 462, 150, C.oat, C.rose));
    n.push(text('Plaque / title', px, py + 500, pw, 'BRAND GUIDELINES', 'display', 30, 38, C.cocoa, { ls: 20, align: 'center' }));
    n.push(text('Plaque / descriptor', px, py + 580, pw, COPY.descriptor + '  ·  ' + o.edition, 'display', 15, 20, C.cocoa, { ls: 28, align: 'center' }));
    // top + bottom
    n.push(text('Cover / top label', MARGIN, 64, 600, 'BRAND GUIDELINES  —  ' + o.edition, 'display', 16, 20, C.ivory, { ls: 26 }));
    n.push(text('Cover / page', SLIDE_W - MARGIN - 300, 64, 300, '01 / ' + SLIDE_COUNT, 'display', 16, 20, C.ivory, { ls: 26, align: 'right' }));
    n.push(rect('Cover / bottom band', 0, SLIDE_H - 230, SLIDE_W, 230, C.cocoa));
    n.push(logo('Cover / horizontal lockup', 'horizontal', MARGIN, SLIDE_H - 230 + 70, 90, C.sand));
    n.push(...studioLogo(o, SLIDE_W - MARGIN, SLIDE_H - 230 + 74, 54, C.sand, 'right'));
    n.push(text('Cover / tagline', SLIDE_W - MARGIN - 420, SLIDE_H - 230 + 158, 420, COPY.tagline, 'body', 18, 24, C.sand, { align: 'right' }));
    slides.push({ id: '01-cover', name: '01 Cover', bg: C.sand, nodes: n });
  }

  // 02 — The brand ─────────────────────────────────────────────────────────────
  {
    const n: SNode[] = [...chrome(2, 'THE BRAND', C.cocoa, C.oat)];
    n.push(...eyebrowTitle('01', 'THE BRAND', COPY.headline, 160, C.espresso, C.rose, 72, CW));
    n.push(text('Story', MARGIN, 420, 760, COPY.story, 'body', 26, 40, C.cocoa));
    n.push(logo('Symbol', 'mark', SLIDE_W - MARGIN - 230, 410, 258, C.cocoa));
    // three pillars, as rows
    const rowY = 730, rowH = 150;
    n.push(rect('Pillars / rule top', MARGIN, rowY, CW, 1, C.oat));
    COPY.pillars.forEach((p, i) => {
      const y = rowY + i * rowH;
      n.push(text('Pillar ' + (i + 1) + ' / num', MARGIN, y + 40, 60, '0' + (i + 1), 'display', 15, 20, C.rose, { ls: 26 }));
      n.push(text('Pillar ' + (i + 1) + ' / title', MARGIN + 70, y + 36, 440, p.title, 'displayBold', 32, 38, C.espresso, { ls: 4 }));
      n.push(sparkle('Pillar ' + (i + 1) + ' / sparkle', MARGIN + 492, y + 54, 16, C.rose));
      n.push(text('Pillar ' + (i + 1) + ' / text', MARGIN + 540, y + 40, CW - 540, p.text, 'body', 21, 32, C.cocoa));
      n.push(rect('Pillar ' + (i + 1) + ' / rule', MARGIN, y + rowH, CW, 1, C.oat));
    });
    n.push(plaque('Tagline / plaque', MARGIN, 1250, CW, 190, C.ivory, 26));
    n.push(text('Tagline', MARGIN, 1300, CW, COPY.tagline, 'display', 40, 50, C.cocoa, { ls: 4, align: 'center' }));
    n.push(text('Tagline / note', MARGIN, 1366, CW, 'The tagline closes every story — sentence case, Condor Extended Regular, always with the full stop.', 'body', 17, 26, C.oat, { align: 'center' }));
    slides.push({ id: '02-the-brand', name: '02 The brand', bg: C.sand, nodes: n });
  }

  // 03 — The logo ──────────────────────────────────────────────────────────────
  {
    const n: SNode[] = [...chrome(3, 'THE LOGO', C.cocoa, C.oat)];
    n.push(...eyebrowTitle('02', 'THE LOGO', 'A MUSE, CROWNED IN LAUREL.', 160, C.espresso, C.rose, 72, CW));
    // stage
    const sx = MARGIN, sy = 430, sw = CW, sh = 600;
    n.push(plaque('Stage', sx, sy, sw, sh, C.ivory, 30));
    n.push(logo('Primary lockup', 'stacked', SLIDE_W / 2 - 230, sy + 80, 436, C.cocoa));
    // callouts
    n.push(text('Callout / symbol', sx + 56, sy + 100, 220, 'SYMBOL', 'display', 14, 20, C.rose, { ls: 30 }));
    n.push(rect('Callout / symbol rule', sx + 56, sy + 126, 240, 1, C.oat));
    n.push(text('Callout / wordmark', sx + sw - 56 - 220, sy + 376, 220, 'WORDMARK', 'display', 14, 20, C.rose, { ls: 30, align: 'right' }));
    n.push(rect('Callout / wordmark rule', sx + sw - 56 - 240, sy + 402, 240, 1, C.oat));
    n.push(text('Callout / descriptor', sx + sw - 56 - 220, sy + 470, 220, 'DESCRIPTOR', 'display', 14, 20, C.rose, { ls: 30, align: 'right' }));
    n.push(rect('Callout / descriptor rule', sx + sw - 56 - 240, sy + 496, 240, 1, C.oat));
    // copy, two columns
    const colW = (CW - 60) / 2, ty = 1100;
    n.push(text('Symbol / label', MARGIN, ty, colW, 'THE SYMBOL', 'display', 16, 22, C.rose, { ls: 26 }));
    n.push(text('Symbol / text', MARGIN, ty + 44, colW, COPY.logoSymbol, 'body', 21, 32, C.cocoa));
    n.push(text('Wordmark / label', MARGIN + colW + 60, ty, colW, 'THE WORDMARK', 'display', 16, 22, C.rose, { ls: 26 }));
    n.push(text('Wordmark / text', MARGIN + colW + 60, ty + 44, colW, COPY.logoWordmark, 'body', 21, 32, C.cocoa));
    slides.push({ id: '03-the-logo', name: '03 The logo', bg: C.sand, nodes: n });
  }

  // 04 — Logo system ───────────────────────────────────────────────────────────
  {
    const n: SNode[] = [...chrome(4, 'LOGO SYSTEM', C.cocoa, C.oat)];
    n.push(...eyebrowTitle('03', 'LOGO SYSTEM', 'ONE MUSE, FIVE LOCKUPS.', 160, C.espresso, C.rose, 72, CW));
    const gap = 28;
    const topY = 410, topH = 470, topW = (CW - gap) / 2;
    const botY = topY + topH + gap, botH = 420, botW = (CW - 2 * gap) / 3;
    const tiles: { id: string; x: number; y: number; w: number; h: number; lh: number }[] = [
      { id: 'stacked', x: MARGIN, y: topY, w: topW, h: topH, lh: 260 },
      { id: 'horizontal', x: MARGIN + topW + gap, y: topY, w: topW, h: topH, lh: 150 },
      { id: 'mark', x: MARGIN, y: botY, w: botW, h: botH, lh: 190 },
      { id: 'seal', x: MARGIN + botW + gap, y: botY, w: botW, h: botH, lh: 230 },
      { id: 'badge', x: MARGIN + 2 * (botW + gap), y: botY, w: botW, h: botH, lh: 236 },
    ];
    tiles.forEach((tl) => {
      const v = COPY.variations.filter((x) => x.id === tl.id)[0];
      n.push(plaque('Tile ' + v.num + ' / card', tl.x, tl.y, tl.w, tl.h, C.ivory, 24));
      const a = LOGOS[tl.id]; let lh = tl.lh; let lw = lh * a.w / a.h;
      if (lw > tl.w - 80) { lw = tl.w - 80; lh = lw * a.h / a.w; }
      n.push(logo('Tile ' + v.num + ' / ' + v.title, tl.id, tl.x + (tl.w - lw) / 2, tl.y + 34 + (tl.h - 150 - lh) / 2, lh, C.cocoa));
      n.push(text('Tile ' + v.num + ' / num', tl.x + 32, tl.y + tl.h - 96, 60, v.num, 'display', 14, 20, C.rose, { ls: 26 }));
      n.push(text('Tile ' + v.num + ' / title', tl.x + 32, tl.y + tl.h - 72, tl.w - 64, v.title.toUpperCase(), 'displayBold', 16, 22, C.espresso, { ls: 14 }));
      n.push(text('Tile ' + v.num + ' / text', tl.x + 32, tl.y + tl.h - 46, tl.w - 64, v.text, 'body', 15, 20, C.cocoa));
    });
    n.push(text('Note', MARGIN, 1372, CW, 'Use the primary lockup wherever space allows. The symbol alone needs no descriptor; the seal and badge are reserved for stamps, labels and hang tags.', 'body', 19, 28, C.oat, { align: 'center' }));
    slides.push({ id: '04-logo-system', name: '04 Logo system', bg: C.sand, nodes: n });
  }

  // 05 — Clear space, size, colour ─────────────────────────────────────────────
  {
    const n: SNode[] = [...chrome(5, 'LOGO RULES', C.cocoa, C.oat)];
    n.push(...eyebrowTitle('04', 'LOGO RULES', 'ROOM TO BREATHE.', 160, C.espresso, C.rose, 72, CW));
    // clear-space stage
    const sx = MARGIN, sy = 400, sw = 640, sh = 560;
    n.push(plaque('Clear space / stage', sx, sy, sw, sh, C.ivory, 28));
    const lh = 300, a = LOGOS['stacked'], lw = lh * a.w / a.h, X = 0.145 * lh;
    const lx = sx + (sw - lw) / 2, ly = sy + (sh - lh) / 2;
    n.push(rect('Clear space / zone', lx - X, ly - X, lw + 2 * X, lh + 2 * X, undefined, { stroke: C.rose, strokeW: 1, dash: [8, 6] }));
    n.push(logo('Clear space / lockup', 'stacked', lx, ly, lh, C.cocoa));
    // X markers
    const xm = (xx: number, yy: number, w: number, h: number, nm: string) => {
      n.push(rect(nm, xx, yy, w, h, undefined, { stroke: C.rose, strokeW: 1 }));
      n.push(text(nm + ' / label', xx, yy + h / 2 - 9, w, 'x', 'bodyMedium', 14, 18, C.rose, { align: 'center' }));
    };
    xm(lx - X, ly - X, X, X, 'Clear space / x TL');
    xm(lx + lw, ly + lh, X, X, 'Clear space / x BR');
    n.push(text('Clear space / label', sx + 40, sy + sh - 60, sw - 80, 'x = cap height of the letter M', 'body', 15, 20, C.oat, { align: 'center' }));
    // right column copy
    const rx = MARGIN + sw + 50, rw = CW - sw - 50;
    n.push(text('Clear / label', rx, 410, rw, 'CLEAR SPACE', 'display', 16, 22, C.rose, { ls: 26 }));
    n.push(text('Clear / text', rx, 450, rw, COPY.clearSpace, 'body', 20, 30, C.cocoa));
    n.push(text('Min / label', rx, 620, rw, 'MINIMUM SIZE', 'display', 16, 22, C.rose, { ls: 26 }));
    n.push(text('Min / text', rx, 660, rw, COPY.minSize, 'body', 20, 30, C.cocoa));
    n.push(logo('Min / lockup 110px', 'stacked', rx, 740, 110 * a.h / a.w, C.cocoa));
    n.push(logo('Min / symbol 48px', 'mark', rx + 150, 740, 48 * LOGOS['mark'].h / LOGOS['mark'].w, C.cocoa));
    n.push(text('Min / caption', rx, 862, rw, '110 PX  ·  48 PX', 'display', 12, 18, C.oat, { ls: 24 }));
    n.push(text('Colour / label', MARGIN, 1000, CW, 'COLOUR VERSIONS', 'display', 16, 22, C.rose, { ls: 26 }));
    n.push(text('Colour / text', MARGIN, 1034, CW, COPY.colourVersions, 'body', 17, 25, C.cocoa));
    // four colour tiles
    const gap = 24, tw = (CW - 3 * gap) / 4, ty = 1090, th = 300;
    const combos = [
      { bg: C.sand, fg: C.cocoa, label: 'COCOA ON SAND' },
      { bg: C.cocoa, fg: C.sand, label: 'SAND ON COCOA' },
      { bg: C.rose, fg: C.ivory, label: 'IVORY ON ROSE' },
      { bg: C.blue, fg: C.cocoa, label: 'COCOA ON BLUE' },
    ];
    combos.forEach((cb, i) => {
      const x = MARGIN + i * (tw + gap);
      n.push(rect('Colour tile ' + (i + 1), x, ty, tw, th, cb.bg, { stroke: i === 0 ? C.oat : undefined, strokeW: i === 0 ? 1 : undefined }));
      n.push(logo('Colour tile ' + (i + 1) + ' / lockup', 'stacked', x + (tw - 160 * a.w / a.h) / 2, ty + 48, 160, cb.fg));
      n.push(text('Colour tile ' + (i + 1) + ' / label', x, ty + th - 54, tw, cb.label, 'display', 13, 18, cb.fg, { ls: 24, align: 'center' }));
    });
    slides.push({ id: '05-logo-rules', name: '05 Logo rules', bg: C.sand, nodes: n });
  }

  // 06 — Colour palette ────────────────────────────────────────────────────────
  {
    const n: SNode[] = [...chrome(6, 'COLOUR', C.cocoa, C.oat)];
    n.push(...eyebrowTitle('05', 'COLOUR PALETTE', 'PAINTED, NOT PICKED.', 160, C.espresso, C.rose, 72, CW));
    n.push(text('Palette intro', MARGIN, 404, CW, COPY.paletteIntro, 'body', 21, 32, C.cocoa));
    const gap = 18, sw = (CW - 4 * gap) / 5, sy = 540, sh = 560;
    PALETTE_PRIMARY.forEach((s, i) => {
      const x = MARGIN + i * (sw + gap), hex = COLORS[s.key];
      const light = s.key === 'sand' || s.key === 'blue';
      const fg = light ? C.espresso : C.sand;
      n.push(rect('Swatch ' + s.name, x, sy, sw, sh, hex, { stroke: s.key === 'sand' ? C.oat : undefined, strokeW: s.key === 'sand' ? 1 : undefined }));
      n.push(text('Swatch ' + s.name + ' / num', x + 24, sy + 28, sw - 48, '0' + (i + 1), 'display', 14, 20, fg, { ls: 24 }));
      n.push(text('Swatch ' + s.name + ' / name', x + 24, sy + sh - 214, sw - 48, s.name.toUpperCase(), 'displayBold', 18, 24, fg, { ls: 8 }));
      n.push(rect('Swatch ' + s.name + ' / rule', x + 24, sy + sh - 150, 40, 1, fg));
      const [r, g, b] = hexToRgb255(hex);
      n.push(text('Swatch ' + s.name + ' / hex', x + 24, sy + sh - 132, sw - 48, hex.toUpperCase(), 'bodyBold', 15, 22, fg));
      n.push(text('Swatch ' + s.name + ' / rgb', x + 24, sy + sh - 106, sw - 48, 'RGB ' + r + ' · ' + g + ' · ' + b, 'body', 13, 20, fg));
      n.push(text('Swatch ' + s.name + ' / cmyk', x + 24, sy + sh - 84, sw - 48, 'CMYK ' + hexToCmyk(hex), 'body', 13, 20, fg));
      n.push(text('Swatch ' + s.name + ' / role', x + 24, sy + sh - 54, sw - 48, s.role, 'body', 12, 17, fg, { opacity: 0.85 }));
    });
    // neutrals
    const ny = sy + sh + 44, nh = 190;
    n.push(text('Neutrals / label', MARGIN, ny, CW, 'NEUTRAL TINTS', 'display', 14, 20, C.rose, { ls: 30 }));
    PALETTE_NEUTRAL.forEach((s, i) => {
      const x = MARGIN + i * (sw + gap), hex = COLORS[s.key];
      const fg = (s.key === 'oat' || s.key === 'camel') ? C.ivory : C.cocoa;
      n.push(rect('Tint ' + s.name, x, ny + 34, sw, nh, hex, { stroke: C.oat, strokeW: 1 }));
      n.push(text('Tint ' + s.name + ' / name', x + 20, ny + 34 + nh - 70, sw - 40, s.name.toUpperCase(), 'displayBold', 14, 18, fg, { ls: 12 }));
      n.push(text('Tint ' + s.name + ' / hex', x + 20, ny + 34 + nh - 46, sw - 40, hex.toUpperCase() + '  ·  ' + s.role, 'body', 12, 17, fg));
    });
    n.push(text('Proportion note', MARGIN, 1415, CW, 'Proportion: 60 % Sand & tints  ·  25 % Cocoa  ·  10 % edition colour  ·  5 % Espresso. CMYK values are conversions — match printed colour to the approved proofs.', 'body', 15, 22, C.oat, { align: 'center' }));
    slides.push({ id: '06-colour', name: '06 Colour palette', bg: C.sand, nodes: n });
  }

  // 07 — Typography (dark slide) ───────────────────────────────────────────────
  {
    const ink = C.sand, mutedInk = C.camel;
    const n: SNode[] = [...chrome(7, 'TYPOGRAPHY', ink, mutedInk)];
    n.push(...eyebrowTitle('06', 'TYPOGRAPHY', 'WIDE, CALM, CLASSICAL.', 160, C.ivory, C.rose, 72, CW));
    // primary specimen
    n.push(text('Primary / label', MARGIN, 404, 500, 'PRIMARY TYPEFACE', 'display', 16, 22, C.rose, { ls: 26 }));
    n.push(text('Primary / family', MARGIN, 440, 700, 'Condor Extended', 'displayBold', 54, 62, C.ivory, { ls: 2 }));
    n.push(text('Primary / Aa', SLIDE_W - MARGIN - 420, 380, 420, 'Aa', 'displayBold', 230, 230, C.ivory, { align: 'right', ls: -2 }));
    n.push(text('Primary / alphabet 1', MARGIN, 560, CW - 440, 'ABCDEFGHIJKLM', 'display', 44, 54, ink, { ls: 8 }));
    n.push(text('Primary / alphabet 2', MARGIN, 616, CW - 440, 'NOPQRSTUVWXYZ', 'display', 44, 54, ink, { ls: 8 }));
    n.push(text('Primary / numerals', MARGIN, 672, CW - 440, '0123456789  &  .,:;!?—', 'displayBold', 30, 40, ink, { ls: 10 }));
    n.push(text('Primary / text', MARGIN, 740, 640, COPY.typePrimary, 'body', 18, 27, ink));
    // weights
    n.push(text('Weights / regular', MARGIN, 862, 640, 'REGULAR  —  DESCRIPTORS, MANIFESTO, LABELS', 'display', 13, 20, mutedInk, { ls: 20 }));
    n.push(text('Weights / bold', MARGIN, 888, 640, 'BOLD  —  WORDMARK, HEADLINES', 'displayBold', 13, 20, ink, { ls: 20 }));
    n.push(...divider('Divider', SLIDE_W / 2, 940, CW, mutedInk, C.rose));
    // secondary
    n.push(text('Secondary / label', MARGIN, 985, 500, 'SECONDARY TYPEFACE', 'display', 16, 22, C.rose, { ls: 26 }));
    n.push(text('Secondary / family', MARGIN, 1021, 600, 'Syne', 'bodyBold', 54, 62, C.ivory));
    n.push(text('Secondary / specimen', MARGIN, 1101, 640, 'MIREA captures the moments that shape us — the places, choices and memories we carry with us.', 'body', 22, 32, ink));
    n.push(text('Secondary / text', MARGIN, 1211, 640, COPY.typeSecondary, 'body', 18, 27, mutedInk));
    // scale
    const scaleX = SLIDE_W - MARGIN - 400;
    n.push(text('Scale / label', scaleX, 985, 400, 'HIERARCHY', 'display', 16, 22, C.rose, { ls: 26, align: 'right' }));
    const rows = [
      ['HEADLINE', 'Condor Extended Bold · 84 / 84 · +2 %'],
      ['SUBHEAD', 'Condor Extended Regular · 30 / 38 · +20 %'],
      ['LABEL', 'Condor Extended Regular · 14–16 · +26 %'],
      ['BODY', 'Syne Regular · 20–27 / 1.5'],
      ['CAPTION', 'Syne Regular · 13–15 / 1.4'],
    ];
    rows.forEach((r, i) => {
      const y = 1027 + i * 64;
      n.push(text('Scale / ' + r[0], scaleX, y, 400, r[0], 'displayBold', 14, 20, ink, { ls: 20, align: 'right' }));
      n.push(text('Scale / ' + r[0] + ' spec', scaleX, y + 24, 400, r[1], 'body', 14, 20, mutedInk, { align: 'right' }));
      n.push(rect('Scale / rule ' + i, scaleX, y + 52, 400, 1, C.camel, { opacity: 0.5 }));
    });
    n.push(text('Type note', MARGIN, 1420, CW, 'Headlines and labels are always uppercase and tracked. Body copy is sentence case, never justified, never below 13 px / 7 pt.', 'body', 15, 22, mutedInk, { align: 'center' }));
    slides.push({ id: '07-typography', name: '07 Typography', bg: C.cocoa, nodes: n });
  }

  // 08 — Graphic elements ──────────────────────────────────────────────────────
  {
    const n: SNode[] = [...chrome(8, 'GRAPHIC ELEMENTS', C.cocoa, C.oat)];
    n.push(...eyebrowTitle('07', 'GRAPHIC ELEMENTS', 'SMALL GESTURES, REPEATED.', 160, C.espresso, C.rose, 72, CW));
    const gap = 28, tw = (CW - gap) / 2, th = 430, ty1 = 410, ty2 = ty1 + th + gap;
    const tiles = [
      { x: MARGIN, y: ty1 }, { x: MARGIN + tw + gap, y: ty1 }, { x: MARGIN, y: ty2 }, { x: MARGIN + tw + gap, y: ty2 },
    ];
    COPY.elements.forEach((el, i) => {
      const t = tiles[i];
      n.push(plaque('Element ' + (i + 1) + ' / card', t.x, t.y, tw, th, C.ivory, 26));
      n.push(text('Element ' + (i + 1) + ' / num', t.x + 36, t.y + 36, 80, '0' + (i + 1), 'display', 14, 20, C.rose, { ls: 26 }));
      n.push(text('Element ' + (i + 1) + ' / title', t.x + 36, t.y + th - 118, tw - (i === 1 ? 130 : 72), el.title, 'displayBold', 17, 22, C.espresso, { ls: 14 }));
      n.push(text('Element ' + (i + 1) + ' / text', t.x + 36, t.y + th - 86, tw - (i === 1 ? 130 : 72), el.text, 'body', 15, 22, C.cocoa));
      // demonstrations
      if (i === 0) {
        n.push(...divider('Element 1 / demo', t.x + tw / 2, t.y + 190, 300, C.oat, C.rose, 34));
      } else if (i === 1) {
        n.push(vertical('Element 2 / demo', t.x + tw - 74, t.y + 34, th - 68, COPY.manifesto, 11, C.cocoa, -90));
      } else if (i === 2) {
        const pw = 250, ph = 220, px = t.x + (tw - pw) / 2, py = t.y + 60;
        n.push(rect('Element 3 / demo ground', t.x + 1, t.y + 1, tw - 2, 300, C.blue, { opacity: 0.5 }));
        n.push(plaque('Element 3 / demo plaque', px, py, pw, ph, C.ivory, 18));
        n.push(text('Element 3 / demo eyebrow', px, py + 36, pw, COPY.eyebrow, 'display', 8, 12, C.cocoa, { ls: 30, align: 'center' }));
        n.push(text('Element 3 / demo wordmark', px, py + 62, pw, COPY.brand, 'displayBold', 40, 44, C.espresso, { ls: 4, align: 'center' }));
        n.push(...divider('Element 3 / demo divider', px + pw / 2, py + 126, 80, C.oat, C.rose, 12));
        n.push(text('Element 3 / demo edition', px, py + 142, pw, 'MILANO 01', 'display', 20, 26, C.cocoa, { ls: 10, align: 'center' }));
        n.push(text('Element 3 / demo descriptor', px, py + 186, pw, 'CASA DE PERFUMES · 50 ML', 'display', 8, 12, C.cocoa, { ls: 24, align: 'center' }));
      } else if (i === 3) {
        n.push(text('Element 4 / demo eyebrow', t.x + 36, t.y + 130, tw - 72, COPY.eyebrow, 'display', 15, 20, C.cocoa, { ls: 34, align: 'center' }));
        n.push(text('Element 4 / demo wordmark', t.x + 36, t.y + 166, tw - 72, COPY.brand, 'displayBold', 70, 76, C.espresso, { ls: 6, align: 'center' }));
      }
    });
    n.push(text('Elements note', MARGIN, 1372, CW, 'Elements are set in Cocoa on light grounds and in Sand or Ivory on photography and dark grounds. Sparkles may be Dusty Rose on both.', 'body', 17, 25, C.oat, { align: 'center' }));
    slides.push({ id: '08-graphic-elements', name: '08 Graphic elements', bg: C.sand, nodes: n });
  }

  // 09 — Packaging ─────────────────────────────────────────────────────────────
  {
    const n: SNode[] = [...chrome(9, 'PACKAGING', C.cocoa, C.oat)];
    n.push(...eyebrowTitle('08', 'PACKAGING', 'A PAINTING FOR EVERY EDITION.', 160, C.espresso, C.rose, 72, CW));
    n.push(text('Packaging intro', MARGIN, 404, CW, COPY.packagingIntro, 'body', 19, 28, C.cocoa));
    const gap = 26, tw = (CW - gap) / 2, th = 380, y1 = 520, y2 = y1 + th + 76;
    COPY.packaging.forEach((p, i) => {
      const x = MARGIN + (i % 2) * (tw + gap), y = i < 2 ? y1 : y2;
      n.push(rect('Pack ' + (i + 1) + ' / ground', x, y, tw, th, C.ivory));
      n.push(image('Pack ' + (i + 1) + ' / dieline', x + 14, y + 14, tw - 28, th - 28, p.src));
      n.push(text('Pack ' + (i + 1) + ' / title', x, y + th + 16, tw, p.title, 'displayBold', 14, 20, C.espresso, { ls: 16 }));
      n.push(text('Pack ' + (i + 1) + ' / text', x, y + th + 38, tw, p.text, 'body', 14, 20, C.oat));
    });
    n.push(text('Packaging spec', MARGIN, 1472, CW, COPY.packagingSpec, 'display', 14, 20, C.cocoa, { ls: 30, align: 'center' }));
    slides.push({ id: '09-packaging', name: '09 Packaging', bg: C.sand, nodes: n });
  }

  // 10 — Imagery / art direction ───────────────────────────────────────────────
  {
    const n: SNode[] = [...chrome(10, 'ART DIRECTION', C.cocoa, C.oat)];
    n.push(...eyebrowTitle('09', 'ART DIRECTION', 'SKIES, SILK AND STONE.', 160, C.espresso, C.rose, 72, CW));
    const gap = 22, tw = (CW - gap) / 2, th = 330, y1 = 404, y2 = y1 + th + gap;
    COPY.imagery.forEach((im, i) => {
      const x = MARGIN + (i % 2) * (tw + gap), y = i < 2 ? y1 : y2;
      n.push(image('Image ' + (i + 1) + ' / ' + im.src, x, y, tw, th, im.src));
      n.push(rect('Image ' + (i + 1) + ' / caption ground', x, y + th - 44, tw, 44, C.espresso, { opacity: 0.55 }));
      n.push(text('Image ' + (i + 1) + ' / caption', x + 20, y + th - 32, tw - 40, im.caption.toUpperCase(), 'display', 12, 18, C.ivory, { ls: 24 }));
    });
    n.push(text('Imagery intro', MARGIN, 1130, CW, COPY.imageryIntro, 'body', 21, 32, C.cocoa));
    const px = MARGIN, py = 1300;
    const dos = ['Warm greys, blush, powder blue', 'Soft, diffused light', 'Classical architecture, roses, drapery', 'Figures in profile or turned away'];
    dos.forEach((d, i) => {
      const x = px + (i % 2) * (CW / 2), y = py + Math.floor(i / 2) * 44;
      n.push(sparkle('Do ' + (i + 1) + ' / sparkle', x + 8, y + 12, 14, C.rose));
      n.push(text('Do ' + (i + 1), x + 30, y, CW / 2 - 40, d, 'body', 17, 24, C.cocoa));
    });
    slides.push({ id: '10-art-direction', name: '10 Art direction', bg: C.sand, nodes: n });
  }

  // 11 — Closing (dark) ────────────────────────────────────────────────────────
  {
    const n: SNode[] = [];
    n.push(vertical('Manifesto L', 118, 300, 1030, COPY.manifesto, 22, C.camel, -90));
    n.push(vertical('Manifesto R', SLIDE_W - 118 - 30, 300, 1030, COPY.manifesto, 22, C.camel, 90));
    n.push(text('Header / brand', MARGIN, 64, 600, 'MIREA — BRAND GUIDELINES', 'display', 16, 20, C.sand, { ls: 26 }));
    n.push(text('Header / page', SLIDE_W - MARGIN - 300, 64, 300, SLIDE_COUNT + ' / ' + SLIDE_COUNT, 'display', 16, 20, C.sand, { ls: 26, align: 'right' }));
    n.push(logo('Symbol', 'mark', SLIDE_W / 2 - 120, 330, 268, C.sand));
    n.push(text('Closing', MARGIN + 100, 650, CW - 200, COPY.closing, 'displayBold', 64, 70, C.ivory, { ls: 4, align: 'center' }));
    n.push(...divider('Divider', SLIDE_W / 2, 870, 300, C.camel, C.rose));
    n.push(text('Closing / tagline', MARGIN, 916, CW, COPY.story.split('. ')[0] + '.', 'body', 22, 34, C.sand, { align: 'center' }));
    n.push(text('Credit', MARGIN, 1180, CW, COPY.credit.toUpperCase(), 'display', 14, 20, C.camel, { ls: 30, align: 'center' }));
    n.push(...studioLogo(o, SLIDE_W / 2, 1226, 80, C.sand, 'center'));
    if (o.studioHandle) n.push(text('Studio handle', MARGIN, 1352, CW, o.studioHandle, 'body', 18, 24, C.camel, { align: 'center' }));
    n.push(logo('Horizontal lockup', 'horizontal', SLIDE_W / 2 - 110, SLIDE_H - 150, 80, C.sand));
    slides.push({ id: '11-closing', name: '11 Closing', bg: C.espresso, nodes: n });
  }

  return slides;
}

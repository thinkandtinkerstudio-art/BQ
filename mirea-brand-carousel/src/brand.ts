// ─────────────────────────────────────────────────────────────────────────────
// MIREA — brand tokens, copy and layout constants.
// Shared by the preview renderer (Node + Chromium) and the Figma plugin.
// No imports/exports on purpose: the build concatenates this file.
// ─────────────────────────────────────────────────────────────────────────────
const SLIDE_W = 1305;
const SLIDE_H = 1631;
const MARGIN = 90;
const SLIDE_COUNT = 11;

const COLORS = {
  cocoa: '#7B5A41',
  sand: '#E1C9AE',
  rose: '#B96E64',
  blue: '#B9CAD0',
  espresso: '#342B25',
  ivory: '#F9F8F3',
  linen: '#EAE6D6',
  oat: '#B8A47D',
  camel: '#93744D',
  nude: '#ECD4B8',
  white: '#FFFFFF',
};
type ColorKey = keyof typeof COLORS;

interface Swatch { key: ColorKey; name: string; role: string }
const PALETTE_PRIMARY: Swatch[] = [
  { key: 'cocoa', name: 'Cocoa', role: 'Logo, headlines, base flaps' },
  { key: 'sand', name: 'Sand', role: 'Primary ground, boards, plaques' },
  { key: 'rose', name: 'Dusty Rose', role: 'Floral edition, sparkles, side panels' },
  { key: 'blue', name: 'Powder Blue', role: 'Milano 01 edition, skies' },
  { key: 'espresso', name: 'Espresso', role: 'Body type, dark grounds' },
];
const PALETTE_NEUTRAL: Swatch[] = [
  { key: 'ivory', name: 'Ivory', role: 'Front plaque' },
  { key: 'linen', name: 'Linen', role: 'Panels, cards' },
  { key: 'nude', name: 'Nude', role: 'Soft ground' },
  { key: 'oat', name: 'Oat', role: 'Rules, captions' },
  { key: 'camel', name: 'Camel', role: 'Secondary brown' },
];

type FontRole = 'display' | 'displayBold' | 'body' | 'bodyMedium' | 'bodyBold'; // display = Condor Extended, body = Syne

const COPY = {
  brand: 'MIREA',
  descriptor: 'EAU DE PARFUM',
  eyebrow: 'MEMORIES IN THE MAKING',
  manifesto: 'MOMENTS. OPPORTUNITIES. CHOICES.',
  tagline: 'Memories in the making.',
  headline: 'EVERY MOMENT LEAVES A TRACE.',
  story: 'MIREA captures the moments that shape us — the places, choices and memories we carry with us. Every fragrance is a memory in the making: a city at dusk, a garden in bloom, a feeling you can return to with a single breath.',
  pillars: [
    { title: 'MOMENTS.', text: 'The scenes we live — a balcony in Milano, a garden at golden hour.' },
    { title: 'OPPORTUNITIES.', text: 'The doors that open when we dare to step through them.' },
    { title: 'CHOICES.', text: 'The paths we take, and the trace they leave behind.' },
  ],
  logoSymbol: 'A laurel-crowned muse in profile, drawn from the classical paintings that dress every MIREA box. The laurel speaks of memory and honour; her gaze turns forward, towards the next moment.',
  logoWordmark: 'MIREA is set in Condor Extended Bold — wide, calm and architectural — with the descriptor EAU DE PARFUM tracked beneath it. Symbol and wordmark are always reproduced from the master artwork, never retyped.',
  variations: [
    { id: 'stacked', num: '01', title: 'Primary lockup', text: 'Default on packaging, print and the front plaque.' },
    { id: 'horizontal', num: '02', title: 'Horizontal lockup', text: 'Headers, website, narrow bands and lids.' },
    { id: 'mark', num: '03', title: 'Symbol', text: 'Social avatars, seals, small sizes.' },
    { id: 'seal', num: '04', title: 'Round seal', text: 'Stamps, stickers, wax seals.' },
    { id: 'badge', num: '05', title: 'Oval badge', text: 'Labels, hang tags — ESTD 2026.' },
  ],
  clearSpace: 'Keep a margin equal to the height of the letter M around every lockup. Nothing enters this space — no type, no edges, no imagery.',
  minSize: 'Primary lockup 24 mm / 110 px wide. Symbol alone 10 mm / 48 px.',
  colourVersions: 'Four approved combinations. Never recolour the symbol outside the palette, never add effects or outlines.',
  paletteIntro: 'A palette lifted from the paintings. Cocoa and Sand carry the brand; Dusty Rose and Powder Blue name the editions; Espresso is for type on light grounds. The neutral tints build panels and plaques.',
  typePrimary: 'Wide, geometric and quietly classical. Condor Extended sets the wordmark, every headline, the vertical manifesto and all tracked uppercase labels. Bold for titles, Regular for descriptors. Letter-spacing +10 to +25 % in uppercase.',
  typeSecondary: 'A contemporary grotesque for body copy, product information and legal text. Regular for paragraphs, Bold for emphasis — the word MIREA is always bold inside running text.',
  elements: [
    { title: 'THE SPARKLE', text: 'A four-point star between two hairlines. It divides, it never decorates: one per panel.' },
    { title: 'THE MANIFESTO', text: 'MOMENTS. OPPORTUNITIES. CHOICES. runs vertically along the edges — Condor Extended Regular, +20 % tracking.' },
    { title: 'THE PLAQUE', text: 'An ivory label with notched corners carries eyebrow, wordmark, sparkle and edition name on every front panel.' },
    { title: 'THE EYEBROW', text: 'MEMORIES IN THE MAKING sits above the wordmark in small, widely tracked capitals.' },
  ],
  packagingIntro: 'Each edition pairs a painting with a colour from the palette. The front plaque carries the eyebrow, wordmark, sparkle and edition name; the side panel carries the manifesto and the story; the base is a solid field of the edition colour.',
  packaging: [
    { src: 'pack-milano-sand', title: 'MILANO 01 — SAND', text: 'Moment of new opportunities' },
    { src: 'pack-floral-rose', title: 'FLORAL — DUSTY ROSE', text: 'Moment of soft bloom' },
    { src: 'pack-milano-blue', title: 'MILANO 01 — POWDER BLUE', text: 'Clouds edition' },
    { src: 'pack-floral-muse', title: 'FLORAL — THE MUSE', text: 'Dusty rose side panel' },
  ],
  packagingSpec: '50 ML · 1.7 FL.OZ · MADE IN EGYPT',
  imageryIntro: 'Rococo skies, balustrades and draped silk, painted in warm greys, blush and powder blue. Light is soft and diffused; nothing is saturated. Crop generously and let the sky breathe behind the plaque. Figures appear in profile or turned away — the muse, never a portrait.',
  imagery: [
    { src: 'balustrade', caption: 'The balustrade — Milano 01' },
    { src: 'arches', caption: 'The arches — Floral, cocoa' },
    { src: 'muse', caption: 'The muse — Floral, rose' },
    { src: 'clouds', caption: 'The clouds — Milano 01, blue' },
  ],
  closing: 'MEMORIES IN THE MAKING.',
  credit: 'Brand identity & packaging design by',
};

// Image sources: file names inside assets/ (fetched by the plugin UI, or placeholders).
const IMAGE_FILES: { [key: string]: string } = {
  balustrade: 'assets/images/balustrade.jpg',
  arches: 'assets/images/arches.jpg',
  muse: 'assets/images/muse.jpg',
  clouds: 'assets/images/clouds.jpg',
  'pack-milano-sand': 'assets/packaging/milano-01-sand.jpg',
  'pack-floral-rose': 'assets/packaging/floral-rose-balustrade.jpg',
  'pack-milano-blue': 'assets/packaging/milano-01-blue.jpg',
  'pack-floral-muse': 'assets/packaging/floral-rose-muse.jpg',
};

function hexToRgb255(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}
function hexToCmyk(hex: string): string {
  const [r, g, b] = hexToRgb255(hex).map((v) => v / 255);
  const k = 1 - Math.max(r, g, b);
  if (k >= 0.999) return '0 · 0 · 0 · 100';
  const c = (1 - r - k) / (1 - k), m = (1 - g - k) / (1 - k), y = (1 - b - k) / (1 - k);
  return [c, m, y, k].map((v) => Math.round(v * 100)).join(' · ');
}

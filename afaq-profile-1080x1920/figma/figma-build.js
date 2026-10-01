// AFAQ Corporate Profile — native Figma builder (Figma Plugin API).
//
// Builds every slide of spec/deck-spec.json as a 1080x1920 frame with native layers:
// rectangles/ellipses, vector paths (via the SVG importer, so geometry is exact), and real
// paragraph TEXT nodes (fixed width, auto height, Inter 300/400/500/600).
//
// Where it runs:
//   • Figma MCP `use_figma`  — paste the body of buildDeck plus one slide's spec (see figma/slides/*.js,
//                              each file is a self-contained script under the 50k-char tool limit).
//   • Scripter plugin        — paste this whole file, then `await buildDeck(SPEC)` with SPEC = the JSON.
//   • Any plugin main thread — import and call buildDeck(spec, { x: 0, y: 0 }).
//
// No masks are used: photo placeholders are single shapes named "…__set-image-fill" — select one,
// Fill → Image, done. Delete the "Placeholder-Art" group once a photo is in.

const STYLE = { 300: "Light", 400: "Regular", 500: "Medium", 600: "Semi Bold", 700: "Bold" };

function hex(h) {
  return { r: parseInt(h.slice(1, 3), 16) / 255, g: parseInt(h.slice(3, 5), 16) / 255, b: parseInt(h.slice(5, 7), 16) / 255 };
}
function solid(h, opacity = 1) {
  return { type: "SOLID", color: hex(h), opacity };
}
// Linear gradient given in page coordinates → Figma paint relative to the node's box (bx, by, bw, bh).
function gradientPaint(fill, bx, by, bw, bh) {
  const u1 = (fill.x1 - bx) / bw, v1 = (fill.y1 - by) / bh, u2 = (fill.x2 - bx) / bw, v2 = (fill.y2 - by) / bh;
  const dx = u2 - u1, dy = v2 - v1, det = dx * dx + dy * dy || 1;
  const a = dx / det, b = dy / det, c = -dy / det, d = dx / det;
  return {
    type: "GRADIENT_LINEAR",
    gradientTransform: [[a, b, -(a * u1 + b * v1)], [c, d, -(c * u1 + d * v1)]],
    gradientStops: fill.stops.map(([position, color, alpha]) => ({ position, color: { ...hex(color), a: alpha } })),
  };
}
function paintFor(fill, bx, by, bw, bh) {
  return typeof fill === "string" ? solid(fill) : gradientPaint(fill, bx, by, bw, bh);
}
function pathBounds(d, pad) {
  const nums = d.replace(/[MLCZ]/g, " ").trim().split(/\s+/).map(Number);
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (let i = 0; i < nums.length; i += 2) {
    x0 = Math.min(x0, nums[i]); x1 = Math.max(x1, nums[i]);
    y0 = Math.min(y0, nums[i + 1]); y1 = Math.max(y1, nums[i + 1]);
  }
  return [x0 - pad, y0 - pad, x1 + pad, y1 + pad];
}

async function buildDeck(SPEC, opts = {}) {
  const page = figma.currentPage;
  await Promise.all(Object.values(STYLE).map((style) => figma.loadFontAsync({ family: "Inter", style })));

  // place to the right of whatever is already on the page
  let startX = opts.x;
  if (startX === undefined) {
    startX = 0;
    for (const c of page.children) startX = Math.max(startX, c.x + c.width + 160);
  }
  const startY = opts.y ?? 0;
  const created = [];

  function addRect(e, parent) {
    const n = figma.createRectangle();
    n.name = e.name;
    n.resize(Math.max(e.w, 0.01), Math.max(e.h, 0.01));
    n.x = e.x; n.y = e.y;
    n.cornerRadius = e.rx || 0;
    n.fills = [paintFor(e.fill, e.x, e.y, e.w, e.h)];
    if (e.stroke) { n.strokes = [solid(e.stroke)]; n.strokeWeight = e.sw || 1; n.strokeAlign = "INSIDE"; }
    n.opacity = e.opacity ?? 1;
    parent.appendChild(n);
    return n;
  }
  function addCircle(e, parent) {
    const n = figma.createEllipse();
    n.name = e.name;
    n.resize(2 * e.r, 2 * e.r);
    n.x = e.cx - e.r; n.y = e.cy - e.r;
    n.fills = [paintFor(e.fill, e.cx - e.r, e.cy - e.r, 2 * e.r, 2 * e.r)];
    if (e.stroke) { n.strokes = [solid(e.stroke)]; n.strokeWeight = e.sw || 1; }
    n.opacity = e.opacity ?? 1;
    parent.appendChild(n);
    return n;
  }
  function addPath(e, parent) {
    const pad = (e.sw || 0) / 2 + 1;
    const [x0, y0, x1, y1] = pathBounds(e.d, pad);
    const w = x1 - x0, h = y1 - y0;
    const hasGradient = e.fill && typeof e.fill !== "string";
    const fillAttr = e.fill ? (hasGradient ? "#000000" : e.fill) : "none";
    const strokeAttr = e.stroke
      ? ` stroke="${e.stroke}" stroke-width="${e.sw}" stroke-linecap="${e.cap || "round"}" stroke-linejoin="${e.join || "round"}"`
      : "";
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="${x0} ${y0} ${w} ${h}"><path d="${e.d}" fill="${fillAttr}"${strokeAttr}/></svg>`;
    const holder = figma.createNodeFromSvg(svg);
    const kids = [...holder.children];
    let node;
    if (kids.length === 1) {
      node = kids[0];
      parent.appendChild(node);
      node.x = x0 + node.x; node.y = y0 + node.y;
      holder.remove();
    } else {
      // (rare) importer produced several children — flatten them into one vector so fills apply to the geometry
      node = figma.flatten(kids, parent);
      node.x = x0 + node.x; node.y = y0 + node.y;
      holder.remove();
    }
    node.name = e.name;
    if (hasGradient && "fills" in node) node.fills = [gradientPaint(e.fill, node.x, node.y, node.width, node.height)];
    node.opacity = e.opacity ?? 1;
    return node;
  }
  function addText(e, parent) {
    const t = figma.createText();
    t.name = e.name;
    t.fontName = { family: "Inter", style: STYLE[e.weight] || "Regular" };
    t.characters = e.text;
    t.fontSize = e.size;
    t.lineHeight = { unit: "PIXELS", value: e.lh };
    t.letterSpacing = { unit: "PERCENT", value: (e.ls || 0) * 100 };
    t.textAlignHorizontal = { left: "LEFT", right: "RIGHT", center: "CENTER" }[e.align || "left"];
    if (e.case === "upper") t.textCase = "UPPER";
    t.fills = [solid(e.color)];
    t.opacity = e.opacity ?? 1;
    t.resize(e.w + 4, Math.max(e.h, e.lh)); // +4: same wrap slack the SVG generator uses, so line breaks match
    t.textAutoResize = "HEIGHT";
    // Figma adds letter-spacing after the last glyph too; shift right-aligned tracked labels so glyphs end on the margin
    t.x = e.x + ((e.align === "right") ? (e.ls || 0) * e.size : 0);
    t.y = e.y;
    parent.appendChild(t);
    return t;
  }
  function addElement(e, parent) {
    switch (e.type) {
      case "group": {
        const nodes = e.children.map((c) => addElement(c, parent)).filter(Boolean);
        if (!nodes.length) return null;
        const g = figma.group(nodes, parent);
        g.name = e.name;
        return g;
      }
      case "rect": return addRect(e, parent);
      case "circle": return addCircle(e, parent);
      case "path": return addPath(e, parent);
      case "text": return addText(e, parent);
      default: return null;
    }
  }

  SPEC.slides.forEach((slide, i) => {
    const f = figma.createFrame();
    f.name = slide.name;
    f.resize(SPEC.canvas.width, SPEC.canvas.height);
    f.x = startX + i * (SPEC.canvas.width + 120);
    f.y = startY;
    f.fills = [solid(slide.bg)];
    f.clipsContent = true;
    page.appendChild(f);
    for (const e of slide.elements) {
      if (e.type === "rect" && e.name === "Background") continue; // frame fill already is the background
      addElement(e, f);
    }
    created.push({ id: f.id, name: f.name });
  });
  return { createdNodeIds: created.map((c) => c.id), frames: created };
}

// eslint-disable-next-line no-undef
if (typeof module !== "undefined") module.exports = { buildDeck };

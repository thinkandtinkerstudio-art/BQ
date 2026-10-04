// Node entry: expose the scene builder to the preview tooling.
declare const module: { exports: unknown };
module.exports = { SLIDE_W, SLIDE_H, MARGIN, COLORS, COPY, IMAGE_FILES, LOGOS, LOGO_FILL, buildSlides, DEFAULT_OPTIONS, hexToRgb255, hexToCmyk, plaquePath, sparklePath };

// Screenshot helper: node tools/shot.js <html-file> <out.png> [width] [height]
const { chromium } = require('playwright');
const path = require('path');
(async () => {
  const [,, html, out, w = '1305', h = '1631'] = process.argv;
  const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: +w, height: +h }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.resolve(html));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(150);
  await page.screenshot({ path: out, fullPage: false });
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });

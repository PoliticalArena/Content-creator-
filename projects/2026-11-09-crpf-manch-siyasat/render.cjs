// Usage: [FROM=i TO=j] node render.cjs <mode: preview|overlay> <outDir> [fps=30] [dur=42] [onlyTimes=comma list]
(async () => {
const { chromium } = require('playwright');
const { mkdirSync } = require('fs');
const { pathToFileURL } = require('url');
const path = require('path');
const [mode='preview', out='frames', fps=30, dur=42, only] = process.argv.slice(2);
mkdirSync(out, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
const url = pathToFileURL(path.resolve(__dirname, 'template/index.html')).href + '?mode=' + mode;
await page.goto(url); await page.evaluate(() => document.fonts.ready);
const times = only ? only.split(',').map(Number) : Array.from({ length: Math.round(dur * fps) }, (_, i) => i / fps);
const FROM = +(process.env.FROM || 0), TO = +(process.env.TO || times.length);
for (let i = FROM; i < Math.min(TO, times.length); i++) {
  await page.evaluate(t => window.seek(t), times[i]);
  const name = only ? `t${times[i]}.png` : String(i).padStart(5, '0') + '.png';
  await page.screenshot({ path: path.join(out, name), omitBackground: mode === 'overlay' });
}
await browser.close();
})();

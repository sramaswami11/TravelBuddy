import { execSync } from 'child_process';
import { existsSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Install puppeteer if needed
if (!existsSync(resolve(__dirname, 'node_modules/puppeteer'))) {
  console.log('Installing puppeteer...');
  execSync('npm install puppeteer --no-save', { stdio: 'inherit', cwd: __dirname });
}

const { default: puppeteer } = await import(resolve(__dirname, 'node_modules/puppeteer/lib/esm/puppeteer/puppeteer.js'))
  .catch(() => import(resolve(__dirname, 'node_modules/puppeteer')));

const htmlPath = resolve(__dirname, 'og-image-source.html');
const outputPath = resolve(__dirname, 'public/og-image.png');

const browser = await puppeteer.launch();
const page = await browser.newPage();
await page.setViewport({ width: 1200, height: 630, deviceScaleFactor: 1 });
await page.goto(`file:///${htmlPath.replace(/\\/g, '/')}`);
await page.screenshot({ path: outputPath, clip: { x: 0, y: 0, width: 1200, height: 630 } });
await browser.close();

console.log(`OG image saved to ${outputPath}`);

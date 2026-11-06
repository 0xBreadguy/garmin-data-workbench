// Exact chart-kit exports, using the explorer's React stand-in; never a native-app test.
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import assert from 'node:assert/strict';
const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.dirname(here);
const requireDev = createRequire(path.join(here, 'grok_harness/package.json'));
const esbuild = requireDev('esbuild');
const playwright = requireDev('playwright');
assert.equal(process.argv.length, 4, 'Usage: --output-dir /absolute/new/dir');
assert.equal(process.argv[2], '--output-dir');
assert(path.isAbsolute(process.argv[3]));
const output = process.argv[3];
await fs.mkdir(output, { mode: 0o700 });
const shimSource = await fs.readFile(path.join(here, 'test_grok_widget.mjs'), 'utf8');
const shim = /const shim = `([\s\S]*?)`;/u.exec(shimSource)[1];
const dev = path.join(here, 'grok_harness/node_modules');
const run = (args) => execFileSync('uv', ['run', '--quiet', '--locked', 'garmin-archive', ...args], { cwd: repo, encoding: 'utf8' });
const sources = {};
for (const host of ['grok', 'muse']) {
  const receipt = JSON.parse(run(['chart-kit', '--host', host, '--output', path.join(output, host)]));
  const file = receipt.paths[host === 'grok' ? 'starter.canvas.tsx' : 'starter.html'];
  sources[host] = await fs.readFile(file, 'utf8');
}
const tsconfig = { compilerOptions: { strict: true, noEmit: true, jsx: 'react-jsx', target: 'ES2022', module: 'ESNext', moduleResolution: 'node',
  typeRoots: [path.join(dev, '@types')], paths: { 'react/jsx-runtime': [path.join(dev, '@types/react/jsx-runtime.d.ts')] } },
  files: [path.join(output, 'grok/starter.canvas.tsx'), path.join(here, 'grok_harness/canvas.d.ts')] };
await fs.writeFile(path.join(output, 'tsconfig.json'), JSON.stringify(tsconfig));
execFileSync(process.execPath, [path.join(dev, 'typescript/bin/tsc'), '-p', path.join(output, 'tsconfig.json')], { stdio: 'inherit' });
const surfaces = { light: '#ffffff', dark: '#1f1f1f' };
async function html(host, source, theme) {
  if (host === 'grok') {
    const entry = `import {createRoot} from 'react-dom/client';\n${source.replace('export default function App()', 'function App()')}\ncreateRoot(document.getElementById('root')).render(<App/>);`;
    const built = await esbuild.build({ stdin: { contents: entry, loader: 'tsx', resolveDir: here }, bundle: true, write: false, format: 'iife',
      platform: 'browser', target: 'es2022', jsx: 'automatic', nodePaths: [dev], define: { 'process.env.NODE_ENV': '"production"' },
      plugins: [{ name: 'existing-grok-stand-in', setup(build) {
        build.onResolve({ filter: /^grok\/canvas$/ }, () => ({ path: 'canvas', namespace: 'shim' }));
        build.onLoad({ filter: /.*/, namespace: 'shim' }, () => ({ contents: shim, loader: 'tsx', resolveDir: here }));
      } }] });
    source = `<div id="root"></div><script>window.__HARNESS_THEME__=${JSON.stringify(theme)};window.__HARNESS_SURFACE__=${JSON.stringify(surfaces[theme])};</script><script>${built.outputFiles[0].text.replace(/<\/script/gi, '<\\/script')}</script>`;
  }
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;background:${surfaces[theme]}}:root{--hatch-widget-bg:${surfaces[theme]};--hatch-widget-text:${theme === 'dark' ? '#edf2fa' : '#0b2855'};--hatch-widget-muted:${theme === 'dark' ? '#a4adbc' : '#5b6980'}}</style></head><body>${source}</body></html>`;
}
// Only these supplementary variants change configuration: single date, no values, long range.
function variant(source, host, length, empty = false, count = 2) {
  const dates = Array.from({ length }, (_, i) => new Date(Date.UTC(2030, 0, i + 1)).toISOString().slice(0, 10));
  const values = Array.from({ length }, (_, i) => empty || i === 2 || i === 4 ? null : (i % 9) * 1500);
  const lanes = Array.from({ length: count }, (_, n) => n % 2 ? 'line' : 'bar').map((mark) => ({ label: 'Example ' + mark, unit: 'units', mark, values,
    statuses: values.map((v) => v === null ? 'not_checked' : 'ok'), coverage: `${values.filter((v) => v !== null).length}/${length}` }));
  const config = `const title = "Configuration check";\nconst provenance = "SAMPLE DATA, REPLACE";\nconst freshness = "Invented";\nconst dates = ${JSON.stringify(dates)};\nconst lanes${host === 'grok' ? ': Lane[]' : ''} = ${JSON.stringify(lanes)};\n`;
  return source.replace(/\/\/ CONFIGURATION[\s\S]*?(?=\/\/ END CONFIGURATION)/, config);
}
// Readable durations, hour ticks and a constant zero lane that stays non-negative.
function hours(source, host) {
  const statuses = '["ok", "ok", "ok"]';
  const config = `const title = "Configuration check";\nconst provenance = "SAMPLE DATA, REPLACE";\nconst freshness = "Invented";\nconst dates = ["2030-01-01", "2030-01-02", "2030-01-03"];\nconst lanes${host === 'grok' ? ': Lane[]' : ''} = [{ label: "Sleep", unit: "hours", mark: "line", format: duration, step: 3600, values: [27720, 25200, 18000], statuses: ${statuses}, coverage: "3/3" }, { label: "Flat", unit: "units", mark: "line", values: [0, 0, 0], statuses: ${statuses}, coverage: "3/3" }];\n`;
  return source.replace(/\/\/ CONFIGURATION[\s\S]*?(?=\/\/ END CONFIGURATION)/, config);
}
const results = [];
async function check(label, fn) {
  try { await fn(); results.push({ label, passed: true }); }
  catch (error) { results.push({ label, passed: false, error: error.stack }); }
}
for (const host of ['grok', 'muse']) for (const theme of ['light', 'dark']) {
  for (const [name, source] of Object.entries({ sample: sources[host], quarter: variant(sources[host], host, 90), one: variant(sources[host], host, 1), empty: variant(sources[host], host, 7, true), eight: variant(sources[host], host, 7, false, 8), hours: hours(sources[host], host) })) {
    await fs.writeFile(path.join(output, `${host}-${theme}-${name}.html`), await html(host, source, theme));
  }
}
for (const engine of ['chromium', 'webkit']) {
  const browser = await playwright[engine].launch({ headless: true });
  try {
    for (const host of ['grok', 'muse']) for (const width of [320, 390, 728]) for (const theme of ['light', 'dark']) {
      const label = `${host}-${engine}-${width}-${theme}`;
      const context = await browser.newContext({ viewport: { width, height: 900 }, hasTouch: true, colorScheme: host === 'muse' ? (theme === 'dark' ? 'light' : 'dark') : theme, reducedMotion: 'reduce' });
      const page = await context.newPage();
      page.setDefaultTimeout(5000);
      const errors = [], network = [];
      page.on('pageerror', (e) => errors.push(e.message));
      page.on('request', (r) => { if (!r.url().startsWith('file:')) network.push(r.url()); });
      await page.route(/^https?:/, (route) => route.abort());
      const open = async (name) => {
        await page.goto(pathToFileURL(path.join(output, `${host}-${theme}-${name}.html`)).href);
        await page.locator('[data-chart]').waitFor();
      };
      const linked = async (date, values) => {
        await page.waitForFunction((d) => [...document.querySelectorAll('[data-lane]')].every((e) => e.dataset.date === d), date);
        assert.equal(await page.locator('[data-selected-date]').getAttribute('data-selected-date'), date);
        for (let i = 0; i < values.length; i++) assert.equal(await page.locator(`[data-readout="${i}"]`).textContent(), values[i]);
      };
      await open('sample');
      await check(label + ': initial and provenance', async () => {
        await linked('2030-01-07', ['6', '4']);
        assert.equal(await page.locator('[data-badge]').textContent(), 'SAMPLE DATA, REPLACE');
      });
      const box = await page.locator('[data-lane="0"] [data-plot]').boundingBox();
      const point = (i) => ({ x: box.x + box.width * i / 6, y: box.y + 40 });
      await check(label + ': hover preview and restore', async () => {
        await page.mouse.move(point(1).x, point(1).y);
        await linked('2030-01-02', ['0', '3']);
        assert.equal(await page.locator('[data-chart]').getAttribute('data-committed'), '2030-01-07');
        await page.mouse.move(0, 0);
        await linked('2030-01-07', ['6', '4']);
      });
      await check(label + ': arrow keys', async () => {
        await page.locator('input').focus();
        await page.keyboard.press('ArrowLeft');
        await linked('2030-01-06', ['5', 'N/A']);
      });
      await check(label + ': drag and touch select without text', async () => {
        await page.mouse.move(point(0).x, point(0).y);
        await page.mouse.down();
        await page.mouse.move(point(6).x, point(6).y, { steps: 12 });
        await page.mouse.up();
        await page.mouse.move(0, 0);
        await linked('2030-01-07', ['6', '4']);
        assert.equal(await page.evaluate(() => String(getSelection())), '');
        await page.touchscreen.tap(point(3).x, point(3).y);
        await linked('2030-01-04', ['8', '6']);
      });
      await check(label + ': independent gaps and unsmoothed lines', async () => {
        assert.deepEqual(await page.locator('[data-run]').evaluateAll((els) => els.map((e) => e.getAttribute('data-run'))), ['0,1']);
        assert.equal(await page.locator('[data-lone="true"]').count(), 2);
        assert.equal(await page.locator('[data-lane="0"] [data-gap]').count(), 2);
        assert.equal(await page.locator('[data-lane="1"] [data-gap]').count(), 3);
        assert.equal(await page.locator('[data-gap-key] > span').count(), 5);
        for (const dot of await page.locator('[data-lone="true"]').all()) assert((await dot.boundingBox()).height >= 5);
      });
      await check(label + ': zero, edge insets, axis and slider alignment', async () => {
        assert((await page.locator('[data-value="0"]').boundingBox()).height >= 2);
        const outer = await page.locator('[data-lane="0"]').boundingBox();
        for (const i of [0, 6]) {
          const mark = await page.locator(`[data-lane="0"] [data-mark][data-index="${i}"]`).boundingBox();
          assert(mark.x >= outer.x && mark.x + mark.width <= outer.x + outer.width);
        }
        assert(await page.locator('[data-date-label]').count() <= 5);
        const track = await page.locator('[data-track]').boundingBox();
        const thumb = await page.locator('[data-thumb]').boundingBox();
        assert(Math.abs(track.x - box.x) < 1 && Math.abs(track.width - box.width) < 1);
        assert(Math.abs(thumb.x + thumb.width / 2 - point(3).x) < 1);
        assert(track.y < box.y);
        assert(await page.locator('input').getAttribute('aria-valuetext'));
        assert.equal(await page.locator('[data-lane="0"]').evaluate((e) => getComputedStyle(e).touchAction), 'pan-y');
      });
      await check(label + ': surface, overflow and signature', async () => {
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        assert.equal(await page.locator('[data-logo],.logo').evaluate((e) => e.getBoundingClientRect().height), 22);
        assert.equal(await page.locator('[data-value="0"]').evaluate((e) => getComputedStyle(e).backgroundColor), theme === 'dark' ? 'rgb(92, 157, 255)' : 'rgb(8, 99, 232)');
        if (host === 'grok' && theme === 'dark') {
          assert.equal(await page.locator('[data-chart]').evaluate((e) => e.style.background), 'rgb(31, 31, 31)');
          assert.deepEqual(await page.locator('[data-chart] *').evaluateAll((els) => els.flatMap((e) => {
            const css = getComputedStyle(e);
            return ['backgroundColor', 'borderTopColor', 'borderRightColor', 'borderBottomColor', 'borderLeftColor'].filter((key) => {
              const c = css[key].match(/[\d.]+/g)?.map(Number);
              return c && (c[3] ?? 1) > 0 && c.slice(0, 3).every((v) => v > 200) && (key === 'backgroundColor' || parseFloat(css[key.replace('Color', 'Width')]) > 0);
            });
          })), []);
        }
      });
      if ([390, 728].includes(width)) await page.screenshot({ path: path.join(output, `${label}.png`), fullPage: true });
      for (const name of ['quarter', 'one', 'empty', 'eight', 'hours']) await check(label + ': ' + name, async () => {
        await open(name);
        assert(await page.locator('[data-date-label]').count() <= 5);
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth));
        if (name === 'quarter') {
          assert.equal(await page.locator('[data-mark="dot"]').count(), 1);
          assert.equal(await page.locator('[data-lone="true"]').count(), 1);
          assert.equal(await page.locator('[data-gap-key] > span').count(), 1);
          const ticks = await page.locator('[data-tick]').evaluateAll((nodes) => nodes.map((n) => n.getBoundingClientRect().height));
          assert(ticks.length > 0 && ticks.every((h) => h < 24), 'Axis labels stay on one line');
        }
        if (name === 'one') assert.equal(await page.locator('[data-date-label]').count(), 1);
        if (name === 'empty') assert.equal(await page.locator('[data-mark]').count(), 0);
        if (name === 'hours') {
          await page.locator('input').focus();
          await page.keyboard.press('Home');
          await linked('2030-01-01', ['7h 42m', '0']);
          const labels = await page.locator('[data-lane="0"] [data-tick]').allTextContents();
          assert(labels.length > 1 && labels.every((t) => /^\d+h$/.test(t)), labels.join());
          const flat = await page.locator('[data-lane="1"] [data-tick]').allTextContents();
          assert(flat.every((t) => !/[-−]/.test(t)), flat.join());
          assert.equal(await page.locator('[data-lane="0"]').evaluate((e) => getComputedStyle(e).overflow), 'hidden');
        }
        if (name === 'eight') {
          // Gap values stay on one line, so the slider holds still. 652 px is Grok's native Page width.
          for (const size of [width, 540, 652]) {
            await page.setViewportSize({ width: size, height: 900 });
            await page.locator('input').focus();
            await page.keyboard.press('Home');
            await linked('2030-01-01', Array(8).fill('0'));
            const top = (await page.locator('[data-track]').boundingBox()).y;
            await page.keyboard.press('ArrowRight');
            await page.keyboard.press('ArrowRight');
            await linked('2030-01-03', Array(8).fill('N/A'));
            if (size === 652 && theme === 'dark') await page.screenshot({ path: path.join(output, `${label}-eight-gap.png`) });
            assert.equal((await page.locator('[data-track]').boundingBox()).y, top, 'Slider holds still');
            const heights = await page.locator('[data-readout]').evaluateAll((nodes) => nodes.map((n) => n.getBoundingClientRect().height));
            assert(heights.every((h) => h < 40), 'Gap values stay on one line');
          }
        }
      });
      await check(label + ': offline and error free', async () => { assert.deepEqual(network, []); assert.deepEqual(errors, []); });
      await context.close();
    }
  } finally { await browser.close(); }
}
await fs.writeFile(path.join(output, 'results.json'), JSON.stringify({ strict_tsc: true, results }, null, 2));
const failed = results.filter((r) => !r.passed);
console.log(JSON.stringify({ checks: results.length, passed: results.length - failed.length, failed }, null, 2));
if (failed.length) process.exitCode = 1;

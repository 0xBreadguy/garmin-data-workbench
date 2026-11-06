/**
 * Synthetic browser checks for the exact exported Grok TSX, using a React shim.
 * This is not the native Grok compiler, sandbox, Page wrapper or delivery test.
 *
 * Setup: npm ci --prefix scripts/grok_harness
 *        npm exec --prefix scripts/grok_harness -- playwright install chromium
 * Run: node scripts/test_grok_widget.mjs --fixtures /new/fixtures --output-dir /checks
 * Optional: --chromium /absolute/chromium (otherwise Playwright's bundled browser).
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import assert from 'node:assert/strict';

const here = path.dirname(fileURLToPath(import.meta.url));
const requireDev = createRequire(path.join(here, 'grok_harness', 'package.json'));
let esbuild, chromium;
try {
  esbuild = requireDev('esbuild');
  ({ chromium } = requireDev('playwright'));
} catch {
  throw new Error('Install optional harness dependencies: npm ci --prefix scripts/grok_harness');
}

const flags = new Map();
for (let i = 2; i < process.argv.length; i += 2) {
  const key = process.argv[i], value = process.argv[i + 1];
  if (!['--fixtures', '--output-dir', '--chromium'].includes(key) || !value || flags.has(key)) {
    throw new Error('Usage: --fixtures DIR --output-dir DIR [--chromium EXECUTABLE]');
  }
  flags.set(key, value);
}
if (!flags.has('--fixtures') || !flags.has('--output-dir')) throw new Error('Both --fixtures and --output-dir are required.');
const fixtureDir = path.resolve(flags.get('--fixtures'));
const outputDir = path.resolve(flags.get('--output-dir'));
const receipt = JSON.parse(await fs.readFile(path.join(fixtureDir, 'fixtures.json'), 'utf8'));
assert.equal(receipt.synthetic, true, 'The browser harness only accepts its synthetic fixture manifest.');
await fs.mkdir(outputDir, { recursive: true });

const shim = `
import * as React from 'react';
export * from 'react';
export function useGrokTheme() { return {kind:window.__HARNESS_THEME__}; }
export function Page({title,summary,width,children}) {
  return <main style={{maxWidth:width==='full'?'none':880,margin:'0 auto',padding:20}}>
    <h1 style={{fontSize:24,letterSpacing:'-.04em',fontWeight:600,margin:'0 0 12px'}}>{title}</h1>
    {summary&&<p>{summary}</p>}{children}</main>;
}
export function Section({heading,children}) { return <section>{heading&&<h2>{heading}</h2>}{children}</section>; }
`;

async function buildScenario(name) {
  const source = await fs.readFile(path.join(fixtureDir, name + '.canvas.tsx'));
  assert.equal(createHash('sha256').update(source).digest('hex'), receipt.source_sha256[name], 'Exported source changed after its fixture receipt');
  const entry = `import {createRoot} from 'react-dom/client';
    import App from ${JSON.stringify(path.join(fixtureDir, name + '.canvas.tsx'))};
    createRoot(document.getElementById('root')).render(<App/>);`;
  const result = await esbuild.build({
    stdin: { contents: entry, loader: 'tsx', resolveDir: here, sourcefile: 'grok-harness-entry.tsx' },
    bundle: true, write: false, format: 'iife', platform: 'browser', target: 'es2022',
    jsx: 'automatic', nodePaths: [path.join(here, 'grok_harness', 'node_modules')],
    define: { 'process.env.NODE_ENV': '"production"' },
    plugins: [{ name: 'grok-react-test-shim', setup(build) {
      build.onResolve({ filter: /^grok\/canvas$/ }, () => ({ path: 'grok-shim', namespace: 'grok-test' }));
      build.onLoad({ filter: /.*/, namespace: 'grok-test' }, () => ({ contents: shim, loader: 'tsx', resolveDir: here }));
    }}],
  });
  const code = result.outputFiles[0].text.replace(/<\/script/gi, '<\\/script');
  for (const theme of ['light', 'dark']) {
    const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
      <title>Synthetic Grok React shim — ${name}</title><style>
      *{box-sizing:border-box}body{margin:0;font-family:system-ui,sans-serif;background:${theme === 'dark' ? '#101114' : '#fff'};color:${theme === 'dark' ? '#edf2fa' : '#152b4b'}}
      button,input,select{font:inherit}button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid #559aff;outline-offset:3px}
      </style></head><body><div id="root"></div><script>window.__HARNESS_THEME__=${JSON.stringify(theme)};</script><script>${code}</script></body></html>`;
    await fs.writeFile(path.join(outputDir, `${name}-${theme}.html`), html);
  }
}

const results = [], failures = [];
let assertionCount = 0;
async function check(label, fn) {
  try { await fn(); results.push({ label, passed: true }); assertionCount++; }
  catch (error) { results.push({ label, passed: false, error: error.message }); failures.push({ label, error: error.message }); }
}
const laneKeys = ['sleep_duration', 'overnight_hrv', 'resting_heart_rate', 'sleep_score', 'body_battery_charged'];
function lane(page, key) { return page.getByTestId('lane-' + key); }
async function selectedDate(page) { return lane(page, 'sleep_duration').getAttribute('data-selected-date'); }
async function assertLinked(page, expected) {
  for (const key of laneKeys) assert.equal(await lane(page, key).getAttribute('data-selected-date'), expected, key);
}
async function chooseIndex(page, index) {
  await page.locator('#day-range').evaluate((element, value) => {
    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
    setter.call(element, String(value));
    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
  }, index);
}
async function noOverflow(page) {
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1), true, 'Horizontal overflow');
}
async function visibleText(page) { return page.locator('body').innerText(); }
function displayDuration(seconds) {
  const minutes = Math.round(seconds / 60);
  return `${Math.floor(minutes / 60)}h ${String(minutes % 60).padStart(2, '0')}m`;
}

for (const name of Object.keys(receipt.snapshots)) await buildScenario(name);
const browser = await chromium.launch({ headless: true, ...(flags.has('--chromium') ? { executablePath: path.resolve(flags.get('--chromium')) } : {}) });
try {
  for (const width of [390, 728]) for (const theme of ['light', 'dark']) {
    const label = `${width}-${theme}`;
    const context = await browser.newContext({ viewport: { width, height: 1100 }, colorScheme: theme });
    const page = await context.newPage();
    page.setDefaultTimeout(5000);
    page.setDefaultNavigationTimeout(30000);
    const network = [], errors = [];
    page.on('request', request => { if (/^https?:/i.test(request.url())) network.push(request.url()); });
    page.on('pageerror', error => errors.push(error.message));
    await page.route(/^https?:\/\//, route => route.abort());
    async function open(name) {
      await page.goto(pathToFileURL(path.join(outputDir, `${name}-${theme}.html`)).href);
      await page.locator('#day-range').waitFor({ state: 'visible' });
    }
    await open('normal');
    await check(`${label}: initial range and synthetic provenance`, async () => {
      assert.match(await visibleText(page), /synthetic/i);
      await assertLinked(page, '2026-04-30');
      assert.equal(await page.locator('#day-range').getAttribute('max'), '13');
    });
    await check(`${label}: keyboard selection links every lane`, async () => {
      await page.locator('#day-range').focus();
      await page.keyboard.press('ArrowLeft');
      await assertLinked(page, '2026-04-29');
    });
    await check(`${label}: tab arrows move selected view and keyboard focus together`, async () => {
      await page.getByRole('tab', { name: 'Trends', exact: true }).focus();
      await page.keyboard.press('ArrowRight');
      assert.equal(await page.evaluate(() => document.activeElement.id), 'tab-night');
      assert.equal(await page.getByRole('tab', { name: 'Night detail', exact: true }).getAttribute('aria-selected'), 'true');
      await page.keyboard.press('ArrowLeft');
      assert.equal(await page.evaluate(() => document.activeElement.id), 'tab-trends');
      await page.locator('#day-range').waitFor({ state: 'visible' });
    });
    await check(`${label}: every chart can select a date`, async () => {
      for (const key of laneKeys) {
        const box = await lane(page, key).boundingBox();
        await lane(page, key).click({ position: { x: box.width * .42, y: box.height * .45 } });
        const date = await selectedDate(page);
        assert.notEqual(date, '2026-04-30');
        await assertLinked(page, date);
      }
    });
    await check(`${label}: drag changes linked selection`, async () => {
      await lane(page, 'sleep_duration').scrollIntoViewIfNeeded();
      const box = await lane(page, 'sleep_duration').boundingBox();
      await page.mouse.move(box.x + box.width * .3, box.y + box.height * .45);
      await page.mouse.down();
      await page.mouse.move(box.x + box.width * .85, box.y + box.height * .45, { steps: 8 });
      await page.mouse.up();
      const date = await selectedDate(page);
      assert.ok(date >= '2026-04-24');
      await assertLinked(page, date);
      assert.equal(await page.evaluate(() => String(window.getSelection())), '');
    });
    await check(`${label}: emulated touch pointer selects across lanes`, async () => {
      const chart = lane(page, 'overnight_hrv');
      await chart.scrollIntoViewIfNeeded();
      const box = await chart.boundingBox();
      await chart.dispatchEvent('pointerdown', { pointerType: 'touch', pointerId: 7,
        clientX: box.x + box.width * .6, clientY: box.y + box.height / 2, buttons: 1 });
      const date = await selectedDate(page);
      await assertLinked(page, date);
      assert.ok(date >= '2026-04-23' && date <= '2026-04-26');
      await chart.dispatchEvent('pointerup', { pointerType: 'touch', pointerId: 7, buttons: 0 });
    });
    await check(`${label}: Last 7 clamps selected date`, async () => {
      await chooseIndex(page, 0);
      await assertLinked(page, '2026-04-17');
      await page.getByRole('button', { name: 'Last 7', exact: true }).click();
      assert.equal(await page.locator('#day-range').getAttribute('min'), '7');
      assert.ok((await selectedDate(page)) >= '2026-04-24');
      await page.getByRole('button', { name: 'All loaded', exact: true }).click();
    });
    await page.screenshot({ path: path.join(outputDir, `${label}-trends.png`), fullPage: true });
    await check(`${label}: selected-night details use source values`, async () => {
      await chooseIndex(page, 13);
      await page.getByRole('tab', { name: 'Night detail', exact: true }).click();
      const expected = receipt.snapshots.normal.report.sleep.nights[13].values;
      assert.ok((await visibleText(page)).includes(displayDuration(expected.sleep_duration)));
      assert.ok((await visibleText(page)).includes(displayDuration(expected.sleep_awake)));
      assert.match(await visibleText(page), /Garmin|estimate/i);
      await noOverflow(page);
    });
    await page.screenshot({ path: path.join(outputDir, `${label}-night.png`), fullPage: true });
    await check(`${label}: comparison uses shared means and independent coverage`, async () => {
      await page.getByRole('tab', { name: 'Compare', exact: true }).click();
      for (const [metric, comparison] of Object.entries(receipt.snapshots.normal.comparison.metrics)) {
        const row = page.getByTestId('compare-' + metric);
        await row.waitFor();
        const text = await row.innerText();
        for (const period of ['baseline', 'period']) {
          const value = comparison[period].mean_of_available_days;
          assert.ok(text.includes(metric === 'sleep_duration' ? displayDuration(value) : String(Math.round(value * 10) / 10)), `${metric} ${period} mean`);
          assert.ok(text.includes(`${comparison[period].coverage.days_with_value}/${comparison[period].coverage.requested_days}`), `${metric} ${period} coverage`);
        }
        if (metric === 'sleep_score') {
          const deltaText = await row.locator('[data-change]').innerText();
          assert.match(deltaText, /pts$/);
          assert.doesNotMatch(deltaText, /\/\s*100/);
          assert.ok(deltaText.includes(String(Number(comparison.change.mean_difference.toFixed(1)))));
        }
      }
      await noOverflow(page);
    });
    await page.screenshot({ path: path.join(outputDir, `${label}-compare.png`), fullPage: true });
    await open('failure');
    await check(`${label}: failed HRV splits segments without erasing other metrics`, async () => {
      const spans = await lane(page, 'overnight_hrv').locator('path[data-series="overnight_hrv"]').evaluateAll(nodes => nodes.map(n => [n.getAttribute('data-start-date'), n.getAttribute('data-end-date')]));
      assert.ok(spans.length >= 2, 'Expected line segments on both sides of Jan 16');
      assert.ok(spans.every(([start, end]) => !(start < '2026-01-16' && end > '2026-01-16')), 'A path bridges the missing date');
      assert.equal(await lane(page, 'overnight_hrv').locator('[data-day="2026-01-16"][data-value]').count(), 0);
      assert.ok(await lane(page, 'resting_heart_rate').locator('[data-day="2026-01-16"][data-value]').count() > 0);
      await chooseIndex(page, 4);
      await page.getByRole('tab', { name: 'Night detail', exact: true }).click();
      assert.match(await visibleText(page), /unavailable|failed/i);
    });
    await check(`${label}: incomplete comparisons show a warning for either period`, async () => {
      await page.getByRole('tab', { name: 'Compare', exact: true }).click();
      for (const [metric, comparison] of Object.entries(receipt.snapshots.failure.comparison.metrics)) {
        if (comparison.warnings.some(warning => warning.endsWith('_incomplete_coverage'))) {
          assert.match(await page.getByTestId('compare-' + metric).innerText(), /incomplete|partial|missing/i, metric);
        }
      }
    });
    await open('incomplete');
    await check(`${label}: incomplete stages do not stack`, async () => {
      assert.equal(await lane(page, 'sleep_duration').locator('[data-day="2026-02-05"] [data-stage]').count(), 0);
      assert.equal(await lane(page, 'sleep_duration').locator('[data-day="2026-02-08"] [data-stage]').count(), 0);
      assert.ok(await lane(page, 'sleep_duration').locator('[data-day="2026-02-06"] [data-stage]').count() > 0);
      await noOverflow(page);
    });
    await open('missing');
    await check(`${label}: all-missing range is explicit, no zero points`, async () => {
      assert.match(await visibleText(page), /no observations|unavailable/i);
      for (const key of laneKeys) assert.equal(await lane(page, key).locator('[data-value]').count(), 0, key);
      assert.equal(await page.locator('#day-range').getAttribute('max'), '6');
      await noOverflow(page);
    });
    await page.screenshot({ path: path.join(outputDir, `${label}-missing.png`), fullPage: true });
    await open('zero');
    await check(`${label}: zero stays zero and failure stays missing`, async () => {
      assert.ok(await lane(page, 'sleep_score').locator('[data-day="2026-01-02"][data-value="0"]').count() > 0);
      assert.equal(await lane(page, 'sleep_duration').locator('[data-day="2026-01-03"][data-value]').count(), 0);
      assert.equal(await lane(page, 'overnight_hrv').locator('[data-day="2026-01-02"][data-value]').count(), 0);
      await chooseIndex(page, 1);
      await page.getByRole('tab', { name: 'Night detail', exact: true }).click();
      assert.match(await visibleText(page), /0h\s+0?0m/);
    });
    await open('single');
    await check(`${label}: one-day range and comparison unavailable`, async () => {
      assert.equal(await page.locator('#day-range').getAttribute('max'), '0');
      await page.getByRole('tab', { name: 'Compare', exact: true }).click();
      assert.match(await visibleText(page), /two|at least|unavailable|single/i);
      await noOverflow(page);
    });
    await open('ninety');
    await check(`${label}: ninety-day boundary remains responsive`, async () => {
      assert.equal(await page.locator('#day-range').getAttribute('max'), '89');
      await chooseIndex(page, 0);
      await assertLinked(page, '2026-01-01');
      await noOverflow(page);
    });
    await open('warning');
    await check(`${label}: current/future warning renders once for either period`, async () => {
      await page.getByRole('tab', { name: 'Compare', exact: true }).click();
      for (const metric of laneKeys) {
        const rowText = await page.getByTestId('compare-' + metric).innerText();
        assert.equal((rowText.match(/Includes today or future dates/g) || []).length, 1, metric);
        assert.match(rowText, /observations may still change/);
      }
      await noOverflow(page);
    });
    await check(`${label}: no runtime errors or network requests`, async () => {
      assert.deepEqual(errors, []);
      assert.deepEqual(network, []);
    });
    await context.close();
  }
} finally { await browser.close(); }

const report = {
  harness: 'Exact exported synthetic TSX with local React grok/canvas shim',
  limitation: 'Does not verify native Grok compilation, theme wrappers, sandbox, delivery, physical touch or persistence.',
  source_sha256: receipt.source_sha256,
  widths: [390, 728], themes: ['light', 'dark'], assertionCount,
  passed: failures.length === 0, results,
};
await fs.writeFile(path.join(outputDir, 'checks.json'), JSON.stringify(report, null, 2) + '\n');
console.log(JSON.stringify({ passed: report.passed, assertionCount, failures, outputDir }, null, 2));
if (failures.length) process.exitCode = 1;

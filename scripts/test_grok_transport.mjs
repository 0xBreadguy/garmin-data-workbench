/**
 * Optional development checks for the actual packaged decoder and renderer.
 * Uses the synthetic fixtures from preview_grok_widget.py and existing harness
 * dependencies. No Node dependency is added to the installed workbench.
 *
 * node scripts/test_grok_transport.mjs --fixtures /new/fixtures
 * This checks local decoding/React output, not Grok's compiler or delivery.
 */
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createRequire } from 'node:module';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const requireDev = createRequire(path.join(here, 'grok_harness', 'package.json'));
let esbuild;
try { esbuild = requireDev('esbuild'); }
catch { throw new Error('Install optional harness dependencies: npm ci --prefix scripts/grok_harness'); }
if (process.argv.length !== 4 || process.argv[2] !== '--fixtures') {
  throw new Error('Usage: node scripts/test_grok_transport.mjs --fixtures DIR');
}
const fixtures = path.resolve(process.argv[3]);
const receipt = JSON.parse(await fs.readFile(path.join(fixtures, 'fixtures.json'), 'utf8'));
assert.equal(receipt.synthetic, true, 'Use generated synthetic fixtures only.');
const template = await fs.readFile(path.join(here, '../src/garmin_archive/ui/recovery.canvas.tsx'), 'utf8');
const marker = '/*__RECOVERY_SNAPSHOT__*/';
assert.equal(template.split(marker).length, 2);
const initialization = `const snapshot = decodeTransport(${marker});`;
assert.equal(template.split(initialization).length, 2, 'Update this check deliberately when initialization changes.');
const [before, after] = template.split(initialization);

function extractPacket(source) {
  assert.ok(source.startsWith(before) && source.endsWith(after), 'Regenerate fixtures for the current template.');
  const block = source.slice(before.length, source.length - after.length);
  const lines = block.split('\n'), parts = [], names = [];
  for (const [i, line] of lines.slice(0, -1).entries()) {
    const match = /^const (transportPart\d+) = (".*");$/.exec(line);
    assert.ok(match, 'Expected a complete inert string declaration.');
    assert.equal(match[1], `transportPart${i}`, 'Parts must be sequential.');
    const part = JSON.parse(match[2]);
    assert.equal(typeof part, 'string');
    assert.ok(part.length > 0 && part.length <= 2048 && /^[\x00-\x7F]*$/.test(part), 'Bounded ASCII transport part.');
    names.push(match[1]); parts.push(part);
  }
  assert.ok(parts.length > 0);
  assert.equal(lines.at(-1), `const snapshot = decodeTransport(JSON.parse([${names.join(',')}].join("")));`);
  return JSON.parse(parts.join(''));
}

// Explicit view contract, independent of production packing/projection code.
function expectedProjection(source) {
  const report = source.report;
  const result = { schema_version: source.schema_version, report: {
    from: report.from, to: report.to, archive_provenance: report.archive_provenance,
    sleep: { nights: report.sleep.nights.map(n => ({
      day: n.day, status: n.status, stages_complete: n.stages_complete, fetched_at: n.fetched_at,
      timing: { start_utc: n.timing.start_utc, end_utc: n.timing.end_utc,
        start_local: n.timing.start_local, end_local: n.timing.end_local },
      values: { sleep_duration: n.values.sleep_duration, sleep_need: n.values.sleep_need,
        sleep_awake: n.values.sleep_awake, sleep_score: n.values.sleep_score,
        sleep_deep: n.values.sleep_deep, sleep_light: n.values.sleep_light,
        sleep_rem: n.values.sleep_rem, sleep_unmeasurable: n.values.sleep_unmeasurable },
    })) },
    trends: Object.fromEntries(['overnight_hrv', 'resting_heart_rate', 'body_battery_charged'].map(metric =>
      [metric, { points: report.trends[metric].points.map(p =>
        ({ day: p.day, value: p.value, status: p.status, fetched_at: p.fetched_at })) }])),
  }, comparison: null };
  if (source.comparison !== null) {
    result.comparison = { metrics: Object.fromEntries(Object.entries(source.comparison.metrics).map(([metric, c]) => {
      const period = p => ({ from: p.from, to: p.to, mean_of_available_days: p.mean_of_available_days,
        coverage: { days_with_value: p.coverage.days_with_value, requested_days: p.coverage.requested_days },
        freshness: { oldest_available_fetch: p.freshness.oldest_available_fetch,
          newest_available_fetch: p.freshness.newest_available_fetch } });
      return [metric, { baseline: period(c.baseline), period: period(c.period),
        change: { status: c.change.status, mean_difference: c.change.mean_difference }, warnings: c.warnings }];
    })) };
  }
  return result;
}

function loadCommonJS(code) {
  const module = { exports: {} };
  // Trusted local synthetic test code. The exported native Page has no eval.
  new Function('module', 'exports', 'require', code)(module, module.exports, requireDev);
  return module.exports;
}
const decoderSource = template.slice(0, template.indexOf('const snapshot =')) + '\nexport { decodeTransport };';
const decodedModule = await esbuild.transform(decoderSource, { loader: 'tsx', format: 'cjs', target: 'es2022' });
const { decodeTransport } = loadCommonJS(decodedModule.code);

const shim = `import * as React from 'react'; export * from 'react';
  const state = {values:[], index:0, theme:'light'};
  export function reset(values,theme){state.values=values;state.theme=theme;state.index=0;}
  export function useState(initial){return [state.values[state.index++],()=>{}];}
  export function useGrokTheme(){return {kind:state.theme};}
  export function Page({title,children}){return <main><h1>{title}</h1>{children}</main>;}
  export function Section({children}){return <section>{children}</section>;}`;
async function renderer(source) {
  const entry = `import {renderToStaticMarkup} from 'react-dom/server';
    import {reset} from 'grok/canvas'; import App from 'transport-under-test';
    export function render(values,theme){reset(values,theme);return renderToStaticMarkup(<App/>);}`;
  const built = await esbuild.build({ stdin: { contents: entry, loader: 'tsx', resolveDir: here },
    bundle: true, write: false, format: 'cjs', platform: 'node', target: 'es2022', jsx: 'automatic',
    external: ['react', 'react-dom/server', 'react/jsx-runtime'],
    plugins: [{ name: 'native-test-shim', setup(build) {
      build.onResolve({ filter: /^grok\/canvas$/ }, () => ({ path: 'shim', namespace: 'grok-test' }));
      build.onResolve({ filter: /^transport-under-test$/ }, () => ({ path: 'source', namespace: 'grok-test' }));
      build.onLoad({ filter: /.*/, namespace: 'grok-test' }, args =>
        ({ contents: args.path === 'shim' ? shim : source, loader: 'tsx', resolveDir: here }));
    } }],
  });
  return loadCommonJS(built.outputFiles[0].text).render;
}

let checks = 0;
for (const [name, canonical] of Object.entries(receipt.snapshots)) {
  const source = await fs.readFile(path.join(fixtures, name + '.canvas.tsx'), 'utf8');
  assert.equal(createHash('sha256').update(source).digest('hex'), receipt.source_sha256[name], 'Fixture source changed.');
  const packet = extractPacket(source);
  assert.deepEqual(decodeTransport(packet), expectedProjection(canonical), `${name}: canonical field parity`);
  assert.equal(packet.range[0], 0, 'Exercise dictionary index zero.');
  assert.throws(() => decodeTransport({ ...packet, codec_version: 2 }), /Unsupported recovery transport version/);
  assert.throws(() => decodeTransport({ ...packet, schema_version: 2 }), /Unsupported recovery transport version/);
  checks += 4;
  const fullSource = template.replace(initialization, `const snapshot = ${JSON.stringify(canonical)} as Snapshot;`);
  const compactRender = await renderer(source), fullRender = await renderer(fullSource);
  const days = canonical.report.sleep.nights.length;
  for (const theme of ['light', 'dark']) for (const view of ['trends', 'night', 'compare']) {
    for (const selected of new Set([0, days - 1])) for (const last7 of [false, true]) {
      if (last7 && selected < days - 7) continue;
      const state = [selected, view, last7];
      assert.equal(compactRender(state, theme), fullRender(state, theme), `${name}/${theme}/${view}/${selected}/${last7}: rendered parity`);
      checks++;
    }
  }
}
console.log(JSON.stringify({ passed: true, scenarios: Object.keys(receipt.snapshots).length, checks,
  scope: 'Canonical decoder parity, unsupported versions, and identical static React output; native Grok delivery not exercised.' }, null, 2));

# Grok explorer design pass — November 6, 2026

## Scope and result

The packaged Grok Page now follows the branded [Muse widget](../INTERACTIVE_CHARTS.md).
Two private synthetic Pages, April 17–30 and January 12–18, render and respond in the
native Mac Grok Bot app in its dark theme. Light theme, phones, touch and reopening
remain untested.

The branded Muse branch was merged in so that both hosts share `brand.json`. No
archive, credential, scheduled job or personal Page was touched. All new data is
synthetic. Nothing was pushed or shared.

## What changed

- **Brand:** colors and logo come only from `brand.json` and `assets/logo.svg`. Stage
  order and names match the PNG charts: Deep, REM, Light, Unclassified.
- **Layout:** hero built from the logo's bubbles and an unsmoothed data line, a date
  scrubber aligned to the chart columns, period bubbles and zero-based comparison bars.
- **Selection:** a mouse hover previews a night; a press, drag, tap or arrow key selects.
  Marks are not rebuilt on selection. Stepping through 90 nights in the local harness
  held about 17 ms per step in Chromium and WebKit.
- **Gaps:** the PNG charts' status shapes, a shared key, and a lone observation keeps
  a visible mark.
- **Copy:** shared date wording, proper field names, and each explanation stated once.
- **Fifth lane:** Body Battery moved from a chart lane to the night summary, as in Muse.
  It remains in Night detail, Compare and coverage.

## Native evidence

**Directly observed in the app:**

| Check | April result | January result |
| --- | --- | --- |
| Load | Thu, Apr 30: sleep 6h 55m, need 7h 55m, HRV 56 ms, RHR 60 bpm, score 90 / 100, awake 0h 23m, Body Battery 60 points, 14/14 | `Jan 12–18, 2026 · 7 days`, no window control |
| Stages | Deep 1h 33m, REM 1h 34m, Light 3h 48m, Unclassified 0h 00m | Tinted box on Jan 17; no proportions inferred |
| Selection | Chart click selected Apr 24 across every lane: sleep 7h 53m, need 7h 50m, HRV 44 ms, RHR 56 bpm, score 88 / 100 | Jan 16: sleep 7h 49m, HRV Unavailable, RHR 61 bpm, score 74 / 100 |
| Keyboard | Left and Right each moved one night after a chart click | Right moved one night |
| Missing data | Not applicable | `×` at Jan 16 and `◇` at Jan 17 with no bar; no line bridges a gap; Jan 18's lone point shows |
| Layout stability | Not applicable | Hero height unchanged between Jan 16 and Jan 17 |
| Compare | Sleep 7h 27m / 7h 24m / −3.2 min; HRV 49.7 / 47.0 / −2.7; RHR 58.3 / 58.0 / −0.3; score 79.0 / 78.7 / −0.3; Body Battery 60.0 / 60.0 / 0.0; each 7/7 days | `Incomplete coverage` per metric, explanation once |
| Other controls | Last 7 clamps and re-scales; `Next` disables on the last night without losing focus | Failed-refresh wording in Night detail |
| Privacy | Share menu: **Only you** | Share menu: **Only you** |

**Reported by the user after trying the April Page:** hover preview and mouse drag work.
The control tool used for the checks above can do neither.

**Reported by Grok, not independently inspected:** final source byte-identical to the
export for each Page, 58,359 bytes for April and 57,137 for January. It compared
actual saved `ReadCanvas` bytes, excluding only the response wrapper.

## What the real app showed

Local checks could not have found these. The [host's behavior](../GROK_CHARTS.md#what-the-host-does-to-a-page)
is written up with the workarounds.

- A runtime color adapter repainted the first native build: white shapes went dark and
  secondary text changed. An explicit root background fixed the text and SVG.
- Host styling on native `table`, `p` and `h3` added cell borders and a second font.
- The compiler rejected a diagnostic Page for `matchMedia` on the color scheme and
  another for `outerHTML`. The renderer uses neither.

Two final renders differ from intent, and both were accepted:

- The logo plate is authored as `#b4d1ff` and sampled near-white, `#fefefe` to `#ffffff`.
  That matches Muse's white plate, so it stays. The reason is unknown.
- The lone hero point paints about 3 px wide natively, against 6 px locally.

Grok's floating composer and fixed header overlap the Page at some scroll positions.
That is host chrome, and all content scrolls clear of it.

## Delivery reliability

Grok must retype source into its Page writer. It reports no supported way to pass a
file to that writer.

| Delivery | Slips | Outcome |
| --- | --- | --- |
| First build, April | Step 9: `p.secondary` for `p.stages[i]` | Compiled. Caught by byte check |
| First build, January | None | Clean |
| Second build, April | Step 5 lost 1,593 bytes. Step 8 lost 7 bytes | Compiled. Caught by byte check. Two remembered corrections failed to compile |
| Second build, January | Step 4 lost 7 bytes | Compiled. Corrected by script |

Every slip compiled, so compilation is not evidence of correct text. The plan now checks
each step's `after_sha256`, and the handoff ships `fix_step.py`, which prints the exact
correction. Later small updates used one atomic edit batch per Page, without a slip.

## Local verification

On the delivered renderer:

- **Passed:** 212 offline tests.
- **Passed:** 324 browser assertions through the React stand-in, in Chromium and WebKit at
  320, 390 and 728 px in both themes. One WebKit run hit a single "waiting for element
  to be stable" timeout. Three later WebKit runs passed all 162 assertions.
- **Passed:** 194 decoder and static-render parity checks.
- **Passed:** a strict TypeScript compile of the export against a local type stand-in.
- **Passed:** installed-wheel smoke checks in base and charts modes.

The harness does not reproduce Grok's adapter, so its guards cover causes only. Judge
appearance from the real app.

## Not verified

Native light theme; physical touch and phone delivery; reopening after restart; cross-device state; Windows and Linux hosts; a Page
built from a personal archive. The Mac-specific host findings may change with the app.

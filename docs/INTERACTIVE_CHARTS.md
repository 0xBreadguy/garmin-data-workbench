# Local interactive chart trial

This experimental MCP App keeps sleep and recovery exploration inside a compatible assistant. It is a local trial, not a replacement for PNG chart delivery or a standalone dashboard.

## Try an isolated installation

Use a new environment and a new synthetic archive outside the repository. Preserve existing registrations, installations and scheduled collectors. From this checkout, after offline tests:

```sh
uv build
uv venv /absolute/new/trial/venv --python 3.12
uv pip install --python /absolute/new/trial/venv/bin/python dist/garmin_data_workbench-0.1.0-py3-none-any.whl
uv run --quiet --locked python scripts/create_demo_archive.py /absolute/new/trial/archive
```

On Windows the environment executables are under `Scripts` rather than `bin`. The interactive app does not need the optional Matplotlib extra. Add `[charts]` when installing the wheel if PNG fallback is also wanted. Register a separate server such as `garmin-workbench-trial` in the chosen assistant, using the absolute installed `garmin-archive-mcp` executable and arguments `--data-dir /absolute/new/trial/archive`. Follow the client's supported registration/reload procedure. No network listener is needed.

In a fresh conversation after discovery, ask:

> Use garmin-workbench-trial to open the interactive sleep and recovery explorer for April 17–30, 2026. Keep it inside this conversation. Use explore_sleep_recovery, not a PNG.

The demo ends April 30, 2026; “this week” does not move those observations. Test:

- Drag through dates and use the day slider's arrow keys; all panels should select the same date.
- Open Night detail, switch nights, and inspect all four stages, source times and independent unavailable fields.
- Compare April 17–23 with April 24–30. Each metric has its own denominator and shared server-calculated change.
- Load February 5–8 for incomplete stages/score/need cases; load March 12–18 for no collected observations. No missing reading should turn into zero.
- Load January 16 to see failed HRV refresh masking independently of sleep.
- Click “Ask about this night”; the selected date and synthetic provenance should enter the same conversation, without starting a sync.

Removal is just removing this separate trial registration. Keep the old executable/registration as the rollback; do not uninstall or replace the scheduled collector to test the UI. An existing personal archive can be selected later with a deliberate read-only registration; do not mix it with synthetic data.

## Diagnose missing delivery

Treat query success, UI loading, and visible interaction as separate evidence. The host displays the app independently of the model's text. An agent's lack of browser/computer-use access does not establish that the app is absent. After success, a brief date/provenance acknowledgement is enough; do not automatically add a disclaimer, data dump, or PNG. Follow the user's report of what actually appeared.

For a missing app, compare the original tool event's `mcpAppResourceUri`, success/error state and structured result with a working conversation, then check whether the host read the UI resource and initialized the app. Record where the conversation was created and where it was viewed separately. Identical tool results with different app-load activity point toward host delivery; they do not by themselves identify the precise host defect. Test a desktop-created conversation on mobile and a mobile-created conversation on desktop, including reopening each. A narrow browser viewport alone does not test that path.

Local acceptance observation, November 5, 2026: the user reported a working interactive chart in the ChatGPT/Codex Mac app, despite the agent claiming it had not appeared. A phone-created conversation reportedly showed no app on either device. Two matching local Codex trial runs returned identical structured results and UI resource references. Desktop logs recorded resource loading and app initialization for one run, with no corresponding load events found for the other. Both agents inferred failure from unavailable computer-use/browser surfaces and generated PNG fallbacks. The guidance now avoids that inference. Mobile delivery remains unresolved; no rendering fix or general mobile compatibility is claimed.

## Muse native widget trial

Muse's native HTML widgets provide a separate in-conversation route when a custom MCP Apps host is unavailable. Use the same installed package and synthetic archive above, then run:

```sh
garmin-archive --data-dir /absolute/new/trial/archive widget sleep-recovery \
  --from 2026-04-17 --to 2026-04-30 --output /absolute/new/trial/recovery.html
```

Pass the returned absolute path unchanged to Muse's `widget.create_html_file_widget`, with `present_now: true` or embed its returned token in the reply. Do not rewrite the HTML or turn it into a file-preview link, PNG, external website, or nested iframe. Keep the file outside `workspace/your_files/` and `workspace/visual_grounding/`, which Muse treats as preview files. File generation and tool success are not proof that the user saw the widget.

The fragment bundles the shared renderer and D3 with a read-only 1–90 day snapshot (14 days by default). No charts extra, Node runtime, network listener, or CDN is needed. It refuses exports above Muse's 1 MB limit and creates new files with owner-only permissions where supported. It contains the selected health observations; use a synthetic archive for this trial and treat real exports like health data.

Touch or drag any chart, use Last 7, or switch between Trends, Night detail, and Compare. Comparison divides the loaded range at its midpoint and uses the same Python calculations and independent coverage as MCP; an odd range has one extra day in the later period. One day has no comparison. Ask Muse to generate another widget for different dates or an updated archive snapshot. The widget itself cannot query the archive or send a follow-up message. Its only durable host state is the selected date, tab, and window, using `hatchWidget`; metrics stay in the fixed snapshot. Reopening and cross-device state delivery require separate host acceptance tests.

Native capability observation, November 5, 2026: Muse 11.0 on Mac rendered a counter and its button visibly changed the value. Muse reported native HTML widget tools and no custom MCP Apps host. This established a route worth testing, not Garmin chart or mobile acceptance by itself.

Subsequent trial: branch revision `e854d04` was transferred as a Git bundle, installed in a fresh Muse environment and used to generate a synthetic April 17–30 widget (359,164 bytes). The actual Mac app displayed it in the conversation. Last 7, selected-night changes, Night detail, previous-night navigation and the five-metric comparison responded visibly. Muse reported matching revision and manifest verification. The local suite passed 182 tests, both installed-wheel modes passed, and the native/MCP browser harnesses passed 13/16 assertions respectively at widths 320, 390 and 728 in both themes. Physical-phone rendering, cross-device state and persistence after host restart remain separate acceptance checks. No public push, live sync or scheduler change was part of this trial.

## Brand

Both delivery routes render the same branded view. `src/garmin_archive/brand.json` is the only source of its colors, including the sleep stage ramp shared with PNG charts and a dark step for each color; `brand.py` turns them into CSS tokens when the page is bundled, and tests reject color literals in the UI. Hosts may supply the surface and body text. Marks, titles, summary values and the footer logo stay on brand, selected from the host's actual surface rather than the operating-system theme.

The hero repeats the logo's idea with real data: two overlapping conversation bubbles joined by a white line. That line is the visible range's unsmoothed sleep duration, labeled with its range, with a gap for any missing night. Keep the logo itself as a small footer signature in its authored colors; the white plate keeps it legible in dark themes. Vocabulary, stage order, status glyphs and date wording match the PNG charts.

## Verify the implementation

```sh
uv run --locked --extra charts python -m unittest discover -s tests -p 'test_recovery.py' -v
uv run --locked --extra charts python -m unittest discover -s tests -p 'test_widgets.py' -v
node --check src/garmin_archive/ui/recovery.js
uv build
uv run --locked python scripts/smoke_installed.py
uv run --locked --extra charts python scripts/smoke_installed.py --charts
```

The shared queries keep source units. The UI converts sleep/stage/awake seconds to minutes for hours/minutes display; sleep need already uses minutes. The app never recomputes score, Body Battery levels, or a personal baseline. Daily charge is not automatically overnight charge. Period means use independent available-day counts and retain source fetch bounds. Empty periods and invalid/overlapping ranges are explicit failures or unavailable comparisons, not numeric zero.

Automated stdio tests prove tool metadata, resource packaging, query results and read-only archive behavior. Browser harness checks prove the exercised UI and bridge messages. Neither proves the actual assistant displayed the resource or accepted an in-app follow-up. Record those host acceptance steps separately, including desktop/mobile and keyboard/touch coverage. The user-controlled local trial comes before publishing or merging.

For a repeatable browser check, run `uv run --locked python scripts/preview_recovery_app.py --output /absolute/new/recovery-harness.html`. This developer-only harness creates a disposable synthetic archive, embeds the packaged app without modifying it, and simulates the MCP Apps parent bridge. It runs 18 assertions covering initial results, date selection, touch events, window bounds, night drill-down, follow-up payloads, server comparisons, failed/missing/incomplete/single-day data, keyboard tabs, forbidden sync calls, overflow and untrusted message sources. It reports its result above the embedded app. Inspect the generated HTML with a browser test runner or an assistant HTML-preview tool; no HTTP server is needed. This harness is a test fixture, not the user-facing delivery route.

Add `--host muse` for the native widget harness. It checks the logo signature, linked/touch selection, hero and scrubber updates, brand colors following the host surface, saved state, reopening, incoming state without write-back loops, comparison rendering, missing unsupported controls, responsive overflow and absence of MCP requests. The test harness's iframe and simulated state bridge are development fixtures; the exported fragment is handed directly to Muse.

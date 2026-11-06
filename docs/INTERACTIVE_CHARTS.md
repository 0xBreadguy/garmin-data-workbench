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

## Verify the implementation

```sh
uv run --locked --extra charts python -m unittest discover -s tests -p 'test_recovery.py' -v
node --check src/garmin_archive/ui/recovery.js
uv build
uv run --locked python scripts/smoke_installed.py
uv run --locked --extra charts python scripts/smoke_installed.py --charts
```

The shared queries keep source units. The UI converts sleep/stage/awake seconds to minutes for hours/minutes display; sleep need already uses minutes. The app never recomputes score, Body Battery levels, or a personal baseline. Daily charge is not automatically overnight charge. Period means use independent available-day counts and retain source fetch bounds. Empty periods and invalid/overlapping ranges are explicit failures or unavailable comparisons, not numeric zero.

Automated stdio tests prove tool metadata, resource packaging, query results and read-only archive behavior. Browser harness checks prove the exercised UI and bridge messages. Neither proves the actual assistant displayed the resource or accepted an in-app follow-up. Record those host acceptance steps separately, including desktop/mobile and keyboard/touch coverage. The user-controlled local trial comes before publishing or merging.

For a repeatable browser check, run `uv run --locked python scripts/preview_recovery_app.py --output /absolute/new/recovery-harness.html`. This developer-only harness creates a disposable synthetic archive, embeds the packaged app without modifying it, and simulates the MCP Apps parent bridge. It runs 16 assertions covering initial results, date selection, touch events, window bounds, night drill-down, follow-up payloads, server comparisons, failed/missing/incomplete/single-day data, keyboard tabs, forbidden sync calls, overflow and untrusted message sources. It reports its result above the embedded app. Inspect the generated HTML with a browser test runner or an assistant HTML-preview tool; no HTTP server is needed. This harness is a test fixture, not the user-facing delivery route.

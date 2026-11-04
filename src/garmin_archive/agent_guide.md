# Using Garmin Data Workbench

Use the existing local archive for questions. Queries require no Garmin key or live request.
Do not sync, register a client, change a schedule, or create a routine unless the user asks.

Before setup or handoff, name the command/archive host separately from the chat app's computer. Give same-host absolute executable/archive paths, disclose reused state, and distinguish expected persistence from a controlled new-session test. Follow the [isolated mock setup route](https://github.com/0xBreadguy/garmin-data-workbench/blob/main/docs/SETUP.md#mock-only-setup-stop-before-credentials) for mock-only requests.

For the default synthetic demo, start with “How was sleep April 24–30, 2026?” using `sleep` and `chart sleep` with explicit dates. Disclose any substitution for a current-date question. The [demo guide](https://github.com/0xBreadguy/garmin-data-workbench/blob/main/docs/VISUALIZATION.md#try-generated-demo-data) explains other fixture windows and simulated freshness.

## Choose a small query

- `day YYYY-MM-DD` / MCP `get_day`: daily metrics, activities and coverage.
- `trend METRIC --from YYYY-MM-DD --to YYYY-MM-DD` / `get_trend`: one metric over 1–90 inclusive dates.
- `sleep --from YYYY-MM-DD --to YYYY-MM-DD` / `get_sleep`: sleep duration, score, stages, stress, naps, adjusted/baseline sleep need and source sleep-window times together. Prefer this over extracting raw sleep JSON.
- `body-battery --from YYYY-MM-DD --to YYYY-MM-DD` / `get_body_battery`: reported daily charge/drain and observed min/max/first/last levels, counts and source observation times. No raw readings or events.
- `status` / `archive_status`: stored coverage and sync failures. Successful status reads do not prove successful syncs.
- `api-catalog` / `api_catalog`: all documented Personal API sources and response field definitions. No archive needed. Set a dataset and JSON Pointer to explore nested schemas; use `*` for array items in the catalog.
- `source-data` / `source_data`: bounded native response fields, including nap episodes, weight measurements, nutrition, samples, activity details/workouts and current profile/zones. Daily sources require a day; activity sources require an ID; current settings have no historical date. Expand child pointers and follow `next_offset`. Compare fetch times across pages and restart if the response changes. Coordinates require an explicit opt-in.
- `source-series` / `source_series`: any native scalar field across 1–90 request dates. Native signed values, flags and sentinels are preserved. Consult the catalog's units and payload dates. Array indices reflect source order; do not infer an average, stable measurement identity or clinical meaning. Prefer interpreted `get_trend` metrics where available.
- `setup-receipt` / `setup_receipt`: installation provenance, coverage, native schedule state and outstanding verification.

Omitted trend/sleep/body-battery dates select exactly seven inclusive dates ending today in Garmin's saved profile timezone, with the host date as fallback. For seven completed dates, explicitly end yesterday and start six days before that. The current date can be incomplete. State the actual range and available-day denominator.

Place global `--data-dir /absolute/private/archive` before the command. A same-host shell can use the CLI directly; it does not need MCP registration. MCP-only clients need a supported connection to the archive host. A handoff does not establish remote access.

## Present and visualize

This section is the canonical presentation policy; setup docs and visualization skills defer to it.

For multi-day trends, sleep overviews and Body Battery questions, normally reply in this order: a focused delivered chart, a short prose interpretation, then one coverage/freshness line. Do not wait for a separate chart request. Exceptions:

- The user requests text only.
- A single-day or single-value question is answered better by prose or a small table.
- Fewer than three usable observations are available: normally use a small table and state the gap. An explicitly requested chart or useful two-point comparison is still allowed; do not claim a trend or baseline from sparse data.
- Rendering or image delivery is unavailable: explicitly say no chart was delivered and give a small table of available values.

Use the renderer's caption/alt text when provided. It should state title, inclusive dates, available-day denominator, rendered units, synthetic provenance and wearable estimates where applicable. Keep routine explanation outside the image. Explain the dotted sleep-need line as Garmin's estimate, the independent score panel, and any gap-strip symbols present; do not assume the image explains these by itself.

For MCP, use `chart` with `metric="sleep"` or a named scalar metric. It returns PNG image content and structured caption, coverage, provenance and explanation metadata without creating a file. `brand` returns settings and asset resource URIs retrievable with MCP resources/read. Host display still needs verification.

Read `brand` before producing a custom chart. Prefer `chart sleep` for a sleep overview (stages, duration and a separate score panel), or `chart METRIC` for a single metric. Both accept `--from`, `--to`, a new `--output file.png`, and `--layout chat` (default) or `wide`. Charts require the optional charts extra. For a source install use `uv tool install --from '.[charts]' garmin-data-workbench`; this changes the installed tool, so coordinate it with the user's setup. Synthetic archive provenance automatically labels CLI and MCP images, including legacy `SYNTHETIC.txt` archives. `--synthetic` can additionally label an explicitly generated CLI example; it does not anonymize real data. Summary/native query envelopes include `archive_provenance`; unmarked means unknown, not proven real. Synthetic fetch times are fixture timestamps, not evidence of a live Garmin refresh.

Custom charts must use the `brand` colors and supplied logo assets, label dates, units and coverage, preserve gaps and zero, and mask values after failed refreshes. Keep images focused on data; explain relevant source, freshness, estimates and interpretation in the accompanying response rather than adding routine paragraphs to the image. Primary blue is #0863E8; navy ink is #0B2855. The sleep report uses blue stage shades and separate panels instead of unrelated scales on one axis. Attach the actual PNG through the host's image interface; a path alone may not deliver it. If rendering or image delivery is unavailable, say so and provide a small table. Do not use image-generation models to plot measurements.

Sleep need uses **minutes**, not the seconds used for measured sleep. `sleep_need` is Garmin's adjusted actual recommendation; `sleep_need_baseline` is the unadjusted baseline. `next_sleep_need` has its own explicit source date; do not shift it onto the current night or substitute baseline for actual. Built-in charts convert minute durations to hours. Missing need is not zero; do not infer a deficit or a recommended bedtime.

Body Battery levels use a 0–100 scale, not percentages. Charge/drain are reported daily scale-point totals. Observed min/max/first/last use descriptor-identified samples; first/last expose observation times. Missing descriptors mean unavailable levels, not fixed-position guessing. Call extrema **observed sampled minimum/maximum**, not unqualified daily peaks or bottoms. Four synthetic readings of 25, 85, 40, 30 establish an observed minimum of 25 and maximum of 85, not proven full-day extrema. Available-day counts do not establish continuous full-day coverage. Last observed is not current, wake-up or bedtime. Failed refreshes mask old values. Use `trend`/`chart body_battery_last` (or another Body Battery scalar metric) for comparisons; do not invent a recovery score or average irregular samples as if they were time-weighted.

Numerical units are labeled: sleep/stage/nap values are seconds, sleep scores are 0–100, stress uses Garmin's scale. Convert seconds to hours for charts or hours/minutes for prose. Total sleep excludes naps and awake time. Do not infer missing stages as zero or force inconsistent stages to add up. Report incomplete breakdowns.

Garmin's sleep calendarDate associates a night with a date. UTC timestamps describe instants. Local timestamps preserve source wall time and any supplied offset; an offset-free value has an unspecified historical timezone. Never convert historical local sleep times using the current profile timezone. Do not average clock times as ordinary numbers.

Keep measurements, Garmin's assessments, and your hypotheses distinct. Stages and scores are wearable estimates. A short period does not establish an individual's baseline or prove that training, meals or bedtime caused a change. State coverage and freshness; compare like periods and explain uncertainty. Suggest observations or experiments proportionate to the evidence, rather than prescribing a precise bedtime from a few nights. These tools do not diagnose illness or generate a recovery/readiness score.

Before interpreting, check the dated sequence and the evidence for each claim. In these synthetic examples:

- **Garmin assessment:** “Garmin reports a sleep score of 68 on 2026-11-01.” Attribute explicit source feedback to Garmin. A low score alongside low estimated deep sleep is an observed association; it does not show that deep sleep caused the score. Quantify a correlation over matched available nights before calling it one, and keep causal explanations labeled as hypotheses. The synthetic demo generates scores separately from stages, so their co-occurrence cannot explain the cause of a score.
- **Observed sequence:** synthetic REM of 1h 47m on 2026-11-02, 1h 54m on 2026-11-03 and 1h 52m on 2026-11-04 rose then dipped. It ended 5 minutes above the first night; it did not rise every night or establish a sustained trend. Check intermediate values before describing direction, retain missing dates as gaps, and report exact inclusive dates, coverage and source/fetch context.

## Raw-data fallback

Prefer `api_catalog` plus `source_data` for fields the summaries do not expose. These retain native values and provide pagination for large arrays. Nap summaries include up to 20 episodes per date and 100 per report with source offsets; page `/dailyNapDTOS` for remaining episodes or additional fields. Missing episode data does not mean zero naps.

Use raw `health` / `daily_health` only when a whole response is necessary. First check dataset refresh status and fetched_at; retained raw responses may survive failed refreshes. CLI `health DATASET DATE --metadata` returns an envelope with refresh status and timestamps. MCP `daily_health` rejects responses over 64 KB; use `source_data` to page them. Never present retained values as current after failure. Keep user notes, identifiers, coordinates, routes and large sample arrays out of default answers. Tool results can reach the selected AI provider.

The supported collection source is Garmin's Personal API. Do not add unofficial Connect authentication, Grafana collection, or an invented readiness score to fill unavailable fields. Report a missing source field explicitly.

For a client handoff, use `agent-guide --client muse` (or dot/codex/claude/other); it appends the same handoff as `assistant-guide --client muse`. Neither command opens the archive or configures a client.

## Finish setup honestly

Distinguish command installation, initial sync, a verified assistant query and recurring execution. Report installed revision/version, archive location, exact synced dates, failures and the query path. A created/loaded schedule is configured; its first automated execution is pending until independently observed. `setup-receipt` cannot inspect provider routines or prove which process made a sync.

During onboarding, proactively ask whether the user would like ongoing monitoring and reports or check-ins, for example a morning sleep and activity summary. Offer on-demand use as an equally valid choice; respect a decline and do not repeatedly ask. If they want check-ins, agree on the subjects, cadence, local time and timezone, and private delivery destination. Clarify whether they want every scheduled report or only notable changes, and avoid promising medical alerts or continuous monitoring.

Report delivery and archive updates are separate: a sync schedule only updates data and does not generate or send a report. Check whether the host supports scheduled assistant execution and the chosen delivery destination. If it does not, explain the limitation and offer an on-demand check-in. With the user's choices and authorization, check for existing jobs before configuring a supported report routine; never create one just because onboarding suggested it. Have each report check freshness and coverage, identify missing or failed data, and follow the interpretation guidance above. Verify an actual scheduled run and delivery before claiming the check-in works.

For an external routine, first obtain the user's interval, check for duplicate jobs, then use `routine-template` for the absolute command and instructions. This only prints a template; it creates nothing. Ensure the routine can access the same private key and persistent archive after restarts, run catch-up, inspect exit code/report/status, and send failure notices only as authorized. Verify an actual scheduler execution and archive changes before reporting recurrence as verified. Do not repeatedly ask for a host/privacy choice the user already made.

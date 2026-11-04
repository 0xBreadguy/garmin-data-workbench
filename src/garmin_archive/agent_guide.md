# Using Garmin Data Workbench

Use the existing local archive for questions. Queries require no Garmin key or live request.
Do not sync, register a client, change a schedule, or create a routine unless the user asks.

## Choose a small query

- `day YYYY-MM-DD` / MCP `get_day`: daily metrics, activities and coverage.
- `trend METRIC --from YYYY-MM-DD --to YYYY-MM-DD` / `get_trend`: one metric over 1–90 inclusive dates.
- `sleep --from YYYY-MM-DD --to YYYY-MM-DD` / `get_sleep`: sleep duration, score, stages, stress, naps, adjusted/baseline sleep need and source sleep-window times together. Prefer this over extracting raw sleep JSON.
- `body-battery --from YYYY-MM-DD --to YYYY-MM-DD` / `get_body_battery`: reported daily charge/drain and observed min/max/first/last levels, counts and source observation times. No raw readings or events.
- `status` / `archive_status`: stored coverage and sync failures. Successful status reads do not prove successful syncs.
- `setup-receipt` / `setup_receipt`: installation provenance, coverage, native schedule state and outstanding verification.

Omitted trend/sleep/body-battery dates select exactly seven inclusive dates ending today in Garmin's saved profile timezone, with the host date as fallback. For seven completed dates, explicitly end yesterday and start six days before that. The current date can be incomplete. State the actual range and available-day denominator.

Place global `--data-dir /absolute/private/archive` before the command. A same-host shell can use the CLI directly; it does not need MCP registration. MCP-only clients need a supported connection to the archive host. A handoff does not establish remote access.

## Present and visualize

Read `brand` before producing a custom chart. Prefer `chart sleep` for a sleep overview (stages, duration and a separate score panel), or `chart METRIC` for a single metric. Both accept `--from`, `--to`, a new `--output file.png`, and `--layout chat` (default) or `wide`. Charts require the optional charts extra. For a source install use `uv tool install --from '.[charts]' garmin-data-workbench`; this changes the installed tool, so coordinate it with the user's setup. Use `--synthetic` for generated examples only; it does not anonymize real data.

Custom charts must use the `brand` colors and supplied logo assets, label dates, units, source, coverage and fetch context, preserve gaps and zero, and mask values after failed refreshes. Primary blue is #0863E8; navy ink is #0B2855. The sleep report uses blue stage shades and separate panels instead of unrelated scales on one axis. Attach the actual PNG through the host's image interface; a path alone may not deliver it. If image delivery is unavailable, say so and provide a small table. Do not use image-generation models to plot measurements.

Sleep need uses **minutes**, not the seconds used for measured sleep. `sleep_need` is Garmin's adjusted actual recommendation; `sleep_need_baseline` is the unadjusted baseline. `next_sleep_need` has its own explicit source date; do not shift it onto the current night or substitute baseline for actual. Built-in charts convert minute durations to hours. Missing need is not zero; do not infer a deficit or a recommended bedtime.

Body Battery levels use a 0–100 scale, not percentages. Charge/drain are reported daily scale-point totals. Observed min/max/first/last use descriptor-identified samples; first/last expose observation times. Missing descriptors mean unavailable levels, not fixed-position guessing. Sparse samples do not establish full-day coverage. Last observed is not current, wake-up or bedtime. Failed refreshes mask old values. Use `trend`/`chart body_battery_last` (or another Body Battery scalar metric) for comparisons; do not invent a recovery score or average irregular samples as if they were time-weighted.

Numerical units are labeled: sleep/stage/nap values are seconds, sleep scores are 0–100, stress uses Garmin's scale. Convert seconds to hours for charts or hours/minutes for prose. Total sleep excludes naps and awake time. Do not infer missing stages as zero or force inconsistent stages to add up. Report incomplete breakdowns.

Garmin's sleep calendarDate associates a night with a date. UTC timestamps describe instants. Local timestamps preserve source wall time and any supplied offset; an offset-free value has an unspecified historical timezone. Never convert historical local sleep times using the current profile timezone. Do not average clock times as ordinary numbers.

Keep measurements, Garmin's assessments, and your hypotheses distinct. Stages and scores are wearable estimates. A short period does not establish an individual's baseline or prove that training, meals or bedtime caused a change. State coverage and freshness; compare like periods and explain uncertainty. Suggest observations or experiments proportionate to the evidence, rather than prescribing a precise bedtime from a few nights. These tools do not diagnose illness or generate a recovery/readiness score.

## Raw-data fallback

Use raw `health` / `daily_health` only for fields the summaries do not expose. First check dataset refresh status and fetched_at; retained raw responses may survive failed refreshes. CLI `health DATASET DATE --metadata` returns an envelope with refresh status and timestamps. Never present retained values as current after failure. Keep user notes, identifiers, coordinates, routes and large sample arrays out of default answers. Tool results can reach the selected AI provider.

## Finish setup honestly

Distinguish command installation, initial sync, a verified assistant query and recurring execution. Report installed revision/version, archive location, exact synced dates, failures and the query path. A created/loaded schedule is configured; its first automated execution is pending until independently observed. `setup-receipt` cannot inspect provider routines or prove which process made a sync.

For an external routine, first obtain the user's interval, check for duplicate jobs, then use `routine-template` for the absolute command and instructions. This only prints a template; it creates nothing. Ensure the routine can access the same private key and persistent archive after restarts, run catch-up, inspect exit code/report/status, and send failure notices only as authorized. Verify an actual scheduler execution and archive changes before reporting recurrence as verified. Do not repeatedly ask for a host/privacy choice the user already made.

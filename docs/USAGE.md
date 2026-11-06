# Use your archive

[Setup](SETUP.md) · [Assistants](ASSISTANTS.md) · [Commands](#commands) · [SQL](#sql-and-source-data) · [Scheduling](#catch-up-and-scheduling)

## Discover the installed CLI

Start without credentials or an archive:

```sh
garmin-archive --help
garmin-archive agent-guide
garmin-archive metrics
garmin-archive api-catalog
garmin-archive api-catalog sleep --pointer '/dailyNapDTOS/*'
garmin-archive version
garmin-archive --version
```

`COMMAND --help` lists required arguments and defaults. `metrics` returns the finite interpreted metric catalog as JSON: names accepted by `trend`, titles, datasets and source units. It uses the shared query definitions, including observed Body Battery statistics; a dataset is not a promise that a metric maps directly to one native field. Use `api-catalog SOURCE` and JSON Pointer traversal for native fields. Quote pointers containing `*` so shells do not expand them. `version` reuses the installation receipt's package/build provenance, OS, Python version and optional chart-dependency availability, without inspecting an archive or schedule. `--version` prints just the package version. An unknown revision is explicit; version `0.1.0` alone does not identify the executed source revision. Chart dependency presence does not verify rendering or image delivery.

## Commands

```sh
# Sync the past seven days, including today, or an inclusive date range.
garmin-archive sync
garmin-archive sync --from 2026-01-01 --to 2026-01-07

# Check coverage, list activities or locate the database.
garmin-archive status
garmin-archive activities
garmin-archive path

# Read stored summaries without a live request.
garmin-archive day 2026-01-01
garmin-archive trend sleep_duration --from 2026-01-01 --to 2026-01-07
garmin-archive sleep --from 2026-01-01 --to 2026-01-07
garmin-archive body-battery --from 2026-01-01 --to 2026-01-07
garmin-archive api-catalog
garmin-archive source-data sleep --day 2026-01-01 --pointer /dailyNapDTOS
garmin-archive chart sleep --from 2026-01-01 --to 2026-01-07 --output sleep.png

# Replace the example ID with one from your activity list.
garmin-archive records 123456789 --limit 100
garmin-archive records 123456789 --format csv --limit 1000 > activity.csv
garmin-archive health sleep 2026-01-01
garmin-archive health sleep 2026-01-01 --metadata
garmin-archive export-original 123456789 activity.zip
```

Use `--offset` to page through activities or records (limits 1–10000; defaults 20 and 100). Native `api-catalog` and `source-data` pages allow 1–100 items; follow `next_offset` until null. Activity/record lists retain their bare-list format; advance the offset by the requested limit until an empty list. IDs and offsets must fit a signed 64-bit SQLite integer. `records --full` includes all decoded fields and may expose precise coordinates.

Put `--data-dir /absolute/private/archive` before the command to choose an archive. The database is `archive.sqlite3`; the default directory is `~/.local/share/garmin-extraction` or an absolute `$XDG_DATA_HOME/garmin-extraction`. Quote paths with spaces. On POSIX shells:

```sh
'/absolute/path with spaces/garmin-archive' --data-dir '/absolute/private archive' status
```

In native PowerShell, use the call operator for a quoted executable path:

```powershell
& 'C:\Tools\Garmin Workbench\garmin-archive.exe' --data-dir 'C:\Private Archive' status
```

Use paths on the execution host. `--data-dir` after the command is rejected with an actionable error; it does not select a different archive. Command and directory names are unchanged from the project's original name.

## Output and automation

`day`, `trend`, `compare`, `workout-summary`, `sleep`, `body-battery`, `source-data`, `source-series`, `status`, `activities`, `health` and `records` read an existing archive without creating, migrating or syncing it. They need no Garmin key. `export-original` also opens the archive read-only and writes only the requested destination, with owner-only permissions on POSIX; existing files are never overwritten. `path` prints the configured database location even if it doesn't exist, without opening or creating it.

`chart` uses the same read-only trend query and writes a new PNG. By default it prints `Chart saved to PATH`. Add `--json` to receive one JSON object on stdout after saving, with `output_path` (the supplied destination) and the shared chart metadata: `caption`, `alt_text`, `coverage`, `units`, `freshness`, `archive_provenance`, `synthetic` and `explanations`. The `delivery` field describes a saved CLI file; attaching and displaying it in the host remains a separate step.

```sh
garmin-archive --data-dir /absolute/private/archive chart body_battery_max --from 2026-01-01 --to 2026-01-07 --output body-battery.png --json
```

Keep the caption, freshness meaning and relevant explanations alongside the delivered image. Body Battery extrema describe observed samples; available-date coverage does not establish continuous full-day coverage. Explicit synthetic provenance labels charts and metadata automatically; synthetic fetch timestamps are simulated, not evidence of a live refresh. `--synthetic` can also explicitly label demo data. Use a new `.png` destination each time: existing files are never overwritten. The charts extra remains optional; see [chart installation and layouts](VISUALIZATION.md).

Both output modes follow the error contract below; a missing chart dependency exits `2` with `dependency_unavailable`. An unwritable or existing PNG destination exits `1` with `output_error`. Failures leave stdout empty and report JSON on stderr.

`sync` uses Garmin credentials/network and writes the archive. `install` prepares credentials, syncs, connects a client and can configure scheduling. `connect` probes local MCP and may register client configuration. `setup` changes the managed macOS schedule. `save-key` uses live authentication and writes the private key unless `--dry-run` is selected. These are explicit actions, not discovery checks. Locally decidable invalid ranges, limits, selectors and setup intervals fail before archive creation or authentication. Interactive cancellation and later runtime failures can still leave initialized setup state.

Successful reads write JSON to stdout by default; no `--json` flag is needed. `records --format csv` writes CSV instead. `path` prints a plain path; `chart` (without `--json`) and `export-original` print a confirmation. Help remains plain text.

For automation, call the installed `garmin-archive` executable directly. When running from a source checkout, use `uv run --quiet --locked` so uv's environment creation, build and installation messages don't precede the CLI's JSON errors on stderr:

```sh
uv run --quiet --locked garmin-archive --data-dir /absolute/private/archive status
```

Keep stdout and stderr separate when parsing results. `--quiet` suppresses uv's setup chatter; it does not turn uv's own failures (such as a dependency installation failure or an out-of-date lockfile) into CLI JSON errors. Check the exit code and handle non-JSON stderr as a launcher/setup failure. The JSON contract below applies once `garmin-archive` runs.

Read and export failures leave stdout empty and write one JSON object to stderr:

```json
{"error":{"code":"not_found","message":"Activity not found in this archive."}}
```

Branch on `error.code`, not the human-readable message. Exit codes for read and export commands are:

| Exit | Meaning | Error codes |
| --- | --- | --- |
| `0` | Query or export succeeded, including an empty result | None |
| `1` | Operational failure | `archive_unavailable`, `records_unavailable`, `invalid_data`, `output_error` |
| `2` | Invalid arguments or missing chart dependencies | `invalid_argument`, `dependency_unavailable` |
| `3` | Requested health response, activity or original file isn't stored | `not_found` |

`archive_unavailable` covers missing, unreadable, corrupt or incompatible archives; queries don't initialize or repair them. `records_unavailable` means the activity exists but has no successfully decoded FIT records; inspect `status`. `invalid_data` means a stored response couldn't be parsed as JSON. `output_error` means the export destination couldn't be written, including when it already exists. CSV requests use the same JSON errors on stderr.

An existing empty archive is valid: `day` returns null metrics with `not_checked`, `trend` reports zero days with values, and `activities` returns `[]`, all with exit `0`. A stored empty health response such as `{}` is also a successful read. A records page beyond the available rows returns an empty list (or just the CSV header). `status` exits `0` when it can read coverage, even if that coverage reports failed syncs; check its `errors`, `fit_errors`, `source_snapshots` and `catch_up` fields. Read success does not establish data completeness or sync success.

Argument-parsing errors use JSON on stderr and exit `2` for every command. Runtime diagnostics from sync, installation and scheduling retain their existing formats; the read/export error contract doesn't change those workflows. In particular, sync may return a JSON report containing partial failures on stdout with a nonzero exit.

**Compatibility:** missing health responses, activities and original files now exit `3` instead of `1`; read/export diagnostics are JSON rather than plain text. Update callers that matched old messages or treated every failure as exit `1`.

`health` without flags preserves raw stored JSON, including retained data after a failed refresh; it is for local inspection, not freshness-aware answers. Prefer structured summaries or `health --metadata`, which adds refresh/fetch context and masks non-ok data. A metadata-aware request for an unchecked date returns a successful envelope with null data, matching MCP `daily_health`. MCP fallback responses now also mask failed retained data; callers can inspect `retained_data_available` and `status`.

`agent-guide` prints installed guidance without opening an archive; optional `--client muse` appends the corresponding `assistant-guide` handoff. `routine-template` emits JSON with an absolute command and provider-neutral instructions; it schedules nothing. `setup-receipt` emits read-only installation/coverage/native-schedule evidence, returning an unavailable archive in its report rather than creating one. Successful receipt output does not mean setup is verified.

## Summaries, units and dates

### Compare periods and summarize workouts

```sh
garmin-archive compare steps --from 2026-01-08 --to 2026-01-14 --baseline-from 2026-01-01 --baseline-to 2026-01-07
garmin-archive activities --from 2026-01-01 --to 2026-01-31 --type running --limit 20
garmin-archive workout-summary --from 2026-01-01 --to 2026-01-31 --type running
```

`compare` / MCP `compare_periods` requires two explicit periods of 1–90 inclusive dates each; the baseline must end before the comparison period starts. It returns both existing trend envelopes (dated points, fetch/attempt times, source units and coverage), plus period-minus-baseline differences between their available-day means. Calculations use unrounded observations and round changes to two decimals. Each period uses its own available-value denominator; unequal lengths, incomplete coverage and periods including today/future dates are flagged. Missing or failed data is never substituted with zero. Percentage changes are null with a reason for zero baselines, missing means, scores, Garmin stress, Body Battery scales/points and percentage-valued metrics. Differences use source units even when the underlying distance trends also contain preferred display units. These descriptive comparisons do not establish causes, significance or a personal baseline.

`activities` / MCP `list_activities` accepts optional inclusive `--from`/`--to` (`start`/`end` in MCP) and `--type` (`activity_type`) filters. Type matches Garmin's native `activityType.typeKey` exactly; `running` does not silently include `trail_running`. Omitted bounds leave that side open. Pagination is applied after filtering. CLI retains its existing bare-list fields; MCP reports refresh status and masks numeric measurements after unsuccessful refreshes. The list includes parent and child activities for inspection.

`workout-summary` / MCP `get_workout_summary` covers 1–90 dates (default: seven ending today), returning distance in meters, Garmin's summary duration in seconds, activity counts, per-field available-activity counts, daily coverage/attempt times and Monday-based weekly buckets clipped to the request. It uses stored search summaries and does not decode laps or infer effort. Source activity dates remain unchanged; today's profile zone is not applied to historical timestamps. Available field totals can be partial; counts disclose missing distance/duration. Known empty/filtered-out available days have zero activity volume; unchecked/failed days remain null. An all-missing measurement is null, not zero. A successful empty search does not prove complete Garmin history.

Parents with stored child activities are excluded from volume totals **before** date/type filtering, including children outside the requested window. Missing children can leave multisport volume incomplete. Other overlapping recordings remain separate: summed duration is not deduplicated elapsed time. The archive retains activity rows rather than tracking deletion history; refreshing cannot establish that every retained row still exists at Garmin. These queries are read-only and need no key or network request.

`day`, `trend` and `sleep` share MCP's query definitions. `sleep` returns all supported sleep fields and source window times together; `chart sleep` renders a branded overview with separate duration/stages and score panels.

The [Personal API coverage guide](API_COVERAGE.md) lists all 26 collected sources and native field access. `api-catalog` needs no archive. `source-data` pages complete native responses, including large arrays; `source-series` preserves native scalar values across dates without inferring an aggregation. These queries share MCP definitions.

The named daily metrics also include calorie totals/active/BMR/consumed, goals, hydration, stress durations, intensity, floors, wheelchair movement, respiration, Pulse Ox and heart-rate extrema. Run `metrics` to discover all names, titles, datasets and units without an archive, or `day DATE` to inspect their dated values and coverage. Existing metrics: `steps`, `distance`, `resting_heart_rate`, `sleep_duration`, `overnight_hrv`, `sleep_score`, `sleep_deep`, `sleep_light`, `sleep_rem`, `sleep_awake`, `sleep_unmeasurable`, `sleep_stress`, `nap_duration`, `sleep_need`, `sleep_need_baseline`, `body_battery_charged`, `body_battery_drained`, `body_battery_min`, `body_battery_max`, `body_battery_first`, `body_battery_last`. See [sleep source definitions and time semantics](SLEEP.md) and [Body Battery aggregation semantics](BODY_BATTERY.md). Sleep-need values use source minutes; stage/nap durations use seconds. Body Battery last/first refer to observed samples, not a live current or bedtime/wake-up level. Trends cover 1–90 inclusive days. Dates must be exactly `YYYY-MM-DD`; `--to` defaults to the Garmin profile's today (host date fallback), and `--from` defaults to six days before that end, even when `--to` is explicit. Supplying only `--from` retains today as the end and can exceed 90 days; supply both bounds for historical questions. There is no CLI time-zone/unit override flag: use explicit dates and convert source units or the returned display units when requested. Results include dated values, units, freshness and missing/failed days. Means use available values only; failed refreshes mask stale values.

Sync saves the Garmin profile's measurement system and time zone. Queries use those defaults; today falls back to the host date if needed. Distance includes a preferred miles/kilometers value alongside source meters. Honor explicit unit requests. Cached preferences may be stale, and the current profile zone doesn't establish an older activity's location or time zone.

For branded PNG trend charts, synthetic demos and the `brand` JSON command, see [Visualizing your archive](VISUALIZATION.md).

For interactive sleep/recovery snapshots, `widget sleep-recovery` exports a
private Muse HTML fragment by default. `--host grok` exports native TSX; add
`--handoff-dir /absolute/new/directory` for bounded create/edit and verification
calls. See the [Muse guide](INTERACTIVE_CHARTS.md#muse-native-widget-trial) and
[Grok guide](GROK_CHARTS.md#bounded-native-delivery). The command prints a JSON
receipt; a saved export still needs the host's native delivery and interaction checks.

## SQL and source data

| Table or view | Contents |
| --- | --- |
| `daily_data` | Complete per-date JSON for all 20 daily Personal API sources |
| `source_snapshots` | Current profile/zones and activity detail/workout JSON, with independent refresh state |
| `activities` | Complete activity search result JSON and original ZIP bytes |
| `activity_messages` | Decoded FIT messages, including unknown fields |
| `activity_records` | Common time-series fields and full decoded JSON |

A null means absent, not zero. Originals survive decoding failures and unsupported formats.

With `sqlite3` installed:

```sh
sqlite3 "$(garmin-archive path)" \
  'SELECT timestamp, heart_rate_bpm, power_w, cadence_rpm FROM activity_records WHERE activity_id = 123456789 ORDER BY record_index LIMIT 20;'
```

Keep the archive in encrypted storage with your own backups. New POSIX files get owner-only permissions; check existing directories and backup permissions too. Keep credentials, archives, raw responses, routes and identifying logs out of Git and public reports.

## Sync and recovery

Completed older days are skipped; recent days and failed requests are retried. `sync --refresh` re-fetches selected health/activity days and retries failed original-file downloads. Successfully decoded files are retained.

Authentication failures, HTTP 429 and repeated network/server errors stop sync. Failed runs exit nonzero without printing Garmin response bodies. Check `status`, resolve the cause and resume. Concurrent syncs to one archive are rejected.

Each selected day requires 20 health calls plus activity pagination. Each run refreshes two current sources; new/recent/refreshed activities also fetch details/workouts, plus original downloads as needed. Backfills can be slow. Garmin controls history and field availability; success or an empty response doesn't establish completeness. The archive retains each day's latest response and each activity's first successfully decoded original, without full edit/deletion history.

## Catch-up and scheduling

Garmin's API is pull-only: devices upload to Connect before the workbench can fetch data.

```sh
garmin-archive sync --catch-up
garmin-archive status
```

For an earlier starting date, add `--from 2026-01-01` on the **first** catch-up only. That anchor is saved even on failure. Later runs cover missed dates from the last successful catch-up and recheck recent days. Failures don't advance the checkpoint; interruptions can leave status at `running` until the next run.

Direct catch-up defaults to seven lookback days; installer-managed jobs default to two. A broken activity file can block completion; inspect `status`, then use `sync --catch-up --refresh` to retry its download and refresh selected days.

### macOS

```sh
garmin-archive setup --every-hours 6 --lookback-days 2
```

Without `--every-hours`, setup asks for an interval. Allowed: 1–168 hours, 1–31 lookback days. Setup changes only its managed job and runs no immediate sync. An MCP assistant can check `setup_status` and call `configure_sync` after you choose an interval.

### Other hosts

Use an OS scheduler or persistent provider routine to run:

```sh
/absolute/path/to/garmin-archive --data-dir /absolute/private/archive sync --catch-up --lookback-days 2
```

For example, after a first sync, add a daily job with `crontab -e` if cron is available:

```cron
15 6 * * * umask 077; "$HOME/.local/bin/garmin-archive" sync --catch-up >> "$HOME/.local/share/garmin-extraction/sync.log" 2>&1
```

Adjust executable, archive and log paths for your installation. Use the same OS user and persistent key. On Windows, Task Scheduler can invoke the installed executable with `sync --catch-up`. If cron/systemd is unavailable, the provider must supply the routine; the workbench doesn't create or monitor it.

### Verify recurring sync

Check for duplicate jobs, protect logs and verify an actual execution and archive status. The job needs the same storage and key after restarts. Sleeping/offline hosts may update later. More frequent syncs and longer lookbacks make more requests; uploads outside the lookback may need a manual refresh. Garmin's exact quota isn't published, and catch-up can't guarantee historical data.

Summary and native-query envelopes include `archive_provenance`. Explicit synthetic provenance (or a legacy `SYNTHETIC.txt` marker) labels charts automatically. Unmarked provenance is unknown; fetch timestamps do not prove live Garmin freshness for synthetic data. Legacy bare-list activity/record exports retain their existing format.

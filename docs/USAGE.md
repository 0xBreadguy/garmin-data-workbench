# Use your archive

[Setup](SETUP.md) · [Assistants](ASSISTANTS.md) · [Commands](#commands) · [SQL](#sql-and-source-data) · [Scheduling](#catch-up-and-scheduling)

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

# Replace the example ID with one from your activity list.
garmin-archive records 123456789 --limit 100
garmin-archive records 123456789 --format csv --limit 1000 > activity.csv
garmin-archive health sleep 2026-01-01
garmin-archive export-original 123456789 activity.zip
```

Use `--offset` to page through activities or records. `records --full` includes all decoded fields and may expose precise coordinates.

Put `--data-dir /absolute/private/archive` before the command to choose an archive. The database is `archive.sqlite3`; the default directory is `~/.local/share/garmin-extraction` or an absolute `$XDG_DATA_HOME/garmin-extraction`. Command and directory names are unchanged from the project's original name.

## Summaries, units and dates

`day` and `trend` share MCP's query definitions. They read an existing archive without creating, migrating or syncing it and need no Garmin key.

Supported metrics: `steps`, `distance`, `resting_heart_rate`, `sleep_duration`, `overnight_hrv`. Trends cover 1–90 inclusive days; omitted dates select seven days ending today. Results include dated values, units, freshness and missing/failed days. Means use available values only; failed refreshes mask stale values.

Sync saves the Garmin profile's measurement system and time zone. Queries use those defaults; today falls back to the host date if needed. Distance includes a preferred miles/kilometers value alongside source meters. Honor explicit unit requests. Cached preferences may be stale, and the current profile zone doesn't establish an older activity's location or time zone.

## SQL and source data

| Table or view | Contents |
| --- | --- |
| `daily_data` | Latest per-date JSON: daily summary, sleep, HRV, heart rate, Body Battery |
| `activities` | Activity metadata and original ZIP bytes |
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

Each selected day requires five health calls plus activity pagination and original downloads. Backfills can be slow. Garmin controls history and field availability; success or an empty response doesn't establish completeness. The archive retains each day's latest response and each activity's first successfully decoded original, without full edit/deletion history.

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

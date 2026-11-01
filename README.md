<img src="assets/icon.svg" width="64" height="64" alt="">

# Garmin Data Workbench

**Your Garmin data, ready for your own tools.**

Garmin Data Workbench is a community-built, local-first tool for downloading, owning and querying your Garmin health and activity data. Bring your own Garmin Personal API key and explore your SQLite archive with SQL, scripts and notebooks. An MCP interface and automatic scheduling are planned but are not implemented yet.

This is an independent open-source project. It is not affiliated with, endorsed by, or supported by Garmin.

See the [product brief](PRODUCT_BRIEF.md) for the proposed experience, the [existing-projects review](EXISTING_PROJECTS.md) for competitive context, and the [data extraction plan](GARMIN_DATA_PLAN.md) for sources, architecture, privacy boundaries, implementation phases, and release requirements.

## Contributing

We welcome bug reports, ideas, documentation improvements, and code from people who want more control over their Garmin data. See [CONTRIBUTING.md](CONTRIBUTING.md) for how to get started and how to share useful examples without exposing personal data.

## Personal API setup

1. Install Python 3.12 or later and [uv](https://docs.astral.sh/uv/).
2. Clone this repository and run `uv sync` from its directory to install Garmin's official client and FIT decoder.
3. Sign in to [Garmin Connect's Personal API key page](https://connect.garmin.com/app/settings/personalApiToken). Create your own key after reviewing Garmin's terms, choose its expiration, and save it securely. Garmin shows the key only once.
4. Store the key in a local secret store, or in the official client's default file `~/.config/garmin/connect-personal-api-key` with permissions restricted to your user (`0600`). The file must contain only the key. Never put a key or bearer-token cache in this repository or shell history.
5. Run `uv run python scripts/check_connection.py`. It checks authentication, profile settings, and an activity search without displaying the returned personal data. Garmin's client stores its bearer-token cache under `~/.config/garmin/`; protect this file too.

Your Garmin devices must sync to Garmin Connect before their data can be read. See [Garmin's key and token FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/).

## Sync and query

```sh
# The past seven days, including today; the data directory defaults to
# ~/.local/share/garmin-extraction (or $XDG_DATA_HOME/garmin-extraction).
uv run garmin-archive sync

# Choose an inclusive range. Backfills issue several requests per day.
uv run garmin-archive sync --from 2026-01-01 --to 2026-01-07

# Inspect coverage, errors, available activities and the database path.
uv run garmin-archive status
uv run garmin-archive activities
uv run garmin-archive path

# Inspect one activity's recorded samples. Substitute an ID from activities.
uv run garmin-archive records 123456789 --limit 100
uv run garmin-archive records 123456789 --format csv --limit 1000 > activity.csv

# Complete decoded records can include precise coordinates.
uv run garmin-archive records 123456789 --full --limit 100

# Fetch the stored response for a day, or export an original activity ZIP.
uv run garmin-archive health sleep 2026-01-01
uv run garmin-archive export-original 123456789 activity.zip
```

Pass `--data-dir /path/to/private/directory` **before** the command to use another location. The tool creates `archive.sqlite3` in that directory; the default location is outside the repository. Choose an encrypted location and back it up using your own backup system. The tool creates new files with owner-only permissions on POSIX systems; review the permissions of any existing directories and backups.

The `garmin-archive` command and `garmin-extraction` data-directory name remain unchanged from the project's initial setup, so existing archives continue to work after the rename.

Older days with successful or empty results are skipped on subsequent runs; the most recent seven days are rechecked for late syncs. Failed days are retried. Use `sync --refresh` to re-fetch the selected health/activity days and retry failed activity-file downloads. Activity files previously decoded successfully are retained rather than re-downloaded. HTTP 429, authentication failures and repeated network/server errors stop the run so it can be resumed later. A failed sync exits nonzero and reports the affected dataset without printing Garmin response bodies.

The `daily_data` table stores the latest JSON response per requested date for daily summaries, sleep, HRV, all-day heart rate and Body Battery. `activities` stores activity metadata and original ZIP bytes; `activity_messages` retains decoded FIT messages as JSON, including fields the current SDK does not name. `activity_records` is a convenience view with common time-series fields and the full decoded JSON. Null means the field was not present, not zero. The original ZIP is retained even if FIT decoding fails or the original is a different format.

For example, using the `sqlite3` command installed on your machine:

```sh
sqlite3 "$(uv run garmin-archive path)" \
  'SELECT timestamp, heart_rate_bpm, power_w, cadence_rpm FROM activity_records WHERE activity_id = 123456789 ORDER BY record_index LIMIT 20;'
```

### Current limits

- Sync is manually invoked; no background scheduler or MCP server is installed.
- A selected range fetches five health endpoints and activity pages per day, then downloads original files. Historical coverage depends on Garmin and the account; this is not a guarantee of complete history or every Garmin metric.
- The archive keeps the latest response for each day and the first successfully decoded original per activity; it does not currently retain previous revisions or detect every activity edit/deletion. Use Garmin's account export as an independent backup.
- Avoid running two syncs against the same archive at the same time. Precise location can be present in the original files and `--full` output.
- No Garmin data, tokens or database files belong in the repository. Review all files and history before sharing or changing repository visibility.

## Development

```sh
uv sync
uv run python -m unittest discover -s tests -v
```

The tests use generated FIT data and fake API responses; they do not need Garmin credentials or network access.

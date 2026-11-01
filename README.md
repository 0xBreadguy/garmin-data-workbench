# Garmin Data Workbench

```text
  G A R M I N   D A T A

  __      _____  ___ _  _____ ___ _  _  ___ _  _
  \ \    / / _ \| _ \ |/ / _ ) __| \| |/ __| || |
   \ \/\/ / (_) |   / ' <| _ \ _|| .` | (__| __ |
    \_/\_/ \___/|_|_\_|\_\___/___|_|\_|\___|_||_|
```

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-4B6F92?style=flat-square)](https://www.python.org/)
[![SQLite archive](https://img.shields.io/badge/archive-SQLite-5C7D70?style=flat-square)](https://www.sqlite.org/)
[![Local first](https://img.shields.io/badge/data-local--first-5C7D70?style=flat-square)](#sync-and-query)
[![MIT license](https://img.shields.io/badge/license-MIT-777777?style=flat-square)](LICENSE)

**Your Garmin data, on your machine, ready for your agent.**

Your Garmin devices collect a lot of data. This project gives you a way to keep a copy on your own machine and work with it using the tools you already like.

Bring your own Garmin Personal API key, sync your health data and activities, and ask your MCP-compatible assistant about the local archive. You can also query it with SQL, scripts, or notebooks. Original activity files are kept alongside the decoded records, so you can go back to the source when you need to.

- **Sync** your health data and activities to a local archive.
- **Explore** the detailed records in your activity FIT files.
- **Query** your data with SQL, JSON, CSV, or your own scripts.
- **Connect an assistant** to the local archive through MCP; data tools are read-only, and setup can configure local sync.
- **Build with us** if there's something you'd like to improve.

We're early. Run sync yourself or schedule catch-up with your operating system, then connect a local MCP client to the archive.

[Get started](#personal-api-setup) · [Explore the commands](#sync-and-query) · [Contribute](CONTRIBUTING.md)

Garmin Data Workbench is an independent open-source project. It isn't affiliated with, endorsed by, or supported by Garmin.

Want more context? The [product brief](PRODUCT_BRIEF.md) covers where we'd like to take the project, the [existing-projects review](EXISTING_PROJECTS.md) looks at related tools, and the [architecture notes](ARCHITECTURE.md) explain the storage and performance choices.

## Personal API setup

1. Install Python 3.12 or later and [uv](https://docs.astral.sh/uv/).
2. Clone this repository, then run `uv sync` inside it. This installs Garmin's official client and FIT decoder.
3. Sign in to [Garmin Connect's Personal API key page](https://connect.garmin.com/app/settings/personalApiToken). Review Garmin's terms, choose an expiration, and create your key. Garmin only shows it once, so save it somewhere secure.
4. Put the key in `~/.config/garmin/connect-personal-api-key` and restrict the file to your user (`0600`). The file should contain only the key. Garmin's client can also read it from the `GARMIN_PERSONAL_API_KEY` environment variable. Keep the key and bearer-token cache out of this repository and your shell history.
5. Run `uv run python scripts/check_connection.py` to check authentication and make a couple of read requests. The check won't print your personal data. Garmin's client stores its bearer-token cache under `~/.config/garmin/`, so protect that file too.

Your devices need to sync with Garmin Connect before the API can read their data. Garmin's [key and token FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/) has more detail on expiration and revocation.

## Sync and query

```sh
# Sync the past seven days, including today. Data is stored in
# ~/.local/share/garmin-extraction (or $XDG_DATA_HOME/garmin-extraction).
uv run garmin-archive sync

# Or choose a date range (both dates are included).
# Backfills make several requests per day.
uv run garmin-archive sync --from 2026-01-01 --to 2026-01-07

# Check coverage and errors, list activities, or find the database.
uv run garmin-archive status
uv run garmin-archive activities
uv run garmin-archive path

# Look at an activity's samples. Replace the example ID with one from your list.
uv run garmin-archive records 123456789 --limit 100
uv run garmin-archive records 123456789 --format csv --limit 1000 > activity.csv

# Get all decoded fields (these can include precise coordinates).
uv run garmin-archive records 123456789 --full --limit 100

# Read a stored health response or export an original activity ZIP.
uv run garmin-archive health sleep 2026-01-01
uv run garmin-archive export-original 123456789 activity.zip
```

Want to store the archive somewhere else? Pass `--data-dir /path/to/private/directory` **before** the command. The tool creates `archive.sqlite3` there. By default, it lives outside the repository.

Choose an encrypted location and include it in your own backups. New files get owner-only permissions on POSIX systems; check the permissions of any existing directories and backups too. The command and data-directory names haven't changed since the project's initial setup, so existing archives still work after the rename.

On later runs, completed older days are skipped, and the most recent seven days are checked again for late syncs. Failed days are retried. Use `sync --refresh` to fetch the selected health and activity days again and retry failed activity-file downloads. Files that decoded successfully are kept rather than downloaded again.

If Garmin returns HTTP 429, authentication fails, or network/server errors keep happening, the sync stops so you can resume it later. A failed run exits nonzero and reports which dataset was affected without printing Garmin's response bodies.

The `daily_data` table stores the latest JSON response for each requested date: daily summaries, sleep, HRV, all-day heart rate and Body Battery. The `activities` table holds activity metadata and original ZIP bytes. Decoded FIT messages live in `activity_messages`, including fields the current SDK doesn't name.

For common time-series fields, use the `activity_records` view. It also includes the full decoded JSON. A null means the field wasn't present, not that it was zero. The original ZIP stays in the archive even if decoding fails or the original is a different format.

For example, with `sqlite3` installed on your machine:

```sh
sqlite3 "$(uv run garmin-archive path)" \
  'SELECT timestamp, heart_rate_bpm, power_w, cadence_rpm FROM activity_records WHERE activity_id = 123456789 ORDER BY record_index LIMIT 20;'
```

### Schedule catch-up

Garmin's Personal API is pull-only: the watch first uploads to Garmin Connect, then this tool fetches from Connect. Start the recurring series with one manual run:

```sh
uv run garmin-archive sync --catch-up
# To choose an earlier starting date, use --from on the first catch-up run only:
# uv run garmin-archive sync --catch-up --from 2026-01-01
uv run garmin-archive status
```

The first run saves its starting date even if it fails. Later runs revisit the last seven days and include days since the last fully successful catch-up; completed older days are skipped. A failure or interruption doesn't advance the checkpoint. An interrupted run can remain marked `running` in status until the next run. A broken activity file can keep a run from completing; inspect `status` and use `sync --catch-up --refresh` to retry its download. `--refresh` also re-fetches the selected days. Large missed ranges can take a long time and make many requests. Garmin may return empty or incomplete historical responses, so a successful run is not proof of complete history.

On macOS, `uv run garmin-archive setup` asks how many hours should pass between updates, then installs a per-user schedule. The default is every six hours, rechecking the most recent two days for late uploads. Set the values explicitly or change them later:

```sh
uv run garmin-archive setup --every-hours 6 --lookback-days 2
```

Intervals range from 1 to 168 hours and lookback from 1 to 31 days. More frequent syncs and longer lookback windows make more Garmin requests; the exact quota is not published. Two days is a practical starting point, not a guarantee: uploads arriving later may need a longer lookback or a manual refresh. Missed scheduled runs are covered from the last successful catch-up, subject to Garmin returning the historical data. The tool only changes its own managed schedule. Check for separately configured cron or launchd jobs to avoid duplicate syncs. A machine that is off or asleep may update later.

In an MCP client, ask the assistant to configure or change the sync frequency. It can check `setup_status` and call `configure_sync` after you choose an interval; that tool changes the local schedule and doesn't run a sync immediately. MCP clients differ, so an assistant's setup question may appear in conversation rather than automatically when the server connects.

For example, on macOS or Linux, add a daily job with `crontab -e` after the first run. Replace the path with the absolute path to this checkout (use a stable location, not a temporary worktree):

```cron
15 6 * * * umask 077; "/absolute/path/to/garmin-data-workbench/.venv/bin/garmin-archive" sync --catch-up >> "$HOME/.local/share/garmin-extraction/sync.log" 2>&1
```

Use the same user account and key file as the manual run. The default log directory is created by that first run; if using `--data-dir` or `XDG_DATA_HOME`, adjust both the command and log path. Review the log and `status` for failures. Cron won't run while the machine is off or asleep; catch-up runs when the next scheduled job actually runs. On macOS, launchd is another option; on Windows use Task Scheduler to run the installed `garmin-archive` executable with `sync --catch-up`. Scheduling is opt-in and must be configured and monitored by the user.

### Connect a local assistant

After `uv sync` and at least one archive sync, configure your MCP client to launch the server over stdio. For clients accepting `mcpServers` JSON, use the absolute path to this checkout's executable:

```json
{
  "mcpServers": {
    "garmin-workbench": {
      "command": "/absolute/path/to/garmin-data-workbench/.venv/bin/garmin-archive-mcp",
      "args": []
    }
  }
}
```

For a custom archive, set `args` to `["--data-dir", "/absolute/path/to/archive-directory"]`. Data tools open the existing database read-only; they do not sync or need a Garmin key. The separate `configure_sync` tool can install or update a local macOS schedule when requested. Data tools return a day overview, up to 90 days of metric trends, coverage, activities, daily responses and paginated FIT records. `get_day` and `get_trend` currently support steps, distance, resting heart rate, sleep duration and overnight HRV when Garmin returns the expected fields. Every trend includes dated points, units and missing or failed days; its mean uses only available values. A failed refresh never passes an old value off as current. You can ask your assistant to chart the returned points if it supports visualizations. Samples omit coordinates and raw fields. Daily responses and activity names can still contain sensitive information. Returned data may be sent to the AI provider selected in your client, even though the server runs locally. Individual client setup still needs a full conversational test.

For Codex CLI, a stable local tool install avoids pointing the configuration at a temporary checkout:

```sh
uv tool install --from . garmin-data-workbench
codex mcp add garmin-workbench -- "$HOME/.local/bin/garmin-archive-mcp"
codex mcp get garmin-workbench
```

Start a fresh Codex session after registering the server. Try “How did my sleep and resting heart rate change over the last week?” Each sync reads the Garmin profile's measurement system and time zone and keeps just those preferences locally. They are the defaults, so setup does not ask for them. Dates default to the Garmin profile time zone, with the host's local date as a fallback if it is unavailable. Distance summaries include a preferred miles or kilometers value alongside the unchanged meters; agents can use the preference for other presentation or honor your explicit request for different units. Settings can be stale if Garmin is unavailable. Activity timestamps retain their original meaning; the current profile time zone is not necessarily the zone where an older activity occurred. A local tool installation is a snapshot; after updating the workbench, reinstall it with `uv tool install --force --no-cache --from . garmin-data-workbench`. The CLI/IDE configuration is shared by Codex; other hosts may load MCP configuration differently.

### Current limits

- Guided scheduling is currently available on macOS; use your OS scheduler on other platforms. A first-party dashboard is not a current goal.
- Trend metrics are limited to five fields; richer comparisons and activity analysis are planned. A raw daily response larger than 64 KB is rejected by MCP; use the local `health` command to inspect it. The field shapes were checked against one account's seven-day archive, but the actual values still need comparison with Garmin Connect and a named assistant setup needs a full conversational test.
- Each day in a selected range means five health requests and activity pages, followed by original-file downloads. What's available depends on Garmin and your account, so we can't promise complete history or every metric.
- The archive keeps the latest response for each day and the first successfully decoded original for each activity. It doesn't keep earlier revisions or catch every activity edit or deletion yet. Garmin's account export is a separate backup you can keep.
- The CLI rejects concurrent syncs to the same archive. Original files and `--full` output can contain precise location data.
- Keep Garmin data, tokens, and database files out of the repository. Check the files and history before sharing it or changing its visibility.

## Development

```sh
uv sync
uv run python -m unittest discover -s tests -v
```

The tests use generated FIT data and fake API responses. You don't need Garmin credentials or network access to run them.

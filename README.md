```text
  G A R M I N   D A T A

  __      _____  ___ _  _____ ___ _  _  ___ _  _
  \ \    / / _ \| _ \ |/ / _ ) __| \| |/ __| || |
   \ \/\/ / (_) |   / ' <| _ \ _|| .` | (__| __ |
    \_/\_/ \___/|_|_\_|\_\___/___|_|\_|\___|_||_|
```

# Garmin Data Workbench

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

We're early. The guided installer connects Codex and can schedule sync on macOS; other clients and operating systems have additional steps below.

[Get started](#personal-api-setup) · [Explore the commands](#sync-and-query) · [Contribute](CONTRIBUTING.md)

**Setting up with an assistant?** Give it this repository and ask: “Read `AGENTS.md`, then help me follow `docs/SETUP.md` on the machine I choose.” The [setup guide](docs/SETUP.md) covers local and persistent cloud hosts, private key entry, client connections and scheduling. You choose where the archive lives and who can access it. For coding agents, [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) provide the source map and offline development path.

Garmin Data Workbench is an independent open-source project. It isn't affiliated with, endorsed by, or supported by Garmin.

Want more context? The [product brief](PRODUCT_BRIEF.md) covers where we'd like to take the project, the [existing-projects review](EXISTING_PROJECTS.md) looks at related tools, and the [architecture notes](ARCHITECTURE.md) explain the storage and performance choices.

## Personal API setup

1. Install Python 3.12 or later, [uv](https://docs.astral.sh/uv/), and the [Codex CLI](https://learn.chatgpt.com/docs/cli) if you want the automatic Codex connection.
2. Clone this repository and install the tool from its directory:

   ```sh
   git clone https://github.com/0xBreadguy/garmin-data-workbench.git
   cd garmin-data-workbench
   uv tool install --from . garmin-data-workbench
   ```

   If the command isn't found afterward, follow uv's instructions for adding its tool bin directory to your `PATH`.

3. Sign in to [Garmin Connect's Personal API key page](https://connect.garmin.com/app/settings/personalApiToken). Review Garmin's terms, choose an expiration, and create your key. Garmin only shows it once, so keep it somewhere secure.
4. Run the guided installer in your terminal:

   ```sh
   garmin-archive install
   ```

   First choose how often to update: press Enter for six hours, enter another number of hours, or enter `0` for manual sync. If you haven't saved a Garmin key, paste it into the hidden terminal prompt; don't give it to an AI assistant. The installer checks the key and saves it to `~/.config/garmin/connect-personal-api-key` with owner-only permissions.

   Next it syncs the archive (seven days on the first run), installs the selected macOS schedule, and registers and checks the MCP server in Codex. Start a new Codex conversation to ask about your data. Existing Codex configuration is preserved; if it points to a different archive, check it with `codex mcp get garmin-workbench`.

   For noninteractive use, pass `--every-hours 6` or `--manual`. Use `--client claude` for Claude Code, or `--client chatgpt` / `--client other` for the additional client steps described below. The default is `--client codex`. ChatGPT and other clients return exit code `2` after local setup to indicate that the client connection is still pending. On non-macOS systems use `--manual` and your operating system's scheduler. Manual setup leaves existing schedules unchanged.

Garmin's client also reads `GARMIN_PERSONAL_API_KEY` from the environment. A macOS scheduled job doesn't inherit your terminal's environment; if you use a shell-only key, save the same key in the file above with owner-only permissions before enabling the schedule. The client stores a bearer-token cache under `~/.config/garmin/` as well. Keep the key and token cache out of the repository and your shell history.

Your devices need to sync with Garmin Connect before the API can read their data. Garmin's [key and token FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/) has more detail on expiration and revocation.

## Sync and query

```sh
# Sync the past seven days, including today. Data is stored in
# ~/.local/share/garmin-extraction (or $XDG_DATA_HOME/garmin-extraction).
garmin-archive sync

# Or choose a date range (both dates are included).
# Backfills make several requests per day.
garmin-archive sync --from 2026-01-01 --to 2026-01-07

# Check coverage and errors, list activities, or find the database.
garmin-archive status
garmin-archive activities
garmin-archive path

# Read the same bounded summaries used by MCP, without a live request.
garmin-archive day 2026-01-01
garmin-archive trend sleep_duration --from 2026-01-01 --to 2026-01-07

# Look at an activity's samples. Replace the example ID with one from your list.
garmin-archive records 123456789 --limit 100
garmin-archive records 123456789 --format csv --limit 1000 > activity.csv

# Get all decoded fields (these can include precise coordinates).
garmin-archive records 123456789 --full --limit 100

# Read a stored health response or export an original activity ZIP.
garmin-archive health sleep 2026-01-01
garmin-archive export-original 123456789 activity.zip
```

Want to store the archive somewhere else? Pass `--data-dir /path/to/private/directory` **before** the command. The tool creates `archive.sqlite3` there. By default, it lives outside the repository.

Choose an encrypted location and include it in your own backups. New files get owner-only permissions on POSIX systems; check the permissions of any existing directories and backups too. The command and data-directory names haven't changed since the project's initial setup, so existing archives still work after the rename.

On later runs, completed older days are skipped, and the most recent seven days are checked again for late syncs. Failed days are retried. Use `sync --refresh` to fetch the selected health and activity days again and retry failed activity-file downloads. Files that decoded successfully are kept rather than downloaded again.

If Garmin returns HTTP 429, authentication fails, or network/server errors keep happening, the sync stops so you can resume it later. A failed run exits nonzero and reports which dataset was affected without printing Garmin's response bodies.

The `daily_data` table stores the latest JSON response for each requested date: daily summaries, sleep, HRV, all-day heart rate and Body Battery. The `activities` table holds activity metadata and original ZIP bytes. Decoded FIT messages live in `activity_messages`, including fields the current SDK doesn't name.

For common time-series fields, use the `activity_records` view. It also includes the full decoded JSON. A null means the field wasn't present, not that it was zero. The original ZIP stays in the archive even if decoding fails or the original is a different format.

For example, with `sqlite3` installed on your machine:

```sh
sqlite3 "$(garmin-archive path)" \
  'SELECT timestamp, heart_rate_bpm, power_w, cadence_rpm FROM activity_records WHERE activity_id = 123456789 ORDER BY record_index LIMIT 20;'
```

### Schedule catch-up

Garmin's Personal API is pull-only: the watch first uploads to Garmin Connect, then this tool fetches from Connect. The installer starts catch-up and configures the schedule you selected on macOS. To start or inspect catch-up manually:

```sh
garmin-archive sync --catch-up
# To choose an earlier starting date, use --from on the first catch-up run only:
# garmin-archive sync --catch-up --from 2026-01-01
garmin-archive status
```

The first run saves its starting date even if it fails. Later runs include days since the last fully successful catch-up and revisit a recent window for late uploads; `sync --catch-up` defaults to seven days, while the installer defaults to two days for scheduled runs. Completed older days are skipped. A failure or interruption doesn't advance the checkpoint. An interrupted run can remain marked `running` in status until the next run. A broken activity file can keep a run from completing; inspect `status` and use `sync --catch-up --refresh` to retry its download. `--refresh` also re-fetches the selected days. Large missed ranges can take a long time and make many requests. Garmin may return empty or incomplete historical responses, so a successful run is not proof of complete history.

On macOS, `garmin-archive setup` asks how many hours should pass between updates, then installs or updates a per-user schedule. The default is every six hours, rechecking the most recent two days for late uploads. Set the values explicitly or change them later:

```sh
garmin-archive setup --every-hours 6 --lookback-days 2
```

Intervals range from 1 to 168 hours and lookback from 1 to 31 days. More frequent syncs and longer lookback windows make more Garmin requests; the exact quota is not published. Two days is a practical starting point, not a guarantee: uploads arriving later may need a longer lookback or a manual refresh. Missed scheduled runs are covered from the last successful catch-up, subject to Garmin returning the historical data. The tool only changes its own managed schedule. Check for separately configured cron or launchd jobs to avoid duplicate syncs. A machine that is off or asleep may update later.

In an MCP client, ask the assistant to configure or change the sync frequency. It can check `setup_status` and call `configure_sync` after you choose an interval; that tool changes the local schedule and doesn't run a sync immediately. MCP clients differ, so an assistant's setup question may appear in conversation rather than automatically when the server connects.

For example, on macOS or Linux, add a daily job with `crontab -e` after the first run. Replace the executable path if uv installed it elsewhere:

```cron
15 6 * * * umask 077; "$HOME/.local/bin/garmin-archive" sync --catch-up >> "$HOME/.local/share/garmin-extraction/sync.log" 2>&1
```

Use the same user account and key file as the manual run. The default log directory is created by that first run; if using `--data-dir` or `XDG_DATA_HOME`, adjust both the command and log path. Review the log and `status` for failures. Cron won't run while the machine is off or asleep; catch-up runs when the next scheduled job actually runs. On macOS, launchd is another option; on Windows use Task Scheduler to run the installed `garmin-archive` executable with `sync --catch-up`. Scheduling is opt-in and must be configured and monitored by the user.

### Cloud assistant machines

You can also install the workbench on a cloud machine used by an assistant, if its storage persists and you are comfortable storing your Garmin data there. **Other agents or processes running as the same operating-system user can read the key, token cache, and archive**, even when files have owner-only permissions. Original activity files may contain precise GPS locations. Ask your provider about isolation, storage, backups, and who can access the machine before deciding whether to sync. MCP responses may also be sent to the assistant's AI provider.

On Linux, use `garmin-archive install --manual --client other` for guided setup. It needs a Garmin key and starts a sync immediately; it exits with code 2 because connecting the client is a separate step. Supply the key through a secure mechanism supported by your environment, not through a conversation or command history. Verify that the key is available to any future sync process without exposing it in logs.

If cron or systemd is unavailable, a persistent provider-managed routine can run `garmin-archive sync --catch-up` at an interval you choose, provided it can access the same installation, archive, and key. Test one short sync and inspect `garmin-archive status` before scheduling. Check that the routine survives restarts and review failures. The workbench does not create or monitor provider-managed routines.

An assistant on the same machine can connect to the stdio MCP server if its environment supports local MCP clients. Remote access requires a separately secured connection; this project does not currently provide an authenticated remote connector.

### Connect a local assistant

The installer connects one client. To connect another later without resyncing or changing the schedule, run:

```sh
garmin-archive connect --client codex
garmin-archive connect --client claude
```

Codex registration is checked using a fresh local runtime. Claude Code registration uses its user scope; start a new Claude Code session, check `/mcp`, and make a real query to verify it. Neither command replaces an existing server with the same name; inspect it with `codex mcp get garmin-workbench` or `claude mcp get garmin-workbench` if it points elsewhere. These are separate configurations; registering one doesn't register the other.

For other local MCP clients, configure the server over stdio. For clients accepting `mcpServers` JSON, replace the example with the absolute path to your installed executable:

```json
{
  "mcpServers": {
    "garmin-workbench": {
      "command": "/absolute/path/to/garmin-archive-mcp",
      "args": []
    }
  }
}
```

For a custom archive, set `args` to `["--data-dir", "/absolute/path/to/archive-directory"]`. Data tools open the existing database read-only; they do not sync or need a Garmin key. The separate `configure_sync` tool can install or update a local macOS schedule when requested. Data tools return a day overview, up to 90 days of metric trends, coverage, activities, daily responses and paginated FIT records. `get_day` and `get_trend` currently support steps, distance, resting heart rate, sleep duration and overnight HRV when Garmin returns the expected fields. Every trend includes dated points, units and missing or failed days; its mean uses only available values. A failed refresh never passes an old value off as current. You can ask your assistant to chart the returned points if it supports visualizations. Samples omit coordinates and raw fields. Daily responses and activity names can still contain sensitive information. Returned data may be sent to the AI provider selected in your client, even though the server runs locally. Individual client setup still needs a full conversational test.

Try asking “How did my sleep and resting heart rate change over the last week?” Each sync reads the Garmin profile's measurement system and time zone and keeps just those preferences locally. They are the defaults, so setup does not ask for them. Dates default to the Garmin profile time zone, with the host's local date as a fallback if it is unavailable. Distance summaries include a preferred miles or kilometers value alongside the unchanged meters; agents can use the preference for other presentation or honor your explicit request for different units. Settings can be stale if Garmin is unavailable. Activity timestamps retain their original meaning; the current profile time zone is not necessarily the zone where an older activity occurred. A local tool installation is a snapshot; after updating the workbench, reinstall it with `uv tool install --force --no-cache --from . garmin-data-workbench`.

### Personal assistants and ChatGPT

A personal assistant may coordinate from the cloud even when it can reach your computer. It needs to know **which computer** has the archive and how to use its local agent. On the machine with the archive, run:

```sh
garmin-archive assistant-guide --client dot
```

Copy the result into your dot's conversation and ask it to remember the handoff. Check that the computer name matches the one your dot can reach, especially if you have more than one connected computer. The handoff asks the dot to use a local Codex task and the Garmin MCP tools. [OpenAI documents connecting a computer and starting local tasks](https://learn.chatgpt.com/docs/dots/computers-and-apps); this particular Garmin handoff has not yet been tested end to end. The computer must be online and connected, and Codex must already be registered there. `--client codex`, `--client claude`, and `--client other` print shorter handoffs for those contexts.

Direct MCP access from a regular ChatGPT conversation is separate from Codex configuration. One documented route is OpenAI's [Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels): create a tunnel associated with your ChatGPT workspace, run OpenAI's `tunnel-client` on the archive machine pointing at `garmin-archive-mcp`, then add it as a custom MCP server in ChatGPT. The tunnel client must remain running. This project does not configure or verify that connection yet; account and workspace permissions apply. MCP responses pass through the selected AI provider.

Claude Duet and Meta Muse also run in their own environments, so a Claude Code or Codex registration on your computer doesn't by itself prove those assistants can reach your archive. Assistants with shell access on the archive host can use the read-only `day` and `trend` CLI commands without MCP. `garmin-archive assistant-guide --client muse` prints that same-host handoff; [Muse compatibility notes](docs/MUSE.md) cover the reported headless Linux environment and remaining checks. Direct Duet and Muse MCP integrations are not implemented here.

### Current limits

- Guided scheduling is currently available on macOS; use your OS scheduler on other platforms. A first-party dashboard is not a current goal.
- Trend metrics are limited to five fields; richer comparisons and activity analysis are planned. A raw daily response larger than 64 KB is rejected by MCP; use the local `health` command to inspect it. The field shapes were checked against one account's seven-day archive, but the actual values still need comparison with Garmin Connect. One local Codex conversation has successfully used the MCP; other assistant handoffs still need end-to-end tests.
- Each day in a selected range means five health requests and activity pages, followed by original-file downloads. What's available depends on Garmin and your account, so we can't promise complete history or every metric.
- The archive keeps the latest response for each day and the first successfully decoded original for each activity. It doesn't keep earlier revisions or catch every activity edit or deletion yet. Garmin's account export is a separate backup you can keep.
- The CLI rejects concurrent syncs to the same archive. Original files and `--full` output can contain precise location data.
- Keep Garmin data, tokens, and database files out of the repository. Check the files and history before sharing it or changing its visibility.

## Development

```sh
uv sync --locked
uv run python -m unittest discover -s tests -v
```

The tests use generated FIT data and fake API responses. You don't need Garmin credentials or network access to run them.

See [AGENTS.md](AGENTS.md) for agent instructions, [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow, and [docs/TESTING.md](docs/TESTING.md) for focused checks and live validation. Dependency installation may require network access; the tests themselves run offline.

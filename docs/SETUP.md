# Set up with an assistant

This is the generic setup path for an assistant on your computer or a persistent cloud machine. It applies to any assistant that can run local commands; MCP access depends on the client's capabilities. If you're changing the code, use the offline [contributor setup](../CONTRIBUTING.md#develop-locally) instead.

## 1. Choose where the data lives

Before installing, establish:

- Which machine will hold the archive, and whether its storage survives restarts and new sessions.
- Whether it has Python 3.12+, uv, and enough storage for the history you intend to keep. Activity originals can grow over time.
- How it accepts secrets without putting them in chat, shell history or logs.
- How the assistant will query it: a local stdio MCP client, local CLI commands, or a separately secured connection to another machine.
- Whether a persistent scheduler is available. Manual sync is a valid starting point.

**Choose the host with its access model in mind.** Other agents or processes running as the same operating-system user can read the key, token cache, archive and original activity files even with owner-only file permissions. Original files can include precise GPS locations. A cloud provider may also control storage and backups. Explain this before a cloud sync and let the user choose; a cloud installation is supported when the user accepts that environment. MCP responses may be sent to the AI provider selected by the client.

Do not copy an existing personal archive or credentials to another host just to test installation. Offline tests and an empty synthetic archive are enough for an initial compatibility check.

## 2. Install the commands

Clone the repository and install from its root:

```sh
git clone https://github.com/0xBreadguy/garmin-data-workbench.git
cd garmin-data-workbench
uv tool install --from . garmin-data-workbench
garmin-archive --help
garmin-archive-mcp --help
```

Run `uv tool dir --bin` to find the executable directory. If the commands aren't on `PATH`, add that directory following uv's guidance. Use absolute executable paths for MCP and scheduled jobs rather than assuming a `/Users/...` or `/home/...` layout. Record the source revision when reporting an install test; a local checkout may have features absent from the default branch. Tool installations are snapshots: after updating the checkout, reinstall with `uv tool install --force --no-cache --from . garmin-data-workbench`.

## 3. Supply a key and run a first sync

The user creates their own Garmin Personal API key using the [README's instructions](../README.md#personal-api-setup). Use a hidden terminal prompt or a supported masked secret field. Never paste the key into a conversation or put its value in a shell command.

The Garmin client accepts `GARMIN_PERSONAL_API_KEY` or a key file at `~/.config/garmin/connect-personal-api-key`. Ensure any saved key file is owner-only (`0600` on POSIX) and outside the repository. The provider's secret facility must make the key available to future sync processes if you rely on the environment variable. A scheduled job does not necessarily inherit the interactive environment.

Choose one path:

- **Guided macOS setup:** `garmin-archive install` asks for an update interval, privately prompts for a missing key, syncs, configures the selected schedule, then connects Codex by default. Use `--client claude` for Claude Code. It makes live Garmin requests and changes local configuration.
- **Generic setup on Linux or another host:** `garmin-archive install --manual --client other` syncs and prints the local MCP launch command. It creates no schedule and leaves any existing one in place. Exit code `2` means client connection is still pending, rather than proving the sync failed; read the preceding output. The default first sync covers seven days.
- **A short live test first:** with a key already available, use `garmin-archive sync --from YYYY-MM-DD --to YYYY-MM-DD`, replacing both placeholders with the same user-selected day. This avoids client and scheduler changes. A later guided install can request its default seven-day range; use `connect` instead if you only need to connect the client afterward.

For a custom archive, put `--data-dir /absolute/private/archive` before the command and use that same path in every later CLI, MCP and scheduled command. The default archive is outside the checkout, under `~/.local/share/garmin-extraction` or an absolute `XDG_DATA_HOME`.

After a sync, inspect `garmin-archive status` and `garmin-archive activities` locally. CLI commands such as `status` and `path` initialize the directory and database if missing; an empty result does not prove a sync took place. A completed request also doesn't guarantee Garmin returned complete history. Devices must upload to Garmin Connect first.

## 4. Connect and test the assistant

For a local client that accepts `mcpServers` configuration:

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

Replace the command with the installed executable's absolute path. For a custom archive, set `args` to `["--data-dir", "/absolute/private/archive"]`. The archive must already exist; MCP data queries do not initialize it, sync it, or require a Garmin key.

If Codex or Claude Code is on that machine, `garmin-archive connect --client codex` or `garmin-archive connect --client claude` can register the server without resyncing or changing a schedule. Existing registrations are preserved, so check their target archive. Other clients need their own local configuration. A personal assistant running elsewhere also needs a supported way to reach this machine; see [assistant handoffs](../README.md#personal-assistants-and-chatgpt). An assistant without MCP support can use the local CLI to inspect the archive.

In a fresh client session:

1. Confirm tool discovery and call `archive_status` and `setup_status`.
2. Ask about a day that was synced, using `get_day` or a supported `get_trend` metric. Return dates, units, coverage and freshness.
3. Compare a representative result with the local archive and Garmin Connect. Successful discovery alone is not a successful data query.

There are currently eight MCP tools. Seven read data or status; `configure_sync` changes the local macOS schedule after the user chooses an interval. On Linux, `setup_status` reports `unsupported` for the built-in scheduler. Use an external scheduler if wanted. Do not keep retrying `configure_sync` there.

The shipped server uses stdio. It does not configure an authenticated remote HTTP service. Avoid exposing it publicly to bridge a client that cannot launch local processes.

## 5. Schedule only when wanted

Ask for an interval if the user hasn't already chosen one. Six hours is a starting point; request volume grows with frequency and lookback. Check for an existing job before creating another.

- On macOS, `garmin-archive setup --every-hours 6 --lookback-days 2` installs the managed schedule. Its key file must be available outside the shell environment. The setup command starts no immediate sync.
- On other hosts, use the OS scheduler if available. If cron or systemd is absent, a persistent provider-managed routine can run the command below. The workbench does not create or monitor those routines.

```sh
/absolute/path/to/garmin-archive --data-dir /absolute/private/archive sync --catch-up --lookback-days 2
```

Replace both paths. The routine must reach the same persistent archive and key after a restart, handle exit failures, and avoid overlapping jobs. Protect any logs; do not include credentials in job text. Catch-up resumes from saved state but remains subject to Garmin's historical data availability. Verify an actual scheduled execution and its archive status before calling recurring sync tested.

## Report the outcome

Give the user a short handoff: host, archive location, source revision, client connection, schedule (or manual sync), checks completed and remaining limitations. Keep keys, health values, raw responses and GPS data out of public reports. Use the [setup report template](../.github/ISSUE_TEMPLATE/setup-report.md) when reporting compatibility or friction; it also works for the next assistant being tested.

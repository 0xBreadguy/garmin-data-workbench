# Set up your workbench

For agents with workstations and people installing directly. The archive and commands run on the chosen host. For code changes, use the [offline contributor setup](../CONTRIBUTING.md#develop-locally).

Check [host compatibility and verification limits](COMPATIBILITY.md) first. The offline test targets include macOS, Windows and Linux; live Windows credential/privacy validation remains incomplete.

## 1. Choose where the data lives

Use your computer or a persistent remote workstation. Confirm:

- Python 3.12+, [uv](https://docs.astral.sh/uv/) and storage that survives new sessions.
- Private key entry through a hidden terminal prompt or a verified secret facility.
- A query path: shell commands on the host, local stdio MCP, or a separately secured remote connection.
- A scheduler, if wanted. Manual sync is fine.

**Choose the host before supplying credentials.** Processes sharing your OS user can read the key, token cache, health archive and original files, including GPS locations. Owner-only permissions don't isolate those processes; privileged processes and cloud providers may also have access. Let the user accept that environment before authentication or sync. Query results may reach the selected AI provider.

Use synthetic data for compatibility tests. Don't copy personal archives or credentials to test a host.

## 2. Install the commands

Use a persistent directory, such as `~/src`, rather than `/tmp`:

```sh
git clone https://github.com/0xBreadguy/garmin-data-workbench.git
cd garmin-data-workbench
uv tool install --from . garmin-data-workbench
garmin-archive --help
garmin-archive-mcp --help
```

Ask whether the user wants charts during setup. If so, replace the install command with `uv tool install --from '.[charts]' garmin-data-workbench`. This installs the optional plotting dependencies; it does not access Garmin. See [sleep reports](SLEEP.md) and [visualization](VISUALIZATION.md).

Agents should run `garmin-archive agent-guide` after installation. This installed guide covers queries, sleep interpretation, branded charts, delivery and setup verification even when the repository docs are no longer in context.

Find the executable directory with `uv tool dir --bin`; add it to `PATH` if needed. Use absolute paths in client configuration and jobs. A tool install is a snapshot. After updating the checkout:

```sh
uv tool install --force --no-cache --from . garmin-data-workbench
```

## 3. Supply a key and run a first sync

Create your own key on [Garmin Connect's Personal API page](https://connect.garmin.com/app/settings/personalApiToken). Review the terms, choose an expiration and save it securely: Garmin shows it once. Never put the value in chat, command arguments, logs or Git. See [Garmin's key FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/) for expiration and revocation.

### Interactive setup

On macOS, with Codex CLI installed:

```sh
garmin-archive install
```

The installer asks for an update interval (Enter for six hours, `0` for manual), privately prompts for a missing key, syncs seven days on first use, configures the selected macOS schedule and connects Codex. Use `--client claude` for Claude Code. Existing client registrations are preserved.

For generic MCP setup on Linux or another host:

```sh
garmin-archive install --manual --client other
```

This syncs and prints the MCP launch command. Exit code `2` means the client connection is pending; read the preceding output for sync errors. `--client chatgpt` also requires a separate connection. `--manual` leaves existing schedules unchanged. For unattended interval selection, use `--every-hours 6` on macOS.

For shell-only agents or direct CLI/SQL use, supply the key below and use `sync` directly. No assistant registration required.
Alternatively, after secure key setup, `garmin-archive install --manual --client shell` runs the initial catch-up and prints the same-host CLI handoff and verification receipt without MCP probing or registration. Manual mode preserves any existing schedule.

### Without an interactive terminal

Have the host's **verified private secret facility** deliver a file, then:

```sh
/absolute/path/to/garmin-archive save-key --from-file /absolute/private/provider-secret
```

This makes live authentication/profile requests and saves the key, but doesn't sync, connect a client or schedule anything. Replace both paths; the second is a file, never a key value. On POSIX, it must be a regular file owned by the current user with no group/other permissions, usually `0600`. Symlinks are rejected where `O_NOFOLLOW` is supported. Existing key files aren't overwritten. Dispose of the source through the provider's facility afterward.

File import doesn't provide private entry. If no tested secret facility exists, stop before requesting a key. A pseudo-terminal alone doesn't solve this; the installer also refuses echoed key entry.

### Key and archive paths

| Item | Default |
| --- | --- |
| Key | `~/.config/garmin/connect-personal-api-key` |
| Token cache | Under `~/.config/garmin/` |
| Archive | `~/.local/share/garmin-extraction` or an absolute `$XDG_DATA_HOME/garmin-extraction` |

`GARMIN_PERSONAL_API_KEY` overrides the saved key. Keep files outside the checkout with owner-only permissions. Future sync processes need the same key; jobs may not inherit your shell environment.

For a custom archive, put `--data-dir /absolute/private/archive` **before** each CLI command and use that path in MCP and jobs too.

### Check the first sync

For a smaller live test with a key already available, replace both dates with one chosen day:

```sh
garmin-archive sync --from YYYY-MM-DD --to YYYY-MM-DD
garmin-archive status
garmin-archive activities
```

Devices must upload to Garmin Connect first. Inspect coverage and errors: a completed request doesn't prove complete history. `status` reads an existing archive without creating or migrating it; `path` only prints a location. Neither proves a sync succeeded.

Always state exact inclusive dates: January 1–7 is seven dates; January 1–8 is eight. Default sync/trend/sleep windows contain seven dates ending today, which may be incomplete. Offer a longer initial history separately rather than assuming that an installation contains months of data.

## 4. Connect and test the assistant

Choose the [connection for your assistant](ASSISTANTS.md). Agents with shell access can use `day` and `trend` directly; MCP isn't required.

In a fresh session, query a synced date. Return dates, units, freshness and missing-data caveats, then compare a representative result with the archive and Garmin Connect. For MCP, check tool discovery, `archive_status` and `setup_status` first. Registration and discovery alone don't prove a real query works.

Finish with a useful first question such as “How has my sleep been?” Use `sleep` / `get_sleep` for stages, score and stress; use `chart sleep` for the branded overview and attach the actual PNG if the host supports it. For a custom chart, run `brand` and retain the same coverage/source rules. See the installed `agent-guide`. Do not let missing chart dependencies silently produce an unbranded fallback.

## 5. Schedule only when wanted

Use an interval the user chooses. On macOS:

```sh
garmin-archive setup --every-hours 6 --lookback-days 2
```

This changes the managed schedule without running a sync. Its saved key must be available outside your shell environment. On other hosts, use an OS scheduler or persistent provider routine; Linux's built-in scheduler status is `unsupported`.

Check for existing jobs, preserve unrelated schedules and verify an actual execution. See [catch-up and scheduling](USAGE.md#catch-up-and-scheduling) for recovery, job examples and limits.

`garmin-archive --data-dir /absolute/private/archive routine-template` prints the absolute catch-up command and provider-neutral instructions; it creates no job. After the user selects an interval, an agent with a supported scheduler can use that template. Confirm that its scheduled process can access the same private key and storage after restart. Never embed key values in routine instructions. Inspect the run's exit code, sync report and archive status; authorize any failure-notification destination with the user.

## Hand off

Report the host, archive path, installed source revision, query path, schedule or manual sync, checks passed and remaining gaps. Keep private data out of reports. Use the [setup report](../.github/ISSUE_TEMPLATE/setup-report.md) for compatibility findings.

Run `garmin-archive setup-receipt` (or MCP `setup_receipt`) for read-only evidence. The installer also prints a receipt after its connection step. It includes build revision/dirty status where known, version, chart availability, archive coverage/failures and native schedule configuration. Unknown provenance stays unknown; dirty builds are labeled. It reads no keys and makes no network requests. It does not inspect provider routines or establish an assistant conversation succeeded.

Use “configured; first automated execution pending” until a real scheduled run is observed and its archive update checked. A successful manual sync or loaded job alone cannot verify recurrence. Report manual mode when that is the user's choice; do not create a job just to complete the guide.

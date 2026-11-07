# Set up your workbench

For agents with workstations and people installing directly. The archive and commands run on the chosen host. For code changes, use the [offline contributor setup](../CONTRIBUTING.md#develop-locally).

Check [host compatibility and verification limits](COMPATIBILITY.md) first. The offline test targets include macOS, Windows and Linux; live Windows credential/privacy validation remains incomplete.

## 1. Choose where the data lives

Use your computer or a persistent remote workstation. Confirm:

- Python 3.12+, [uv](https://docs.astral.sh/uv/) and storage that survives new sessions.
- For live setup, private key entry through a hidden terminal prompt or a verified secret facility.
- A query path: shell commands on the host, local stdio MCP, or a separately secured remote connection.
- A scheduler, if wanted. Manual sync is fine.

Name the execution host and OS before starting: commands and archive may live in an assistant's VM even when its chat app is on the user's Mac. A new chat or bot may share an existing filesystem. Distinguish provider-claimed persistent storage from a successful new-session/restart test; don't restart the host just to complete setup.

**Choose the host before supplying credentials.** Processes sharing your OS user can read the key, token cache, health archive and original files, including GPS locations. Owner-only permissions don't isolate those processes; privileged processes and cloud providers may also have access. Let the user accept that environment before authentication or sync. Query results may reach the selected AI provider.

Use synthetic data for compatibility tests. Don't copy personal archives or credentials to test a host.

### Mock-only setup: stop before credentials

A request such as “Install this repo using only mock data; don't connect to Garmin or access existing personal data” selects this route. It needs no key, client registration or recurring job. Skip the live setup steps below and finish with [the handoff](#hand-off).

**If an installation already exists:** “Install the current repo with mock data; leave my existing installation unchanged” still requests a new setup. Report the found checkout's actual revision (or unknown provenance for an installed copy); preservation alone doesn't complete the request. For example: “I found an older checkout at `<found-revision>`. I'll preserve it and use a separate current checkout, environment and synthetic archive for this request.” Continue with the authorized isolated route below and verify the new revision and executable used. If the user instead wants reuse, or their intended choice is unclear, clarify that choice before proceeding; don't silently reuse or upgrade the old installation.

1. Discover prior state by metadata only: executable locations, `uv tool list`, candidate checkout revision/status and environment-directory existence. For keys, token caches and personal archives, check only existence. For client/job configuration, use existence checks or supported metadata-only listings without command bodies or secret values. Never open contents or query existing archives. If discovery isn't available, report it as unknown.
2. Choose a **new dedicated checkout and environment**, plus a **new synthetic archive outside every repository**. Check that the destinations are absent, including the environment selected by `UV_PROJECT_ENVIRONMENT`. Don't pull/fast-forward an existing clone, sync its `.venv`, replace a tool installation, or move/delete old state. Preserve tools, configurations, registrations, jobs and data. If reuse already occurred, disclose exactly what was reused or changed and what remains unknown; don't call it a fresh install or attempt a reset.
3. Generate and query only the new demo. For example, in a POSIX shell, replace `/absolute/new/garmin-mock` with a new location on the chosen host outside existing checkouts:

```sh
git clone https://github.com/0xBreadguy/garmin-data-workbench.git /absolute/new/garmin-mock/source
cd /absolute/new/garmin-mock/source
export UV_PROJECT_ENVIRONMENT=/absolute/new/garmin-mock/env
uv sync --locked --extra charts
uv run --quiet --locked --extra charts python scripts/create_demo_archive.py /absolute/new/garmin-mock/demo
uv run --quiet --locked --extra charts garmin-archive --data-dir /absolute/new/garmin-mock/demo sleep --from 2026-04-24 --to 2026-04-30
uv run --quiet --locked --extra charts garmin-archive --data-dir /absolute/new/garmin-mock/demo chart sleep --from 2026-04-24 --to 2026-04-30 --output /absolute/new/garmin-mock/sleep.png
```

Use host-native absolute paths; in PowerShell set `$env:UV_PROJECT_ENVIRONMENT` to the new environment path. Charts are optional: omit `--extra charts` and the chart command for text-only setup. This environment leaves any installed `uv tool` copy in place. Dependency downloads may use the network; the generator and queries make no Garmin requests. Do not run `install`, `sync`, `setup`, `save-key` (including its dry run), or `scripts/check_connection.py` for this route.

The default demo covers January 1–April 30, 2026, with simulated collection timestamps. Offer “How was sleep in the latest demo week, April 24–30?” rather than implying current-week personal data. See [demo cases and provenance](VISUALIZATION.md#try-generated-demo-data). Deliver a generated image through the host's supported attachment interface; a file path alone doesn't verify delivery. Finish here with synthetic/manual status; live setup requires a separate user request.

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

Agents should run `garmin-archive agent-guide` after installation; `agent-guide --client muse` also appends the Muse handoff (other supported client names work too). This installed guide covers queries, sleep interpretation, branded charts, delivery and setup verification even when the repository docs are no longer in context.

Find the executable directory with `uv tool dir --bin`; if it isn't on `PATH`, invoke the executables by absolute path and report that in the handoff. Add it to the shell's `PATH` if wanted. Use absolute paths in client configuration and jobs. A tool install is a snapshot. After updating the checkout:

```sh
uv tool install --force --no-cache --from . garmin-data-workbench
```

If you installed charts, use `--from '.[charts]'` in the upgrade command too; installing the base package replaces the tool environment without its optional plotting dependencies.

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

First check the host's actual secret-delivery capabilities; don't assume that a vault can inject a process environment or create a file. The workbench supports either route below. A vault storing a secret alone does not establish that it can deliver it to the process. Never ask for the key in chat or put it in a command, argument, or log.

**Environment injection:** If the host can privately inject the secret as `GARMIN_PERSONAL_API_KEY` into the actual workbench process, use that facility and run `garmin-archive install --manual --client shell` or `sync` in that process. Follow the host's documented secret workflow; do not print the variable to check it. The installer recognizes an existing environment key but does not separately validate or save it: the subsequent sync authenticates with Garmin. Check the sync result to establish whether it worked. The environment key takes precedence over a saved key and must be delivered again to future sync processes; it may not survive a new session or reach scheduled jobs. The built-in macOS schedule requires a matching saved key, so environment injection alone is not sufficient for that schedule.

**Private file delivery:** If the host can deliver a private file, use it with:

```sh
/absolute/path/to/garmin-archive save-key --from-file /absolute/private/provider-secret --dry-run
/absolute/path/to/garmin-archive save-key --from-file /absolute/private/provider-secret
```

The dry run checks a bounded single-value UTF-8 source, local file privacy where supported, destination absence and parent access. It makes no network requests, creates no key/token cache and does not test actual destination writes or certify the provider secret facility. On Windows it explicitly reports that ACL privacy remains unverified.

The second command makes live authentication/profile requests and saves the key, but doesn't sync, connect a client or schedule anything. Replace both paths; the second is a file, never a key value. On POSIX, it must be a regular file owned by the current user with no group/other permissions, usually `0600`. Symlink sources are rejected; POSIX also opens with `O_NOFOLLOW` where available and checks the opened file identity. Existing key files aren't overwritten. Live validation prints its authentication/profile phase and uses a 15-second timeout per request; `--timeout` accepts 1–120 seconds. A timeout reports failure instead of a saved key. Dispose of the source through the provider's facility afterward.

File import doesn't provide private entry. If neither delivery route nor a verified hidden terminal prompt is available, stop before requesting a key and explain the host limitation. A pseudo-terminal alone doesn't establish private entry; the installer also refuses echoed key entry.

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

Finish with a useful first question such as “How has my sleep been?” Use `sleep` / `get_sleep` and follow the canonical [presentation policy](../src/garmin_archive/agent_guide.md#present-and-visualize) in installed `agent-guide`. Verify actual image delivery when supported; a generated file or path alone does not pass. For custom charts, read `brand` and retain the same coverage/source rules. Do not let missing chart dependencies silently produce an unbranded fallback.

Proactively offer optional ongoing monitoring and check-ins, such as a morning report. If wanted, agree on the subjects, frequency, local time and timezone, delivery destination, and whether to report every time or only on notable changes. On-demand questions are fine too. A sync schedule does not create or deliver reports: check the assistant host's scheduling and delivery capabilities, obtain the user's authorization, and verify a real run and delivery. If unavailable, offer on-demand check-ins instead. Reports should state freshness, coverage and missing or failed data, and follow the interpretation guidance in `agent-guide`.

## 5. Schedule only when wanted

Use an interval the user chooses. On macOS:

```sh
garmin-archive setup --every-hours 6 --lookback-days 2
```

This changes the managed schedule without running a sync. Its saved key must be available outside your shell environment. On other hosts, use an OS scheduler or persistent provider routine; Linux's built-in scheduler status is `unsupported`.

Check for existing jobs, preserve unrelated schedules and verify an actual execution. See [catch-up and scheduling](USAGE.md#catch-up-and-scheduling) for recovery, job examples and limits.

`garmin-archive --data-dir /absolute/private/archive routine-template` prints the absolute catch-up command and provider-neutral instructions; it creates no job. After the user selects an interval, an agent with a supported scheduler can use that template. Confirm that its scheduled process can access the same private key and storage after restart. Never embed key values in routine instructions. Inspect the run's exit code, sync report and archive status; authorize any failure-notification destination with the user.

## Hand off

Give a compact completion handoff in the user's private setup conversation:

- Execution host/OS and where the archive lives, explicitly distinguishing an assistant VM from the chat app's computer.
- Source revision and fresh versus reused checkout/environment; disclose changed or unknown prior state.
- Synthetic versus live data, exact available dates and simulated versus actual collection freshness; manual/on-demand for this archive or the chosen schedule. No new job does not establish the absence of existing jobs.
- Query route actually used. Give an absolute same-host executable and `--data-dir` reference usable next session, especially if the executable isn't on `PATH`. For the mock environment above, the executable is `env/bin/garmin-archive` under the new root (`env/Scripts/garmin-archive.exe` on Windows). [The shell handoff](ASSISTANTS.md#shell-access-on-the-workstation) prints the command with resolved paths.
- Checks passed and gaps: persistence expected versus tested in a new session/restart; CLI query/image delivery separately from MCP registration, discovery and real tool query. Mark untested stages explicitly. `garmin-archive-mcp --help` proves neither discovery nor a client connection.

Keep private host identifiers and absolute paths out of public reports. Use the [setup report](../.github/ISSUE_TEMPLATE/setup-report.md) for sanitized compatibility findings.

For live setup, run `garmin-archive setup-receipt` (or MCP `setup_receipt`) for read-only evidence, selecting `--data-dir` explicitly for a custom archive. The installer also prints a receipt after its connection step. It includes build revision/dirty status where known, version, chart availability, archive coverage/failures and native schedule configuration. Unknown provenance stays unknown; dirty builds are labeled. It reads no keys and makes no network requests. It does not inspect provider routines or establish an assistant conversation succeeded. For mock-only setup, use `status` with the explicit new demo path instead: the receipt also inspects native job configuration, beyond existence-only discovery.

Use “configured; first automated execution pending” until a real scheduled run is observed and its archive update checked. A successful manual sync or loaded job alone cannot verify recurrence. Report manual mode when that is the user's choice; do not create a job just to complete the guide.

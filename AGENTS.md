# Working on Garmin Data Workbench

This file is the shared entry point for coding agents and assistants helping a user install or use the workbench. Keep instructions portable across agents; add client-specific steps only when a tested difference requires them.

## Start here

- Read [README.md](README.md) for the product and [docs/USAGE.md](docs/USAGE.md) for commands.
- For a user's installation, follow [docs/SETUP.md](docs/SETUP.md). A request to inspect or test the code does not imply permission to use credentials, sync health data, or create a recurring job.
- For code changes, read [CONTRIBUTING.md](CONTRIBUTING.md), [ARCHITECTURE.md](ARCHITECTURE.md), and [docs/TESTING.md](docs/TESTING.md). [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md) explains the direction; planned features are not implemented guarantees.
- Check `git status --short --branch` before editing. Preserve existing work and use the checkout assigned to your task. Do not discard changes or switch another worker's branch.

## Offline development quick start

Requires Python 3.12+ and uv. From the repository root:

```sh
uv sync --locked
uv run python -m unittest discover -s tests -v
uv run garmin-archive --help
uv run garmin-archive-mcp --help
```

These checks need no Garmin account, key, live archive, client registration, or scheduler. Dependency installation may need network access. Do not run `install`, `sync`, `setup`, or `scripts/check_connection.py` as an offline smoke test. `install` starts a live sync and may change assistant configuration and scheduling.

## Repository map

| Location | Responsibility |
| --- | --- |
| `src/garmin_archive/cli.py` | CLI parsing, sync orchestration, exports and installer flow |
| `src/garmin_archive/install.py` | Key setup, client registration, MCP probes and assistant handoffs |
| `src/garmin_archive/sync.py` | Garmin retrieval, retries and per-day sync state |
| `src/garmin_archive/archive.py` | SQLite schema, stored source data and archive writes |
| `src/garmin_archive/fit.py` | Original activity ZIP handling and FIT decoding |
| `src/garmin_archive/queries.py` | Shared metric definitions, daily summaries and trends |
| `src/garmin_archive/preferences.py` | Profile units, time zone and presentation helpers |
| `src/garmin_archive/mcp_server.py` | Bounded stdio tools over the local archive |
| `src/garmin_archive/schedule.py` | Opt-in macOS scheduling and status |
| `tests/` | Offline unittest tests using synthetic data and fake API responses |
| `scripts/` | Optional live connection check and offline synthetic benchmark |

## Implementation rules

- Keep collection separate from queries. MCP data tools read the existing archive without Garmin credentials or live requests. `configure_sync` is an explicit schedule-changing tool, not a data query.
- Keep SQLite as the archive and retain original activity files and source JSON. Preserve existing archives and test schema changes with an older synthetic archive. Do not enable WAL or change durability settings without addressing the constraints in `ARCHITECTURE.md`.
- Keep metric definitions in shared query code. Return units, dates, freshness and coverage; distinguish zero, missing, empty and failed data. Never present stale values after a failed refresh as current.
- Respect Garmin profile preferences and explicit user overrides. Preserve source units and timestamp meaning; don't infer a historical activity's time zone from the current profile.
- Bound tool output and paginate large results. Do not add coordinates to default summary responses.
- Keep sync resumable and serialized per archive. Handle authentication failures, rate limits and repeated server/network errors without tight retry loops or exposing response bodies.
- Use the existing Python, unittest and uv conventions. Change `uv.lock` deliberately when dependencies change. There is currently no separate formatter, linter or type-check gate.

## User setup and privacy

- Discover the intended host and check persistent storage, scheduling, secure key entry and local MCP support. Cloud-hosted assistants can use the generic setup path. Do not assume cron, systemd, macOS, Codex, or a particular bot integration exists.
- Before a cloud sync, explain that other processes or agents running as the same operating-system user can read owner-only files, including the Garmin key, token cache, health archive and precise activity locations. The user chooses whether that environment is acceptable; apply an existing informed choice without asking repeatedly.
- Never ask for a Garmin key in chat or print secrets to inspect them. Use a hidden terminal prompt or the host's supported secret mechanism. Keep keys out of commands, logs, fixtures and Git.
- Keep real data outside the repository. Default archive: `~/.local/share/garmin-extraction` (or under an absolute `XDG_DATA_HOME`). Key file: `~/.config/garmin/connect-personal-api-key`; the Garmin client also uses a token cache under `~/.config/garmin/`.
- Tool responses may reach the selected AI provider. Use the smallest relevant query, and do not upload raw health responses, original files or GPS routes to debug the project.
- Choose a sync interval with the user before configuring a scheduler or provider routine. On Linux, an `unsupported` setup status means the built-in scheduler is unavailable; it does not say whether a provider routine exists.
- Preserve existing client registrations and unrelated scheduled jobs. Do not expose the stdio server on a public port as a shortcut to remote access.

## Verify and hand off

Use the smallest meaningful check for the change; see [docs/TESTING.md](docs/TESTING.md) for focused commands and live validation. Run broader checks for changes with broader regression risk. Before pushing or merging to the default branch, the full offline suite and required release checks must pass for that revision (exact-revision CI can supply that evidence).

Review `git diff --check`, the diff, and the files being staged. Keep secrets, archives, caches and unrelated edits out of commits. Report what changed, which checks passed, any live or platform checks still missing, and the next actionable step. Installation, MCP discovery, a successful sync, a real assistant query and recurring execution are separate verification steps; don't claim one proves the others.

Keep current setup and architecture facts in this repository. Don't require a contributor's private memory, personal accounts, or a particular agent runtime to work on the project.

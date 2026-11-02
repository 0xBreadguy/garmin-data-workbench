# Contributing to Garmin Data Workbench

Thanks for helping make personal Garmin data more useful and accessible. This is an independent, community-built project for people who want to own and query their data locally.

## Ways to help

- Report a reproducible bug or improve setup and troubleshooting documentation.
- Add support for a Garmin Personal API dataset or improve FIT decoding and data coverage.
- Improve queries, exports, sync recovery or tests.
- Improve the MCP tools or share an analysis workflow.
- Test the generic setup with another assistant or on another host and report where it gets stuck.

For larger changes, start with an issue describing the problem and proposed direction so contributors can coordinate before writing a lot of code.

## Develop locally

Install Python 3.12+ and [uv](https://docs.astral.sh/uv/), then from the repository:

```sh
uv sync --locked
uv run python -m unittest discover -s tests -v
uv run garmin-archive --help
uv run garmin-archive-mcp --help
```

The tests use generated FIT data and fake Garmin responses, so they do not require a Garmin account or an API key. The [README](README.md) documents the optional live connection for your own use.

Use `uv run` when developing; a separately installed `uv tool` is a snapshot and won't automatically pick up edits. If `uv sync --locked` fails because a deliberate dependency change needs a new lockfile, run `uv lock` and review and commit `pyproject.toml` and `uv.lock` together. Don't refresh dependencies merely to work around an unrelated setup failure.

## Working with an agent

Start with [AGENTS.md](AGENTS.md). It contains the shared instructions, source map, architecture constraints and privacy boundaries. The repo does not require a particular bot, private memory system or paid assistant account.

For help installing and using your own archive, give the assistant [docs/SETUP.md](docs/SETUP.md). For implementation work, give it the task and ask it to read `AGENTS.md` first. Keep client-specific instructions limited to observed differences so the common path stays usable with new assistants.

## Making a change

1. Check Git status and make a focused branch from the intended base. Preserve existing work if you're sharing a checkout.
2. Read the relevant code and [architecture notes](ARCHITECTURE.md). Keep retrieval, storage, shared queries and adapters separate.
3. Make the smallest complete change. Add meaningful offline tests for new behavior or regressions, and document new commands, datasets or limitations. Use synthetic fixtures and temporary directories.
4. Run the relevant checks in [docs/TESTING.md](docs/TESTING.md), then review `git diff --check` and the diff. Broaden testing for shared or uncertain regression scope. Full-suite checks for the final revision are required before pushing or merging to the default branch.
5. Open a pull request describing the user-visible problem, resulting behavior, checks run and any remaining live or platform validation. Keep unrelated changes separate.

Use existing Python and unittest conventions. There is no separate configured formatter, lint or type-check gate. Run `uv build` when changing packaging, and keep dependency changes deliberate. Do not change storage engines or durability settings without a demonstrated need and a migration/backup plan.

The project stores user data outside the checkout by default; please preserve that behavior. MCP data queries must remain usable when Garmin is unavailable. Changes should preserve source data, dates and units and distinguish missing, empty, failed and stale results.

## Reporting bugs and setup results

Use the bug report for a reproducible failure and the setup report for a new host or assistant. Include the source revision, OS and Python version, command or tool involved, expected behavior and sanitized actual behavior. Distinguish installation, tool discovery, live sync, a real assistant query and scheduled execution. A passing test suite doesn't establish all five.

There is no need to supply credentials or a real archive for an initial report. Give a small synthetic reproduction when possible. Describe the host's persistence and scheduler capabilities without assuming every Linux machine has cron or systemd.

## Protect personal data

Do not include API keys, tokens, activity files, real Garmin exports, health measurements, GPS routes or unredacted API responses in issues, pull requests, fixtures or logs. Use synthetic examples and remove identifying details from reports. If a bug involves sensitive data, describe the behavior without uploading it.

For vulnerabilities or exposed credentials, follow [SECURITY.md](SECURITY.md). Public issue templates are for sanitized bug reports, setup results and feature requests.

The project is independent and is not affiliated with Garmin. Data access and features can differ by account and device; report the behavior you observed without assuming every device works the same way.

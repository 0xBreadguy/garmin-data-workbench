# Contribute

Help with sync reliability, data coverage, FIT decoding, queries, assistant setup or docs. For a larger change, open an issue describing the problem and proposed approach first.

## Develop locally

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/):

```sh
uv sync --locked
uv run python -m unittest discover -s tests -v
uv run garmin-archive --help
uv run garmin-archive-mcp --help
```

Tests use synthetic data and fake responses. No Garmin account or key required; dependency installation may need network access.

Use `uv run` for development. Installed `uv tool` copies don't pick up edits. Change dependencies deliberately: run `uv lock`, then review `pyproject.toml` and `uv.lock` together.

## Make a change

1. Check Git status, use an isolated branch and preserve existing work.
2. Read [AGENTS.md](AGENTS.md) and [ARCHITECTURE.md](ARCHITECTURE.md). Keep collection, storage, shared queries and adapters separate.
3. Add focused offline tests for changed behavior. Preserve source data, units, dates and the distinction between missing, empty, failed and stale values.
4. Run the [relevant checks](docs/TESTING.md), inspect the diff and run `git diff --check`. Run `uv build` for packaging changes.
5. Open a PR explaining the user-visible change, verification and remaining gaps.

Use the existing Python, unittest and uv conventions. There is no separate lint, formatter or type-check gate. Before pushing or merging to the default branch, the full suite and required release checks must pass for that revision; exact-revision CI counts.

## Report a problem

Include the source revision, OS/Python version, command or client, expected behavior and sanitized result. For a new host or assistant, use the [setup report](.github/ISSUE_TEMPLATE/setup-report.md). Distinguish installation, discovery, sync, a real query and actual scheduled execution.

Use synthetic reproductions. Keep keys, tokens, archives, health records, original files and routes out of reports, fixtures and Git. Report vulnerabilities through [SECURITY.md](SECURITY.md).

For installation help rather than code changes, start with [SETUP.md](docs/SETUP.md). No private memory system or particular assistant is required.

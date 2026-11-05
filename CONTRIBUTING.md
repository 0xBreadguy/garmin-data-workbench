# Contribute

Help with sync reliability, data coverage, FIT decoding, queries, assistant setup or docs. For a larger change, open an issue describing the problem and proposed approach first.

## Develop locally

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/):

```sh
git clone https://github.com/0xBreadguy/garmin-data-workbench.git
cd garmin-data-workbench
uv sync --locked --extra charts
uv run --locked --extra charts python -m unittest discover -s tests -v
uv run --locked --extra charts garmin-archive --help
uv run --locked --extra charts garmin-archive-mcp --help
```

Tests use synthetic data and fake responses. No Garmin account or key required; dependency installation may need network access.

Fork the repository first if you need your own push destination. If you already have a checkout, start with the `uv` commands. The charts extra enables rendering tests; a base-only environment skips those tests. Keep `--extra charts` on subsequent `uv run` commands when checking chart behavior.

Use `uv run` for development. Installed `uv tool` copies don't pick up edits. Change dependencies deliberately: run `uv lock`, then review `pyproject.toml` and `uv.lock` together. Don't run `install`, `sync`, `setup` or the live connection script as a development smoke test.

## Where a change belongs

The installable Python package lives in `src/garmin_archive/`. CLI and MCP are adapters over the same local query code; neither should define a separate interpretation of a metric.

| Change | Start here | Verification |
| --- | --- | --- |
| Collection, retries or resumability | `sources.py`, `sync.py`, `cli.py` sync orchestration | `test_archive.py`, `test_catchup.py`, `test_contract_corpus.py` |
| Archive/schema or FIT decoding | `archive.py`, `fit.py` | `test_archive.py`, `test_fit_corpus.py`; older synthetic archive compatibility |
| A named metric or its meaning | `queries.py`, `sleep.py`, `body_battery.py` | Domain tests and matching CLI/MCP results |
| Native API fields or pagination | `api_data.py`, `sources.py`, `personal_api_contract.json` | `test_api_data.py`, `test_contract_corpus.py`; [contract maintenance](docs/API_COVERAGE.md#verification-and-contract-maintenance) |
| Charts and delivery | `charts.py`, `chart_delivery.py`, `brand.json`, `assets/` | `test_charts.py`, `test_chart_delivery.py`, `test_cli_chart_metadata.py`; inspect a synthetic render |
| Commands or tool surfaces | `cli.py`, `mcp_server.py` | `test_cli_queries.py`, `test_workbench_mcp.py`; installed-wheel smoke for entry-point changes |
| Setup, host behavior or scheduling | `install.py`, `onboarding.py`, `platforms.py`, `schedule.py` | Corresponding test files; OS-specific behavior stays at these boundaries |
| User or assistant guidance | `README.md`, `docs/`, `agent_guide.md`, `skills/` | Check commands and links; keep installed guidance aligned with repository docs |

Python paths in this table are relative to `src/garmin_archive/`; tests live in `tests/`. [`AGENTS.md`](AGENTS.md#repository-map) has the full module map and [`docs/TESTING.md`](docs/TESTING.md#focused-checks) lists focused test commands. You don't need an agent, private tooling or a live Garmin account to contribute.

Start with a small bug, a clearer error, a synthetic edge case or a documentation correction. Use issues to discuss new collectors, storage/durability changes, metric interpretations or new integration claims before building them. The current collection scope is Garmin's official Personal API.

## Make a change

1. Check Git status, use an isolated branch and preserve existing work.
2. Read [AGENTS.md](AGENTS.md) and [ARCHITECTURE.md](ARCHITECTURE.md). Keep collection, storage, shared queries and adapters separate.
3. Add focused offline tests for changed behavior. Preserve source data, units, dates and the distinction between missing, empty, failed and stale values. Use invented fixtures; never anonymize a personal archive into a test fixture.
4. Run the [relevant checks](docs/TESTING.md), inspect the diff and run `git diff --check`. Run `uv build` for packaging changes.
5. Open a PR explaining the user-visible change, verification and remaining gaps.

Use the existing Python, unittest and uv conventions. There is no separate lint, formatter or type-check gate. Before pushing or merging to the default branch, the full suite and required release checks must pass for that revision; exact-revision CI counts.

For a focused check, replace the filename with the affected test:

```sh
uv run --locked --extra charts python -m unittest discover -s tests -p 'test_queries.py' -v
git diff --check
```

Keep a PR focused on one problem and describe the resulting behavior, checks and remaining limits in the [PR template](.github/pull_request_template.md). Include user-facing docs when behavior changes. API/schema changes need preservation and compatibility evidence; rendered changes need synthetic visual inspection. Don't bundle unrelated reformatting or generated archives. Contributions use the repository's [MIT license](LICENSE).

Maintainers: follow [the release checklist](docs/RELEASING.md) for dependency review, required CI and a tagged release. Passing the offline suite doesn't establish live host or assistant support.

## Report a problem

Include the source revision, OS/Python version, command or client, expected behavior and sanitized result. For a new host or assistant, use the [setup report](.github/ISSUE_TEMPLATE/setup-report.md). Distinguish installation, discovery, sync, a real query and actual scheduled execution.

Use synthetic reproductions. Keep keys, tokens, archives, health records, original files and routes out of reports, fixtures and Git. Report vulnerabilities through [SECURITY.md](SECURITY.md).

For installation help rather than code changes, start with [SETUP.md](docs/SETUP.md). No private memory system or particular assistant is required.

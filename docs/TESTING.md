# Verification

Use synthetic data, fake responses and temporary archives. Offline checks need no Garmin credentials, client registration or schedule. Dependency installation may need network access.

## Baseline

Python 3.12+ and uv, from the repository root:

```sh
uv sync --locked
uv run python -m unittest discover -s tests -v
uv run garmin-archive --help
uv run garmin-archive-mcp --help
git diff --check
```

[CI](../.github/workflows/tests.yml) runs the locked offline suite on Ubuntu for PRs and pushes to `main`. There is no separate lint, format or type-check gate.

## Focused checks

Use `uv run python -m unittest discover -s tests -p '<file>' -v`:

| Change | Test file |
| --- | --- |
| Installer, key import, registration, handoffs | `test_install.py` |
| Scheduling and rollback | `test_schedule.py` |
| Catch-up and recovery | `test_catchup.py` |
| Archive, FIT decoding, sync | `test_archive.py` |
| Metrics and missingness | `test_queries.py` |
| Read-only CLI queries | `test_cli_queries.py` |
| Units and time zones | `test_preferences.py` |
| Stdio MCP handshake and responses | `test_workbench_mcp.py` |

Run affected checks while iterating. Broaden for shared behavior, schema, dependencies, configuration or uncertain regression scope. Documentation edits usually need command/link checks and diff review. Before pushing or merging to the default branch, require the full suite and release checks for that revision; exact-revision CI counts.

For packaging, run `uv build` and inspect artifacts. `uv run python scripts/benchmark_archive.py` measures a temporary synthetic database, not sync or assistant latency.

## Live checks are separate

Follow [SETUP.md](SETUP.md) only when a real-account test is authorized. Don't run `install`, `sync`, `setup`, `save-key` or `scripts/check_connection.py` as offline smoke tests: they use credentials, make live requests or change configuration.

Record each stage separately:

1. Commands installed: source revision, OS and Python version.
2. Offline tests and a synthetic stdio query passed.
3. A chosen short sync completed; coverage/errors inspected.
4. A real assistant query returned dates, units and missingness, checked against the archive and Garmin Connect.
5. An opted-in scheduled job actually ran and advanced the archive.

Registration doesn't prove discovery; discovery doesn't prove a real query. Matching payload shapes don't prove metric meaning. Current field mappings were checked against one account's seven-day archive; values still need comparison with Connect.

`save-key` tests mock authentication and use disposable files. They don't verify a provider's secret-entry facility. See [Muse notes](MUSE.md) for that host's remaining checks. Report compatibility through the [setup template](../.github/ISSUE_TEMPLATE/setup-report.md), without private data.

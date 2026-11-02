# Verification

Development checks use synthetic FIT data, fake API responses and temporary archives. They do not require a Garmin key, contact Garmin, register a real assistant, or install a real schedule. Dependency installation may require network access.

## Baseline

From the repository root, with Python 3.12+ and uv:

```sh
uv sync --locked
uv run python -m unittest discover -s tests -v
uv run garmin-archive --help
uv run garmin-archive-mcp --help
git diff --check
```

[CI](../.github/workflows/tests.yml) installs locked dependencies and runs the offline suite on Ubuntu for pull requests and pushes to `main`. There is no separate configured lint, format or type-check gate. Do not describe those checks as passing unless you added and ran them.

## Focused checks

Use unittest discovery so tests don't require a `tests` Python package:

| Change | Focused command |
| --- | --- |
| Key setup, registration, handoff or installer flow | `uv run python -m unittest discover -s tests -p 'test_install.py' -v` |
| Schedule configuration and rollback | `uv run python -m unittest discover -s tests -p 'test_schedule.py' -v` |
| Catch-up checkpoints and sync recovery | `uv run python -m unittest discover -s tests -p 'test_catchup.py' -v` |
| Archive writes, FIT decode and sync behavior | `uv run python -m unittest discover -s tests -p 'test_archive.py' -v` |
| Metric definitions and missingness | `uv run python -m unittest discover -s tests -p 'test_queries.py' -v` |
| Units and time zones | `uv run python -m unittest discover -s tests -p 'test_preferences.py' -v` |
| Real stdio MCP handshake and tool responses | `uv run python -m unittest discover -s tests -p 'test_workbench_mcp.py' -v` |

Run the affected checks while iterating. Broaden to the full suite for shared behavior, schema, dependencies, configuration or uncertain regression scope. Documentation-only changes usually need command/link checks and a diff review. Before pushing or merging to the default branch, use a passing full suite and any required release checks for the final revision; exact-revision CI can provide that evidence.

For packaging changes, also run `uv build` and inspect the artifacts. The offline synthetic benchmark is `uv run python scripts/benchmark_archive.py`. Its local database timings do not measure sync latency, assistant response time or cloud performance.

## Live validation is separate

Follow [SETUP.md](SETUP.md) when the user wants to use a real account. Do not run the installer, a sync, or `scripts/check_connection.py` just to verify a code change: they use credentials and make live Garmin requests. Live setup can also alter local client configuration and recurring jobs.

Track these stages separately in a setup report:

1. Commands installed from a recorded source revision on a named OS and Python version.
2. Offline tests and local stdio handshake passed using synthetic data.
3. A user-selected short sync succeeded; archive coverage and errors were inspected.
4. A real assistant query returned dated results with units and missing-data caveats, checked against the archive and Garmin Connect.
5. An opted-in scheduled job actually executed and advanced the archive as expected.

A handoff printed by `assistant-guide` is guidance, not evidence that an assistant can reach the host. A registered client isn't necessarily connected to the intended archive. An empty archive can pass a handshake without verifying real metric mappings. A matched payload shape isn't enough to confirm a metric's meaning.

For a new assistant, start with the same generic setup. Record a client-specific exception only after observing it, with a reproducible command or description and a privacy-safe outcome. Report failures without key values, token caches, raw Garmin bodies, health records or routes. See the [setup report template](../.github/ISSUE_TEMPLATE/setup-report.md).

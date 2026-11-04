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

[CI](../.github/workflows/tests.yml) runs the locked offline suite on macOS, Windows and Ubuntu with Python 3.12 for PRs and pushes to `main`. Each job also builds and smoke-tests an installed wheel. There is no separate lint, format or type-check gate. See [compatibility boundaries](COMPATIBILITY.md) before treating offline results as live-host support.

CI enables the optional `charts` extra so rendering tests run on every OS. To match locally, add `--extra charts` to both `uv sync --locked` and `uv run --locked`.

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
| Entry points and POSIX/PowerShell command examples | `test_platforms.py` |
| Stdio MCP handshake and responses | `test_workbench_mcp.py` |

Run affected checks while iterating. Broaden for shared behavior, schema, dependencies, configuration or uncertain regression scope. Documentation edits usually need command/link checks and diff review. Before pushing or merging to the default branch, require the full suite and release checks for that revision; exact-revision CI counts.

For an automated CLI compatibility check, record the checkout revision and exact invocation, and capture the exit code, stdout and stderr separately. Use the installed executable or `uv run --quiet --locked` (`--extra charts` for charting); see the [output contract](USAGE.md#output-and-automation). Include a first invocation with a fresh disposable `UV_PROJECT_ENVIRONMENT` path to catch setup chatter. With a synthetic archive, missing health responses and activity IDs should exit `3` with `not_found` JSON on stderr; a nonexistent archive should exit `1` with `archive_unavailable` and remain absent. Compare the quiet invocation with the environment's direct executable; uv setup failures aren't CLI responses.

For packaging, run `uv build` and inspect artifacts, then:

```sh
uv run --locked python scripts/smoke_installed.py
uv run --locked --extra charts python scripts/smoke_installed.py --charts
```

The smoke check expects exactly one wheel in `dist/`. It installs that wheel and locked runtime dependencies into a temporary environment, runs both installed help commands, seeds a synthetic archive using the installed package and queries it through CLI and stdio MCP from outside the checkout. It checks that queries leave the database unchanged. Installation may need network access. No credentials, live sync, client registration or scheduler are used.

The `--charts` mode also installs the locked chart dependencies and renders a synthetic PNG with the installed command.

On Windows, POSIX mode-bit assertions do not apply; shared behavior still runs. macOS schedule tests use fake `launchctl` and user IDs on every OS. The command-example test executes the native shell (PowerShell on Windows, `sh` elsewhere).

`uv run python scripts/benchmark_archive.py` measures a temporary synthetic database, not sync or assistant latency.

## Live checks are separate

Follow [SETUP.md](SETUP.md) only when a real-account test is authorized. Don't run `install`, `sync`, `setup`, `save-key` or `scripts/check_connection.py` as offline smoke tests: they use credentials, make live requests or change configuration.

Record each stage separately:

1. Commands installed: source revision, OS and Python version.
2. Offline tests and a synthetic stdio query passed.
3. A chosen short sync completed; coverage/errors inspected.
4. A real assistant query returned dates, units and missingness, checked against the archive and Garmin Connect.
5. An opted-in scheduled job actually ran and advanced the archive.

Registration doesn't prove discovery; discovery doesn't prove a real query. Matching payload shapes don't prove metric meaning. Current field mappings were checked against one account's seven-day archive; values still need comparison with Connect.

`save-key` tests mock authentication and use disposable files. They don't verify a provider's secret-entry facility. Report compatibility through the [setup template](../.github/ISSUE_TEMPLATE/setup-report.md), without private data.

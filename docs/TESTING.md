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

[CI](../.github/workflows/tests.yml) runs the locked offline suite on macOS, Windows and Ubuntu with Python 3.12 for PRs. Each OS job also builds and smoke-tests an installed wheel with charts. Ubuntu additionally checks the installed wheel without chart dependencies. The smoke script creates a separate environment for each installation, so the basic-install check excludes charts even though the checkout has them installed.

The default branch's GitHub ruleset requires `tests (ubuntu-latest)`, `tests (macos-latest)` and `tests (windows-latest)` from GitHub Actions, with the PR up to date with its base branch. Keep these job names aligned with the ruleset when editing CI. New commits cancel obsolete runs for the same PR.

Pushes to `main` run only an Ubuntu package build and installed-wheel smoke checks with and without charts. The full suite and three-OS checks belong before merging; the post-merge check validates packaging for the final commit without repeating the full matrix. Main runs do not cancel an in-progress main run. There is no deployment or publication step, or separate lint, format or type-check gate. See [compatibility boundaries](COMPATIBILITY.md) before treating offline results as live-host support.

CI enables the optional `charts` extra so rendering tests run on every OS. To match locally, add `--extra charts` to both `uv sync --locked` and `uv run --locked`.

CI also passes `--durations 10` to unittest to report the slowest tests. Chart and CLI-query tests seed a closed synthetic archive once per class and copy it into a fresh temporary directory for each test. This avoids repeated database commits during fixture setup while preserving independent archives. Demo generation, archive writes and sync behavior still have dedicated tests using real writes; database durability settings are unchanged.

For coordinator automation, [`.crumb/coordinator.json`](../.crumb/coordinator.json) lists the offline release checks as argument arrays with timeouts. A coordinator runner can record the exact revision and configuration used, keep logs outside the repository and stop on a failed check. The ordinary commands documented here remain available without that optional tooling. Passing local checks does not replace required GitHub checks, review of accepted handoffs or public-content inspection.

## Focused checks

Use `uv run python -m unittest discover -s tests -p '<file>' -v`:

| Change | Test file |
| --- | --- |
| Installer, key import, registration, handoffs | `test_install.py` |
| Scheduling and rollback | `test_schedule.py` |
| Catch-up and recovery | `test_catchup.py` |
| Archive, FIT decoding, sync | `test_archive.py` |
| Scaled FIT sensors, zero/invalid readings, session/lap/event messages and multiple FIT files | `test_fit_corpus.py` |
| Body Battery descriptors, sample order, dates and failed refreshes | `test_body_battery.py` |
| Sleep summaries, source timestamps and missing stages | `test_sleep.py` |
| Setup receipts, installed guidance and routine templates | `test_onboarding.py` |
| All 26 Personal API routes, field catalog, native pagination/series, source snapshots and older archives | `test_api_data.py` |
| All 25 JSON sources through SDK collection and complete paged query round trips; empty/error recovery | `test_contract_corpus.py` |
| Metrics and missingness | `test_queries.py` |
| Read-only CLI queries | `test_cli_queries.py` |
| Chart semantics and branding | `test_charts.py` |
| Versioned demo answers, DST and archive provenance | `test_demo_provenance.py` |
| MCP image/brand resource transport and chart failures | `test_chart_delivery.py` |
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

For sleep acceptance, use the generated demo and render `chart sleep` in both chat and wide layouts. Verify stage stacks only for complete/reconciled breakdowns, independent score coverage/axis, masked failed refreshes, source/date notes and actual image delivery. Test empty, single-day and sparse periods. Before claiming live field validation, compare a representative night (including source timestamps and scores) with Garmin Connect. Provider routine creation is separate from observing its first execution.

For host-level delivery acceptance, use the synthetic archive and the actual assistant and image interface. Ask “How was my sleep this week?” and verify the final answer includes the delivered sleep chart, dates and coverage; a generated file or local path alone does not pass. Repeat with an explicit text-only request (no image), sparse or missing data (no misleading trend; gaps remain missing), and unavailable rendering or delivery (explain the limitation and provide a concise table). Record the host, installed revision, conditions and outcomes. These checks exercise assistant choice and host delivery; renderer and MCP unit tests cannot establish either.

For Body Battery, use descriptor permutations, missing/duplicate descriptors, out-of-order and conflicting timestamps, invalid samples, partial-day coverage and failed retained data. Compare `body-battery`, `day`, `trend` and MCP fields. Verify source observation times remain distinct from fetch times. Sleep-need tests must distinguish adjusted/baseline minutes, independently dated next-night need, invalid units/types and hour conversion in charts. Installed-wheel smoke checks exercise both new summaries.

Personal API contract coverage is checked offline using all documented paths through the official SDK and a fake HTTP session. The catalog contains the reviewed response definitions; count assertions and traversal detect accidental omissions. Pagination tests include large arrays, escaped keys, long Unicode strings, unknown fields, and explicit coordinate opt-in. This does not establish live field availability. See [coverage and maintenance](API_COVERAGE.md).

### Synthetic corpus

`tests/corpus.py` holds reusable, deterministic fixtures generated without account data:

- Contract-derived responses populate declared properties, nested arrays and typed open maps for all 25 JSON sources, including activity search results. Date/time formats get parseable example strings. Unknown extensions exercise signed numbers, zero, both booleans, null, empty containers/strings, large integer IDs, Unicode and escaped/empty JSON Pointer keys. Unsupported schema shapes fail explicitly; recursive object references stop at cycles.
- FIT bytes include heart rate, power, cadence, distance, enhanced speed/altitude, temperature and invented coordinates, plus session/lap/event messages. Independent expectations verify decoding scales, zeroes, invalid sentinels, original-byte retention, full-field access and coordinate omission from default records. Multiple FIT files exercise overlapping timestamps and running/cycling sessions without silently combining records.

The JSON corpus goes through fake HTTP responses and the official SDK into a temporary archive. Tests reconstruct entire responses using bounded native query pages, following pagination and expanding large children; exact JSON comparison checks every generated value and preserves type distinctions such as false versus zero. All daily and snapshot sources also exercise unchecked, empty, failed-retained and recovered states. The FIT corpus goes through sync, decoding, storage and CLI queries. Query checks leave archive bytes unchanged.

These transport fixtures complement the hand-written domain cases in `test_sleep.py`, `test_body_battery.py`, `test_queries.py` and `test_api_data.py`. The chart demo checks every named interpreted metric and coverage gaps. Contract-derived values do not establish physiological validity, vendor-pattern compliance, cross-field consistency, every enum combination or live availability. Device-specific FIT messages/developer fields and Garmin Connect comparisons remain separate coverage; no test corpus proves every possible recording.

The v2 demo generator emits `known-answers.json` independently of production queries. `test_demo_provenance.py` compares full selected series, masking, means and coverage and pins the default manifest fingerprint; changing expected answers requires deliberate corpus-version review. It exercises 90/91-day boundaries, empty/all-missing archives, independently failed datasets, nap consistency/detail gaps, stage/score/need gaps, Body Battery ambiguity and a separate metric/DST profile. The contract corpus tests transport shapes, not physiological realism.

`test_chart_delivery.py` exercises real stdio PNG/JSON transport and typed brand resources, with read-only file/database checks. Installed-wheel smoke checks cover chart-enabled and chart-unavailable MCP behavior. These do not prove that a host displays image content. Key dry-run tests require no authenticator or writes; timeout tests use synthetic exceptions and verify progress/error redaction. Native Windows ACL validation and a real provider secret facility remain separate live-host checks.

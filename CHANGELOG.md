# Changelog

## 0.1.0 — November 5, 2026

First tagged release of Garmin Data Workbench: a local-first Python workbench
for archiving Garmin health and activity data and querying it through the CLI,
local stdio MCP, SQL or exports. This release packages the existing implementation;
release preparation adds documentation and acceptance reports only.

### Included

- Official Personal API collection covering the 26 documented GET endpoints,
  preserving returned source JSON and original activity files in a local archive.
- Shared daily, trend, sleep and Body Battery queries with units, inclusive dates,
  freshness and coverage. Failed refreshes mask retained values; missing data is
  distinct from zero.
- Deterministic period comparisons, date/native-sport activity filtering, and
  daily/Monday-week workout distance and duration totals with per-field coverage.
- Optional branded PNG charts, a detailed sleep overview, structured CLI chart
  captions via `--json`, and MCP PNG/caption transport.
- Guided setup, local assistant handoffs, opt-in macOS scheduling and catch-up,
  read-only discovery commands, and an isolated generated-data demo.

### Install or upgrade

Requires Python 3.12+ and uv. For a new release installation:

```sh
git clone --branch v0.1.0 --depth 1 https://github.com/0xBreadguy/garmin-data-workbench.git
cd garmin-data-workbench
uv tool install --from '.[charts]' garmin-data-workbench
garmin-archive --version
garmin-archive version
```

Omit `[charts]` for an installation without rendering dependencies. This is a
source/GitHub release, not a PyPI publication. Downloadable wheel and source
distribution assets are accompanied by `SHA256SUMS` on the GitHub release.

For an existing installation, first identify the execution host, archive path,
installed executable and whether charts are enabled. Keep the old checkout and
create a separate checkout of the tag. On that same host, after choosing to
replace its existing uv tool installation, run from the new checkout:

```sh
uv tool install --force --from '.[charts]' garmin-data-workbench
garmin-archive version
```

Keep the charts extra if you use charts. This replaces the installed tool; it
does not run setup, sync or change the archive schema. Preserve credentials,
archives, client registrations and jobs. Verify the executable/archive paths
used by existing clients and schedules afterward; do not register a duplicate
server or create another job. An editable/development environment or a different
installation manager needs its own update route; do not overwrite it blindly.

Early checkout users should note the CLI's deliberate validation changes:
dates require exact `YYYY-MM-DD`, activity/record page limits are at most 10,000,
and SQLite IDs must fit a signed 64-bit integer. See the
[CLI audit](docs/reviews/2026-11-04-cli-audit.md). There is no schema migration in
the release preparation.

### Verification and boundaries

The product baseline `2377478` passed 171 offline tests and required macOS,
Windows and Linux CI, including package and installed CLI/MCP smoke checks.
The documentation-only release candidate must pass those release gates again
before tagging. See [release checks](docs/RELEASING.md) and the
[current acceptance snapshot](docs/COMPATIBILITY.md#release-acceptance--november-5-2026).

- Muse delivered synthetic CLI answers and visible charts after a reported
  isolated setup. An older Grok session did the same; a fresh Grok bot was blocked
  before installation. VM revision and filesystem receipts remain assistant-reported.
- A real Claude Code print-mode session verified MCP discovery, model-selected
  queries and PNG/caption transport. **Graphical MCP image display was not tested.**
- Some assistant comparisons, denominators and captions needed clarification.
  Correct query output does not guarantee an assistant will use it faithfully.
- Built-in scheduling is macOS-only. Linux/Windows schedulers and provider
  routines require separate configuration and actual execution verification.
- Windows offline tests do not validate private ACLs for real keys and health
  archives. Live Windows privacy/setup remains unverified.
- Controlled restart persistence, live Garmin/Connect field validation and
  unattended execution were not tested in this release acceptance round. Dot's
  end-to-end handoff and hosted/remote MCP paths remain separately unverified.

Start with the [isolated synthetic setup](docs/SETUP.md#mock-only-setup-stop-before-credentials).
Choose the command/archive host before live setup; keep credentials and health
archives outside the repository. No hosted website or public MCP service is
included. Independent project; not affiliated with or endorsed by Garmin.

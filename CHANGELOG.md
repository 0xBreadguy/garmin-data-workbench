# Changelog

## 0.2.0 — November 8, 2026

Adds experimental interactive chart routes and tools for agents to build the
chart a question needs. The CLI, local MCP queries and SQLite archive remain
the foundation; PNG delivery is still available without an interactive host.

### Added and improved

- Experimental MCP Apps sleep/recovery explorer: a packaged, self-contained UI
  over read-only shared sleep, trend and comparison queries, with linked date
  selection, night details and independent coverage for each metric.
- Muse native HTML widgets and Grok native React Pages over the same bounded
  1–90-day snapshot. Grok exports include compact transport, ordered bounded
  native edits and source-verification/recovery instructions.
- Archive-free `chart-kit` exports for Muse and Grok: chart rules, brand tokens,
  working starters and reference explorers so agents can build views beyond
  the fixed sleep/recovery layout.
- A shared brand palette across PNG and interactive charts, clearer PNG labels,
  dates, summaries and missing-data marks, and the approved README wordmark.
- Approved real README conversation/chart captures with recorded provenance.
  The chart remains an unchanged historical renderer capture, not a v0.2.0 render.
- Clarified private environment/file key delivery and the proposed Muse
  complete-header entry format. The Muse vault adapter is not implemented;
  these documentation changes do not add a supported authentication route.

### Install or upgrade

Requires Python 3.12+ and uv. Use a new checkout of the release on the execution
host you chose for the archive:

```sh
git clone --branch v0.2.0 --depth 1 https://github.com/0xBreadguy/garmin-data-workbench.git
cd garmin-data-workbench
uv tool install --from '.[charts]' garmin-data-workbench
garmin-archive --version
garmin-archive version
```

For an existing uv tool installation, identify its executable, archive path and
chart requirements first. Keep the old checkout, then run from the new checkout
on that same host when ready to replace the installed tool:

```sh
uv tool install --force --from '.[charts]' garmin-data-workbench
garmin-archive version
```

`[charts]` installs Matplotlib for PNG rendering. The MCP App, native widget/Page
exports and `chart-kit` need only the base package; omit `[charts]` if PNG is not
needed. Python users need no Node runtime or CDN for these exports. A compatible
assistant delivery surface is still required. This is a source/GitHub release,
not a PyPI publication; release assets are the wheel, source distribution and
`SHA256SUMS` built from the clean tagged revision.

Upgrading the tool does not run setup or sync. Preserve the archive, original
activity files, source JSON, credentials, client registrations and scheduled
jobs. No archive rebuild or schema migration is required for v0.2.0; the
collector, storage schema and metric definitions are unchanged from v0.1.0.
Check the executable/archive paths used by clients and jobs after upgrading;
do not register a duplicate server or create another schedule. Editable or
other installation managers need their own update route.

### Experimental delivery and known limits

- MCP Apps, Muse HTML widgets and Grok Pages are separate delivery routes, not
  interchangeable HTML/TSX attachments. Exports do not establish native display.
  See the [route index and evidence](docs/COMPATIBILITY.md#interactive-chart-routes-in-v020).
- Muse Mac widget interaction was directly observed; physical-phone interaction
  was user-reported. The packaged Grok explorer was observed in the Mac app's
  dark theme, including sparse data. Grok native light theme and phone/touch
  delivery remain unverified. Browser harnesses and stand-ins are separate evidence.
- MCP Apps desktop display was user-reported; delivery from phone-created
  conversations remains unresolved. Controlled host-restart persistence and
  cross-device state remain unverified for the interactive routes.
- Native Muse/Grok views embed a fixed snapshot. Ask for a new export when dates
  or observations change. Agent-authored charts require their own query,
  semantic and delivery checks; a passing starter harness does not validate a
  newly authored chart.
- Grok's native writer can introduce transcription errors that still compile.
  Follow the bounded delivery plan and compare actual readback bytes when
  available. Native compiler/style behavior is host-specific and may change.
- Built-in scheduling remains macOS-only. Live Windows credential/privacy
  validation, additional assistant connections, live Garmin/Connect comparisons
  and actual unattended execution need separate evidence. No hosted website or
  public MCP service is included.

Release verification follows the [release checklist](docs/RELEASING.md): the
full offline suite, installed-wheel checks and required three-OS CI. Historical acceptance reports describe
the revisions they tested; they are not a new v0.2.0 live acceptance run.
Independent project; not affiliated with or endorsed by Garmin.

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

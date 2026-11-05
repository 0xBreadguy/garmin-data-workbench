# Launch readiness review — November 5, 2026

Reviewed public `main` at `47dcd68`, then prepared the local launch-review changes described below. This is a repository/code/offline review, not a new live Garmin installation or an independent security audit.

The repository is a sound base for an early public release after the dependency fix is merged and the required platform checks pass. Keep live Windows and assistant-connection limits explicit. There is no reason to reorganize the Python package or add a new service before launch.

## Findings and disposition

| Priority | Finding | Disposition |
| --- | --- | --- |
| Before release | Locked `filelock` 3.32.7 returned 13 known advisories. The `<4` constraint excluded patched releases. | Changed the supported range to `>=4.2.1,<5`; lockfile resolves 4.2.9. The complete locked runtime set, including charts, now returns no known advisories. |
| Before broad promotion | GitHub secret scanning, push protection, dependency alerts, automated security updates and private vulnerability reporting were disabled when inspected. | Enable the relevant repository settings with maintainer authorization. `SECURITY.md` has a safe fallback, but a direct private reporting route is preferable. No settings changed during this review. |
| Before release | No GitHub release/tagged release was listed; visitors cannot identify a supported launch snapshot. | Added [release instructions](../RELEASING.md). Cut `v0.1.0` from the verified final revision with capabilities, upgrade instructions and limits. Publication is still pending. |
| Fixed locally | README described the archive but showed no result and buried the no-key route. Chart dependencies were easy to miss. | Added a synthetic sleep preview, a mock-only prompt, optional charts installation, early-version wording, support boundaries, CI badge and report links. |
| Fixed locally | Package metadata omitted the README, license expression and project links. The upgrade example could remove a previously installed charts extra. | Added metadata; documented preserving `.[charts]` on upgrades. Added ignore rules for `.sqlite` sidecars and macOS Finder files. |
| Fixed locally | Contributor guidance lacked a task-to-module/test map and recommended a base environment that skips rendering tests. | Expanded [CONTRIBUTING.md](../../CONTRIBUTING.md) with chart-enabled setup, contribution boundaries, focused verification, PR expectations and release guidance. |

The most directly relevant dependency advisory concerns the Unix backend of the `FileLock` used for sync serialization. Exploitation requires local filesystem conditions such as another account being able to replace/link lock-path entries. Several other reported advisories affect lock types this project does not use. This is not evidence of remote compromise. See [the upstream advisory](https://github.com/tox-dev/filelock/security/advisories/GHSA-69hj-f68j-2879) and [patched release notes](https://github.com/tox-dev/filelock/releases/tag/4.2.1).

## Structure and contribution assessment

The `src/garmin_archive/` package, separate `tests/`, user-facing `docs/`, synthetic helper `scripts/`, reusable `skills/` and small `assets/` directory are appropriate. Collection, archive writes, query definitions, rendering, adapters and host-specific behavior already have named modules. Keep those boundaries and the single shared metric implementation. The wheel contains the runtime package and fixed brand resources; contributor material stays in the source distribution/repository.

Existing bug, feature, setup and PR templates are useful and avoid requesting personal archives. MIT licensing and contributor instructions are present. An active default-branch ruleset requires PRs, an up-to-date base and all three OS test jobs, with no bypass actors. At inspection, there were no open PRs; public main's package smoke and the preceding PR matrix were successful.

As the project grows, split code when a concrete feature needs it. `cli.py` is the largest module and currently owns parser/output/setup orchestration. If CLI and MCP response construction starts diverging, move that behavior into shared query helpers with parity tests. A wholesale package rewrite, new framework or new database would add launch risk without resolving a demonstrated problem.

## Verification evidence

- Baseline and updated-dependency suites: all 161 tests passed with charts enabled on macOS/Python 3.12.13. Tests cover collection with fake responses, archive compatibility, metrics/missingness, FIT, CLI, MCP transport and rendering.
- Source/wheel builds and installed-wheel CLI/MCP smoke checks with and without charts passed for both the reviewed baseline and the updated candidate. Package metadata and required installed guidance/contract/brand resources were inspected.
- `pip-audit` checked all 46 locked runtime dependencies including charts: baseline reported 13 advisories in `filelock`; the updated set reported zero. This is a dated known-advisory check, not proof of security.
- Actual two-process `FileLock` exclusion, reacquisition after the holder exits, and acquisition with a legacy empty lock file passed with 4.2.9. No Garmin authentication or archive sync was involved.
- `detect-secrets` scanned tracked files and 357 distinct reachable historical text blobs across the baseline's 101 commits. Five unique candidates were reviewed as metadata, fake test literals or checksums. One binary blob was skipped. No actual credential was identified by these scans; unknown patterns and arbitrary sensitive data remain outside that guarantee.
- Reviewed storage/read-only boundaries, credential import/redaction, retry/stop behavior, subprocess argument handling, schedule preservation, native pagination/location omission, source-unit/date semantics, package contents, templates and public-facing docs. No real key, token cache, health archive or scheduled job was used.
- Generated and visually inspected the README sleep example from default synthetic corpus v2, seed 42, April 24–30, 2026. Synthetic labels, separate score panel, units and coverage are visible. This does not test image display in a new assistant host.
- Both documented `uv tool install` selectors (`.[charts]` and `.`) passed in isolated disposable tool/bin directories. Replacing the chart-enabled install with the base package removed chart availability, confirming the need for the corrected upgrade guidance. Existing installed tools were untouched.
- Local documentation targets/heading anchors and `git diff --check` checked. The GitHub-rendered revised README has not been inspected because these changes are local.

The dependency update still needs the required Windows/Linux/macOS PR matrix. Prior cross-platform CI covers the baseline, not this new dependency revision. Live Windows ACL/credential handling, a fresh end-to-end assistant connection on the final revision, restart persistence and actual recurring execution remain separate checks. Existing acceptance reports document their specific paths and limitations; do not broaden those claims.

## Rollout priorities

1. Merge the reviewed security/documentation changes after required CI. Enable the GitHub protections and private reporting route, then publish the verified `v0.1.0` snapshot with concise release notes.
2. Lead the announcement with one useful question and one visible result. Link directly to the README's synthetic demo and setup paths. For edited/recreated launch conversations, label the presentation accordingly; keep real observations distinct from scripted examples.
3. Position this as a personal Garmin archive and an agent analysis interface. Garmin describes the Personal API as individual access to one's own data, rather than a commercial multi-user integration; see [Garmin's FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/). Keep the existing non-affiliation statement.
4. Collect a small first wave of sanitized setup reports with OS, Python, installed revision and the specific CLI/MCP/assistant path. Use those reports to prioritize onboarding work. A successful synthetic chart is not evidence of secure live setup or working automatic sync.
5. Add repository discovery topics for the actual agent/CLI use cases (for example `mcp` and `python`) and a custom social preview using approved assets. Keep GitHub Issues as the initial support path; a new support channel or community service is not a launch prerequisite.

## Suggested first release description

Garmin Data Workbench keeps your Garmin health and activity data in a local SQLite archive, with source JSON and original activity files retained. Query sleep, Body Battery, heart rate, steps and activities through the CLI or local MCP tools, or use SQL and CSV for your own analysis. Optional charts use the same shared query definitions and show coverage and missing data.

Start with the synthetic demo without a Garmin key. For live use, choose the archive host and follow the setup guide. This early release has built-in scheduling on macOS; other hosts need their own scheduler. Windows live credential/privacy validation and additional assistant paths still need separate verification. Independent project; not affiliated with Garmin.

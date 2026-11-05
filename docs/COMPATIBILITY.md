# Host compatibility

The core workbench targets macOS, native Windows and Linux with Python 3.12+.
Keep one archive on a chosen host; assistants use its CLI or a supported MCP
connection. Cross-platform support does not require sharing a writable SQLite
archive between machines.

## What is checked

[CI](../.github/workflows/tests.yml) targets `macos-latest`, `windows-latest` and
`ubuntu-latest` with Python 3.12 on PRs. Each OS job runs the offline suite, builds a wheel,
installs it into a disposable environment and checks the installed commands and
synthetic CLI/MCP queries. The smoke check uses paths containing spaces,
non-ASCII characters, apostrophes and a `#`, and checks that queries leave the
archive unchanged. It needs no Garmin account or assistant account.

Ubuntu also verifies installation without the optional chart dependencies.

When charts are installed, the Windows MCP entry point initializes NumPy before
starting the stdio reader, avoiding an [upstream native-import deadlock](https://github.com/numpy/numpy/issues/24290).
The basic installation still requires no plotting dependencies.

After merging, only the Ubuntu build and installed-wheel smoke checks run;
the full three-OS validation is required before merging. See [testing](TESTING.md)
for the GitHub merge requirements and cancellation behavior.

These are automated test targets, not a claim that every OS version, CPU
architecture, assistant or live setup has been verified. Use the results for
the exact revision being installed. macOS has prior local/live usage; Windows
and Linux live setup need separate reports. See [testing](TESTING.md) and the
[setup report](../.github/ISSUE_TEMPLATE/setup-report.md).

## Release acceptance — November 5, 2026

The `v0.1.0` release includes the following synthetic acceptance reports at
product source revision `2377478a9aded1951f917e32754e44e8c6ddaab5`.
The release preparation adds documentation only. These are bounded observations,
not certification of every assistant or live host setup.

| Surface and path | Result and limits |
| --- | --- |
| [Muse native app, CLI](acceptance/2026-11-05-muse-release-verification.md) | Reported isolated current setup in its Ubuntu VM without setup coaching; two actual sleep images opened. Comparisons, workout totals and missing-data answers passed. Some first statistical wording needed correction; host disclosure and complete path handoff arrived late. VM revision, import and preservation receipts remain assistant-reported. |
| [Grok Bot native app, CLI](acceptance/2026-11-05-grok-release-verification.md) | Fresh bot blocked before installation by a reported authenticated-checkout requirement. An authorized older-session recovery reported an isolated current setup in its Debian VM and delivered an opened sleep image and correct synthetic answers. It calculated initial comparisons itself; shared `compare` output matched only on a post-hoc check. VM claims remain assistant-reported; this is not a fresh-bot pass. |
| [Claude Code 2.1.318, local MCP](acceptance/2026-11-05-mcp-client-release-verification.md) | Real print-mode client discovered a session-only synthetic server and made model-selected sleep, comparison, workout and chart calls. PNG/caption transport and read-only archive hashes passed. Clean-stdin recovery and narrow test permissions are recorded separately. Visible graphical image display was not run. |

Default-demo workout gaps were recorded before separately requested synthetic
workout scenarios exercised positive totals. No personal archive or live Garmin
request was used. Controlled restart persistence, live setup, recurring execution
and graphical MCP image display remain unverified in this round. CLI attachment
success does not establish MCP display. Some assistant answers omitted available
caption/freshness details or qualified statistics only after clarification;
guidance cannot guarantee adherence. Earlier Dot access remains blocked as
recorded below; no new Dot run was performed.

## Assistant acceptance snapshot

November 4, 2026 synthetic checks at source revision `28e2aa9`; reports:
[Muse](acceptance/2026-11-04-muse-fresh-install.md) (`b143cd0`),
[Grok](acceptance/2026-11-04-grok-fresh-install.md) (`433b492`), and
[Dot](acceptance/2026-11-04-dot-fresh-install.md) (`edc6ccb`). These results cover the
tested surface and path, not every integration or later revision. App access,
visible answers and opened images were directly observed; command execution,
installation state and VM details below were assistant-reported.

| Surface | Command host | Result and limits |
| --- | --- | --- |
| Muse Mac app | Reported Ubuntu 24.04.5 VM | Synthetic CLI answers and visible sleep/steps images passed. Reported fresh clone/tool install; new side chat retained assistant context. Controlled persistence not run. |
| Grok Bot Mac app | Reported shared Debian 13 VM | Synthetic CLI answers and four visible chart attachments passed. Fresh conversation reused/updated an existing clone; prior environment state unknown. Isolated fresh install not run; prior setup preservation unverified; interpretation needed correction. Controlled persistence not run. |
| Dot, intended ChatGPT assistant | Unknown | Blocked before first prompt; all workbench stages not run. Inventory listed ChatGPT (`com.openai.codex`); app selection was denied for safety before UI inspection. Dot mode unverified. |

Neither CLI run exercised MCP discovery, queries or image transport. Live
Garmin/key entry and recurring execution were excluded from these checks.
The UI's Mac OS does not establish Mac-local installation or storage.

Dot's result is an external test-tool access blocker, not a product failure.
No alternate surface or bypass was attempted. Retest through a supported,
authorized Dot surface once access is resolved; do not infer support from
inventory, existing controller binaries or offline tests. Use the
[stage-by-stage reporting guidance](TESTING.md#assistant-acceptance-reports)
to keep blocked, not run, failed and passed results distinct.

Focused follow-up at `10672e4` verified readable current-version sleep labels
in both apps. [Grok's retest](acceptance/2026-11-04-grok-post-merge-retest.md)
still needed corrections to prose arithmetic and sampled-level wording.
[Muse's retest](acceptance/2026-11-04-muse-post-merge-retest.md) initially used
its old installation, then delivered correct current-version CLI answers and
images after a separate-setup clarification. VM installation/preservation
details remained assistant-reported. These retests did not exercise MCP,
controlled persistence or live Garmin, and do not validate the later CLI and
guidance changes made in response.

## Current boundaries

| Area | Behavior |
| --- | --- |
| Commands and archive | Shared Python implementation; SQLite on a local filesystem |
| Windows command examples | Generated launch commands use PowerShell, including its `&` call operator |
| Paths | Existing defaults remain unchanged; `~` means the current user's home on each OS; custom archives use `--data-dir` |
| Scheduling | Built-in setup is macOS-only; manual sync works independently of scheduling |
| Other schedulers | Windows Task Scheduler, cron/systemd or provider routines must be configured separately |
| Assistant connections | CLI, local stdio MCP and the separately documented remote paths; see [assistants](ASSISTANTS.md) |
| ARM64, WSL, other Linux distributions | Need their own installation/runtime evidence; the three runner labels do not cover every combination |

POSIX creation modes protect new files on macOS/Linux. The workbench does not
currently enforce or validate Windows ACLs. Passing Windows offline tests does
not establish private storage for a live installation. Before using a real key
or syncing health data on Windows, the key, token-cache and archive directories
must have independently verified access restricted to the intended user and
required system accounts. The existing `0600`/`0700` modes alone do not provide
that verification. Native Windows credential/privacy validation remains a
release gap.

Agent VMs and containers need persistent local storage, verified private secret
entry and a usable execution/connection path. Recurring execution also needs
an OS scheduler or provider routine that survives sessions. An ephemeral
sandbox or a browser/mobile conversation should use a supported connection to
an appropriate archive host. A product name alone does not establish those
capabilities. Follow [setup](SETUP.md) before live use.

## Development rule

New shared features must keep the three-OS offline checks passing. Keep OS
differences at small boundaries such as `platforms.py` and the macOS scheduler;
launch subprocesses with argument lists and use shell rendering only for
copyable examples. Platform-only assertions should test the relevant OS
contract without skipping shared sync, query, FIT or MCP behavior.

Additional schedulers and named assistant integrations can be added when
needed. Installation, discovery, live sync, real assistant queries and actual
scheduled execution remain separate verification steps.

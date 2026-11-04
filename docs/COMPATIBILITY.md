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

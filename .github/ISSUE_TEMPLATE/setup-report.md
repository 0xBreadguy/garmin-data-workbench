---
name: Host or assistant setup report
about: Share setup results or friction using the generic setup guide
title: ''
labels: ''
assignees: ''
---

## Environment

- Installed source revision (may differ from checkout), Python version and install method:
- Intended assistant and actual authorized app/browser surface (or access blocker):
- UI OS; actual command host/OS and storage (local, VM/container or remote; unknown if not reached):
- Fresh conversation? Residual assistant memory/context present or unknown?
- Fresh install or reused clone/environment/tool? How was prior state checked and preserved?
- First prompt sent? If not, why? If sent, record its scope and first outcome before coaching/follow-ups:
- Persistent storage claimed or tested across a controlled new session/restart? How?
- Local stdio MCP supported, CLI only, or separate remote connection?
- Available scheduler or provider-managed routine, if any:

## Results

Use **passed** (expected behavior demonstrated), **failed** (attempted; expected behavior not met), **blocked** (could not attempt; name the prerequisite), or **not run** (including excluded stages). Label evidence **directly observed** or **assistant-reported**, and state any unknowns. See [reporting guidance](../../docs/TESTING.md#assistant-acceptance-reports).

No live data or credentials are needed for an offline report. Inventory presence is not assistant access; CLI success is not MCP success; a file/path is not visible image delivery. Keep unexercised stages **not run** after an access blocker.

| Stage | Result | Privacy-safe evidence and limits |
| --- | --- | --- |
| Authorized assistant-surface access | | |
| Command installation | | |
| Offline test suite | | |
| Synthetic CLI query | | |
| MCP discovery | | |
| MCP synthetic query | | |
| MCP image transport | | |
| Actual visible image delivery (name CLI/MCP path) | | |
| Controlled persistence across a new session/restart | | |
| Optional live sync and coverage check | | |
| Optional real assistant query and comparison | | |
| Optional actual recurring execution | | |

## Friction and workaround

Describe the observed defect or access blocker, expected behavior and supported retest needed. Label hypotheses and assistant adherence gaps. Keep any authorized workaround/follow-up result separate from the first outcome.

## Access model

For cloud setups, was access by other agents/processes using the same OS user explained before syncing? Was secure secret entry available? Describe capabilities only; never include a key, token or secret file contents.

Keep health values, raw responses, routes, original files and identifying host details out of this report. A setup report does not require agreeing to a cloud sync or a recurring job.

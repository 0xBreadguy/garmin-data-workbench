---
name: Host or assistant setup report
about: Share setup results or friction using the generic setup guide
title: ''
labels: ''
assignees: ''
---

## Environment

- Source revision (the installed tool may be older than the checkout):
- OS and Python version:
- Assistant/client and install method:
- Local computer or cloud host:
- Persistent storage confirmed? How was it checked?
- Local stdio MCP supported, CLI only, or separate remote connection?
- Available scheduler or provider-managed routine, if any:

## Results

Mark each stage passed, failed or not tested. No live data or credentials are needed for an offline compatibility report.

| Stage | Result and privacy-safe evidence |
| --- | --- |
| Command installation | |
| Offline test suite | |
| Stdio tool discovery and synthetic query | |
| Optional live sync and coverage check | |
| Optional real assistant query and comparison | |
| Optional actual scheduled execution | |

## Friction and workaround

Which instruction or command failed? What did you expect? If there is a client-specific difference, describe how to reproduce it.

## Access model

For cloud setups, was access by other agents/processes using the same OS user explained before syncing? Was secure secret entry available? Describe capabilities only; never include a key, token or secret file contents.

Keep health values, raw responses, routes, original files and identifying host details out of this report. A setup report does not require agreeing to a cloud sync or a recurring job.

# Muse compatibility

User-supplied report against `117a11c`, November 1, 2026. These findings cover one VM; repository tests don't independently verify that host.

| Area | Reported result |
| --- | --- |
| Host | Ubuntu 24.04, Python 3.12.3, persistent home; checkout under `/tmp`; commands ran as root |
| Offline checks | uv 0.13.6 at `~/.local/bin/uv`; locked install, 52 tests and both help commands passed |
| Installation/data | No persistent tool install, key or live archive; uv bin absent from `PATH` |
| Query access | Shell available, no direct MCP client; Codex present without registrations |
| Scheduling | Built-in scheduler `unsupported`; no crontab or systemd user bus |
| Secret entry | Non-TTY shell; no verified private facility |

## Available path

Muse can query through `day` and `trend` on the archive VM. No Codex registration required. `assistant-guide --client muse` prints absolute executable/archive paths; it doesn't establish a remote connection.

`save-key --from-file` imports an already-delivered private key and validates it through Garmin. It doesn't provide private entry. These commands have offline tests; live Muse setup and a provider routine remain unverified.

## Next checks

1. Accept the [host access model](SETUP.md#1-choose-where-the-data-lives). Same-user and privileged processes can access private files. Install persistently, outside `/tmp`; find binaries with `~/.local/bin/uv tool dir --bin` on this reported host.
2. Test the provider's private secret facility with a dummy value. Stop before requesting a Garmin key if none exists; don't use chat or logged input.
3. Import the privately delivered key with `save-key --from-file`, then dispose of the source through that facility. Authentication updates credentials/cache but doesn't sync health data.
4. Sync one chosen day, inspect `status`, query with `day`/`trend` and compare a result with Connect. Follow [setup](SETUP.md#3-supply-a-key-and-run-a-first-sync).
5. Keep manual sync until an interval is chosen. A provider routine needs persistent executable, archive and key paths; verify an actual run separately.

Record the installed revision and each outcome. Updating a checkout requires [reinstalling the tool snapshot](SETUP.md#2-install-the-commands).

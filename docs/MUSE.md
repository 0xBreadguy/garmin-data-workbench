# Muse compatibility notes

Muse reported these findings against revision `117a11c` on November 1, 2026. They describe one cloud VM, not a guarantee about every Muse environment. The report was supplied by the user; repository development tests do not independently verify that VM.

| Stage | Reported result |
| --- | --- |
| Host | Ubuntu 24.04, Python 3.12.3, persistent home storage; temporary checkout under `/tmp` |
| Offline development | uv 0.13.6 installed at `~/.local/bin/uv`; locked dependencies installed, 52 tests passed, both CLI help commands worked |
| Installed commands | No persistent tool installation yet; uv's bin directory was absent from `PATH` |
| Key and live archive | Neither existed; no credential requested or sync attempted |
| Assistant access | Muse could run shell commands but had no direct MCP client; Codex CLI was present with no MCP servers configured |
| Scheduling | Built-in scheduler returned `unsupported`; no crontab and no available systemd user bus in that session |
| Secret entry | Shell was not a TTY; no tested private secret-entry method had been found |

Commands reportedly ran as root. Owner-only file modes do not isolate credentials or health data from other processes with the same user or from privileged processes. Follow the host-choice discussion in [SETUP.md](SETUP.md#1-choose-where-the-data-lives) before any live authentication or sync.

## What the workbench provides

- `save-key --from-file /private/provider-secret` imports a key delivered by a verified secret facility. It validates through Garmin, saves an owner-only key file and refuses replacement. It does not create a secret-entry facility.
- `day` and `trend` return the same bounded, preference-aware summaries as MCP without credentials or live requests. Muse can use them through its shell on the archive VM.
- `assistant-guide --client muse` prints a same-host CLI handoff with absolute executable and archive paths. It does not register Codex or create a remote connection.

These paths have offline coverage with synthetic archives and mocked authentication. A successful Muse live query, private key delivery and a provider-managed routine remain unverified.

## Next test on the selected VM

1. Confirm the user accepts this host and its access model. Use a persistent checkout and tool installation; find the tool bin directory using the absolute uv executable (`~/.local/bin/uv tool dir --bin` in the reported environment).
2. Identify and test a supported private secret facility with a disposable dummy value. Never use chat, literal command arguments or logged terminal input. If no facility exists, stop before requesting a Garmin key. A private file import only helps after delivery is solved.
3. With the user's real key privately delivered, run `save-key --from-file` using absolute paths. This makes live authentication/profile requests but no health sync. Dispose of the temporary secret source through the provider facility. Keep the saved key and token cache outside the checkout.
4. Run a user-selected one-day sync, inspect `status`, then ask Muse a question answered with `day` or `trend`. Compare a result with the archive and Garmin Connect. Follow the commands in [SETUP.md](SETUP.md#3-supply-a-key-and-run-a-first-sync).
5. Keep manual sync until the user chooses an interval. If using a provider routine, give it the same absolute executable and archive paths and ensure the key persists. Verify an actual execution separately; built-in Linux scheduling remains unsupported.

No Codex registration is needed for the Muse shell path. Updating a checkout does not update a uv tool snapshot; reinstall as described in [SETUP.md](SETUP.md#2-install-the-commands). Record the tested source revision and report installation, private key delivery, sync, assistant query and scheduling as separate outcomes.

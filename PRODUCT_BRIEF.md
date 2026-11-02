# Product direction

**Give people and their agents a useful Garmin archive they control.**

Run on a personal computer or persistent remote workstation. Use the official Personal API to collect data; retain source JSON and original activity files. Make the archive useful through MCP, CLI, SQL, scripts, notebooks and exports.

## Who we're building for

| User | What they need |
| --- | --- |
| Agents with remote workstations | Persistent storage, private key delivery, unattended sync and bounded queries through shell or MCP |
| Power users | Inspectable source data, reliable backfills, detailed activity samples, SQL and exports for their own tools |

Both use the same archive and query definitions. Agents are a primary interface; direct access is a first-class workflow.

## Available today

As of November 1, 2026:

- SQLite archive with five health datasets, activity metadata, original ZIPs and decoded FIT messages.
- Resumable sync, catch-up checkpoints, coverage/errors and optional macOS scheduling.
- Five daily/trend metrics, paginated activity samples, CLI exports and local stdio MCP.
- Guided Codex/Claude Code registration, generic workstation setup and assistant handoffs.

A seven-day live sync and a local Codex conversation worked on one machine. Claude Code registration was checked in isolation. Other assistant handoffs and broader platform support need end-to-end tests. [Verification](docs/TESTING.md) separates those claims.

## Product rules

- **Trust the evidence.** Return dates, units, freshness and coverage. Missing isn't zero; failed refreshes aren't current data. Associations don't prove causes.
- **Keep the source.** Preserve original files, unknown fields and timestamp meaning. Use profile units/time zone by default; honor overrides.
- **Let users choose the host.** Explain shared-user access before remote authentication or sync. Keep secrets out of chat and logs. AI providers may receive query results.
- **Keep collection independent.** Queries use the archive without Garmin credentials or live requests. Scheduling is opt-in.
- **Build on measured gaps.** Don't promise complete history, every sensor stream or novelty over existing projects.

## Next priorities

1. Verify metric values and representative watch/Edge recordings against Connect and originals.
2. Improve coverage reporting, sync diagnostics, activity comparisons and sample-gap analysis.
3. Test remote-workstation setup, private secret delivery, real assistant queries and recurring execution.
4. Add historical import or reconciliation only where it fills demonstrated gaps.

Each user operates their own installation with their own key. A hosted multi-user service and first-party dashboard are outside the current direction. See the [data plan](GARMIN_DATA_PLAN.md), [architecture](ARCHITECTURE.md) and [related-project review](EXISTING_PROJECTS.md).

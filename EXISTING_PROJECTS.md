# Existing Garmin projects: overlap and opportunities

Reviewed November 1, 2026. This is a source-and-documentation review of public repository snapshots, not a live test or security audit. No third-party project was run with a Garmin key or personal health data.

## Recommendation

Build an independent public product on Garmin's official Personal API, as requested. The projects below are independent community tools, not products released by Garmin. Overlap with them is useful competitive context rather than a reason to stop. Garmin's [Personal API Python client](https://github.com/garmin/connect-personal-api-python) and [FIT SDK](https://developer.garmin.com/fit/get-the-sdk/) are official Garmin tools we can use as dependencies.

[garmin-connect-personal-mcp](https://github.com/braydenabo/garmin-mcp) already covers much of the proposed archive-and-MCP idea. A promising focus for our own product is **making granular samples from original activity FIT files easy to inspect, compare and query**, with convenient local archiving and transparent data coverage. That is a product hypothesis, not a claim that nobody else offers granular FIT analysis; `garmin-health-data` already parses many of these fields.

Study existing projects' behavior and licenses, then test our own approach with synthetic fixtures and representative user-authorized data. Reuse compatible existing dependencies where they save work. Contributing upstream remains an option, but is not a prerequisite for our independent product.

## Comparison

| Project | What it already does | Fit and gaps for our goal |
| --- | --- | --- |
| [garmin-personal-mcp](https://github.com/Mason-Levyy/garmin-personal-mcp) | MIT-licensed local MCP server using Garmin's official Personal API/client. Exposes health, activity and profile endpoints and can save the original activity download. Key-file location matches Garmin's official client. | Best for quickly asking an assistant questions of the live API. The reviewed source has no local SQLite warehouse or FIT-sample decoder, so a durable offline analysis layer would still be needed. |
| [garmin-health-data](https://github.com/diegoscarabelli/garmin-health-data) | Apache-2.0 CLI that keeps source files and builds a local SQLite database. Its documented FIT processing includes activity time series, GPS, power/cadence, laps, events, swim lengths and R-R intervals when present. | Closest of the original two to granular analysis. It uses its own Garmin Connect SSO/client rather than the official Personal API key, and is a CLI/data store rather than a built-in MCP server. Whether its existing FIT processor can ingest our official-API downloads cleanly requires testing; do not assume the schemas and file lifecycle match. |
| [garmin-connect-personal-mcp](https://github.com/braydenabo/garmin-mcp) | Apache-2.0, alpha project using the official Personal API; has local SQLite, raw daily/activity JSON, activity FIT ZIP downloads, resumable sync, scheduled-sync options, coverage/status tools and an MCP server with activity summaries and charts. | **Closest overall to our proposed product.** The reviewed code saves FIT ZIPs but its activity tools read summary JSON and expose a `fit_file_saved` flag; no FIT decoder or per-record sample query was found. It calls itself alpha. Its documented install is from Git; its client/setup paths still need a hands-on test. |
| [garmin-local-mcp](https://github.com/anup-shesh/garmin-local-mcp) | MIT-licensed local warehouse and MCP with trends, correlations, coverage/gap tools and manual wellness-FIT import. | Another strong overlap, including analytics we had proposed. Uses the unofficial `garminconnect` login/client; its activity tool is summary-only and the README says it doesn't parse FIT *activity* files. |

Primary source details: [personal MCP tools](https://github.com/Mason-Levyy/garmin-personal-mcp#tools), [health-data schema](https://github.com/diegoscarabelli/garmin-health-data/blob/main/garmin_health_data/tables.ddl), [official-API archive sync](https://github.com/braydenabo/garmin-mcp/blob/main/src/garmin_connect_personal_mcp/sync.py), [its activity query code](https://github.com/braydenabo/garmin-mcp/blob/main/src/garmin_connect_personal_mcp/activities.py), and [its MCP tool reference](https://github.com/braydenabo/garmin-mcp/blob/main/docs/tools.md).

## A focused product opportunity

Extend an existing official-API archive with a FIT analysis layer that:

1. Reads an archived original activity file and exposes recorded heart rate, cadence, power, speed, elevation, events and other supported fields **when present**.
2. Reports units, timestamps, sampling gaps and unknown fields, without treating missing samples as zeros. Preserve the original file and distinguish a measured recording from a derived metric.
3. Supports bounded, paginated local queries and CSV export; expose the same query functions through MCP. Keep precise location out of general responses unless requested.
4. Lets users compare segments or similar rides and combine them with nearby sleep/recovery dates. Report sample coverage and avoid implying correlation proves causation.

`garmin-health-data` already does significant FIT parsing, so inspect its existing implementation and Apache-2.0 license before writing a parser. Reuse compatible libraries or code where practical and preserve required notices. Test activity files with synthetic fixtures and known edge cases before relying on real results.

## Decision gates

- **First:** compare the archive project's sync behavior, FIT layout, schema, tests and contribution conventions using its public code and synthetic fixtures. Check how it handles missing days, partial runs, deleted/edited activities, date zones, permissions and rate limits.
- **Second:** verify a bounded activity-sample query and a recovery-plus-ride question work correctly on a representative sample. Real-account access is a separate, explicit test; don't move the user's key into an unreviewed project.
- **Then:** build our independent product around the best user-facing experience we can deliver. Use the competitive review to prioritize real improvements rather than assuming features are novel.

History depth, Personal API rate limits and whether all fields shown in Garmin Connect are returned by the API remain unverified. The archive project's statement about old-day availability should be checked against actual account behavior rather than treated as a universal API restriction.

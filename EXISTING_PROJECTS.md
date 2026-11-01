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

Build on our official-API archive with a FIT analysis layer that:

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

## Expanded review: repeatable sync and agent access

Reviewed November 1, 2026. This is a representative survey of relevant public repositories, not an exhaustive inventory of every Garmin project. It compares their documented behavior and selected source files; we have not run them with credentials or audited their security. Feature claims are project claims unless otherwise noted. Projects and APIs change.

| Project | Useful ideas | Gap or tradeoff for this workbench |
| --- | --- | --- |
| [Garmin's Personal API Python client](https://github.com/garmin/connect-personal-api-python) | Official key/token handling, read methods and original activity downloads. | Building block rather than a maintained offline archive, scheduler or MCP interface. We use it already. |
| [garmin-connect-personal-mcp](https://github.com/braydenabo/garmin-mcp) | Official Personal API plus SQLite, scheduling, setup/doctor, coverage, local MCP, client install and charts. Strongest direct comparison. | Its documented FIT path retains files; the activity tools reviewed use summary data rather than exposing decoded samples. Its claim that old days cannot be retrieved should be tested for each endpoint, not assumed universal. |
| [garmin-personal-mcp](https://github.com/Mason-Levyy/garmin-personal-mcp) | Official API with broad endpoint coverage, automatic date-window splitting, readable responses and multiple client setup examples. | Optimized for live API calls rather than a durable offline archive or FIT-record analysis. |
| [garmin-health-data](https://github.com/diegoscarabelli/garmin-health-data) | Deep local SQLite model, source files and detailed FIT parsing, including available power, cadence, laps and events. | Uses its own Connect login/client; no built-in MCP in the reviewed documentation. Its schema is a useful reference for better local analysis. |
| [GarminDB](https://github.com/tcgoetz/GarminDB) | Long-standing local SQLite, device/Connect imports and notebooks. | A database and analysis toolkit, not the official Personal API-to-MCP workflow described here. |
| [garmin-local-mcp](https://github.com/anup-shesh/garmin-local-mcp) | Local warehouse, trends, gap reports, resumable sync and an offline daily wellness FIT import. | Uses unofficial Connect login; its documentation says it does not parse activity FIT files. Import fallback and explicit source precedence are valuable ideas. |
| [garmin-mcp-local](https://github.com/the-mace/garmin-mcp-local) | Read-only cache-backed MCP, resumable backfill, recent-gap rechecks, persistent rate-limit cooldowns and launchd/watchdog examples. | Uses unofficial Connect access; its cooldown and incomplete-fetch handling are useful reliability targets for us, not features we currently claim. |
| [fitness-data-sync](https://github.com/chrisa84/fitness-data-sync) | Resumable local SQLite mirror, read-only MCP and scheduler examples across platforms. | Uses unofficial Garmin access. Shows that the local mirror plus MCP is not unique. |
| [garmin-health-mcp-gateway](https://github.com/cara-labs/garmin-health-mcp-gateway) | Separate collector and read-only MCP database role, queued sync requests, status and original FIT retention. | PostgreSQL, containers and remote-tunnel setup are a larger operational footprint than our current local CLI. Its credential separation and honest queued/running/error states are useful. |
| [garmin-grafana](https://github.com/arpanghosh8453/garmin-grafana) | A self-hosted collector and Grafana dashboards for long-term visual exploration. | Docker, InfluxDB and Grafana add services; this is a useful dashboard reference if a local website becomes a priority. |
| [Garth](https://github.com/matin/garth) / [Garth MCP](https://garth.readthedocs.io/en/latest/mcp/) | Shared Connect authentication/client and structured health tools, with raw API escape hatches. | Unofficial Connect access and live API dependence; endpoint breadth is useful as a feature inventory, not evidence that all fields exist in the Personal API. |

### What we should build next

1. **Reliable daily collection:** keep the scheduled pull independent of the assistant; add clearer per-run history, persistent rate-limit cooldowns, time-zone configuration, late-upload gap repair and an opt-in scheduler installer with diagnostics. The new catch-up command retains an anchor and retries missed dates, but cannot guarantee Garmin returns historical data or that old empty days will later be rechecked.
2. **Useful assistant answers:** normalize and document daily metrics, add bounded multi-day trends with units, source and coverage, and show FIT sample counts and gaps. Current MCP exposes stored daily responses and paginated samples; it does not yet calculate trends or sampling completeness.
3. **Data recovery and fidelity:** compare real official-API payloads with Connect and original files; add import paths for account exports or wellness FIT where they demonstrably fill gaps. Detect edited/deleted activities without losing source history.
4. **Setup and experience:** add a doctor command and tested client-specific install instructions. The assistant is the primary interface; point users seeking a dashboard to existing options such as Garmin Grafana. An optional integration can be evaluated later, including its data-source and privacy implications.

Garmin documents the [Personal API as pull-only](https://developer.garmin.com/gc-developer-program/overview/). A local schedule polls after the device uploads to Garmin Connect; it is not a real-time subscription, and neither a successful request nor an empty response proves Garmin supplied complete history. The [Personal API FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/) describes individual use and key expiry.

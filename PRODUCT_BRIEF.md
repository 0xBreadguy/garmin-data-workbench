# Garmin Data Workbench: product direction

Status: November 1, 2026. The first manual-sync CLI, local SQLite archive and FIT decoding are implemented and have been verified against one day of data. An MCP adapter, catch-up command, and opt-in macOS schedule setup are implemented; the broader features below remain planned. The goal is an independent public product; [existing community projects](EXISTING_PROJECTS.md) inform our choices, but overlap with them does not rule out building our own.

## The idea

Build an open-source, local-first workbench that lets people ask their own AI assistant about their Garmin data. Each user creates a Garmin Personal API key and operates the software on their own machine or server. The tool maintains a useful local archive and gives an MCP-compatible assistant clear, bounded access to it. SQL, scripts and notebooks remain available for direct inspection.

The primary outcome is **a trustworthy agent experience grounded in a local dataset the user controls**. The assistant is the primary interface: it can answer questions and produce visualizations using the user’s chosen tools. We are not prioritizing a first-party dashboard; users who want one may use an independent project such as [Garmin Grafana](https://github.com/arpanghosh8453/garmin-grafana), subject to its own data source and setup. This is a personal tool, not a hosted service or a business-growth exercise.

## The problem

Garmin Connect already provides dashboards, activity details, reports and data exports. It can export an individual activity in its original format, activity summaries and reports as CSV, a full account archive, and a single day's wellness FIT files. These are useful, but a person who wants a continuously updated, queryable local dataset has to manage collection, FIT decoding, history and consistency themselves. [Garmin's export instructions](https://support.garmin.com/zh-HK/?faq=W1TvTPW8JZ6LfJSfK512Q8).

Garmin's official [Personal API client](https://github.com/garmin/connect-personal-api-python) makes individual calls and downloads activity files, but is not itself a continuously maintained local analytics archive. [Garmin Personal MCP](https://github.com/Mason-Levyy/garmin-personal-mcp) already provides an MCP interface to the official API. [garmin-health-data](https://github.com/diegoscarabelli/garmin-health-data) already builds a local SQLite dataset using its own Garmin Connect client. Neither a local database nor an MCP server alone is a unique idea; we should evaluate those projects before duplicating work.

The opportunity is a dependable, inspectable workflow: the official Personal API, a durable local history, granular original activity files, a transparent data-quality report, and query interfaces for multiple tools. Existing community projects already provide some of these pieces; this is a product direction, not a claim that the combination is unique.

## Who it serves

- Garmin users who are comfortable creating an API key and following a command-line setup.
- People who want to keep their own history on a computer or server and analyze training and recovery with SQL, scripts, notebooks, spreadsheets or an AI assistant.
- Builders who want documented source data and a stable model for their own tools.

Prioritize clear documentation, good defaults, useful errors and reproducibility for power users. A local CLI is an appropriate first interface. A graphical installer, hosted account system and optimized mass-market onboarding are not goals for the first release.

## Access and onboarding strategy

Each person creates their own Personal API key and runs their own installation. Document the one-time key display, expiration, secure storage and a connection check. The key must not be shared with a hosted service. [Garmin's personal FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/) · [personal-key terms](https://connect.garmin.com/web-translations/partner_portal/partner_portal.properties).

Start with the Personal API; a Garmin account export or direct device files may later provide an optional historical import. Garmin business-program access, a hosted multi-user service and monetization are outside the current direction.

## What the user gets

1. **A personal archive that stays current.** Fetch health data and activity summaries, retain original FIT files, and resume safely after a missed sync. Users can inspect and back up their own files.
2. **Useful data, not just downloads.** Decode activity recordings and normalize daily health data into documented, queryable tables. Preserve original files, source, units and timestamps so an analysis can be traced back to Garmin.
3. **A clear picture of coverage.** Show last successful sync, available dates by data type, missing or unrecorded days, failed requests, sampling intervals, and unknown fields. Distinguish 'not recorded', 'not returned', 'not yet checked' and 'request failed' where evidence supports the distinction.
4. **Open ways to work with it.** Provide a documented SQLite schema or views, useful queries and CSV exports. Let scripts, notebooks and local tools use the data without an AI assistant.
5. **An agent-first interface.** MCP tools answer common questions with bounded, dated results, units, provenance and coverage. Document which assistants and platforms actually work and what data each receives.
6. **User control.** Run locally or on a user-managed machine, use a personal key, keep raw data outside the repo, and require explicit user action for any external sharing. The MCP transport and AI client determine where returned data goes; a local server does not make a remote model local.

Potential questions include: 'How did my sleep and resting heart rate change during weeks when I rode more?' or 'Compare heart rate, power, and cadence across similar rides.' Return dates, coverage, units and missingness alongside results. Associations aren't proof of cause, and unavailable metrics cannot be reconstructed just by processing the files.

## Proposed first release

Build one end-to-end path before expanding scope:

1. **Setup:** a documented local install, user-created Personal API key, and connection check. Avoid copying secrets into command history or the repository.
2. **Sync:** fetch a user-selected date range of daily summaries, sleep and HRV plus activity metadata and original files. Respect endpoint-specific request windows and unknown rate limits; use resumable, idempotent checkpoints.
3. **Decode and store:** persist original JSON/FIT; decode available activity records, events and laps; store curated daily health, sleep, activities and time series in SQLite. Record source and observed sampling, not invented precision.
4. **Check:** show coverage, recent sync, errors and missing data by category. Show which fields are present for each activity, including unrecognized fields where practical.
5. **Query and export:** support exporting an activity's samples and a daily-health table as CSV, plus documented example SQL queries.
6. **Connect an assistant:** provide a minimal local MCP adapter for listing activities, inspecting a selected activity, querying daily metrics and viewing sync/coverage status; offer bounded time-series ranges and pagination. Document one verified end-to-end assistant setup. The data archive remains useful without MCP.

Start with the official Personal API and test actual coverage. Account-export import, direct device access, optional dashboard integrations and unofficial endpoints are follow-on options only where they fill demonstrated gaps. A first-party dashboard is not a current goal. Do not require recording strength sets or weights to make the core product useful.

## Architecture and data contract

```text
Garmin Personal API ──> sync + original files ──> local data model
                                                   ├── CLI and CSV
                                                   ├── SQLite / notebooks
                                                   └── local MCP adapter ──> user-chosen AI client
```

Keep retrieval, storage, analysis and adapters separate. Shared query functions should serve the CLI and MCP; neither should contain its own data definitions. Initially model daily metrics, sleep sessions, activities and activity samples, plus source/import/sync metadata. Preserve UTC instants and relevant local dates, units, activity IDs and source files. Keep unknown FIT fields in the retained original file even if a parser cannot yet interpret them.

The agent experience is the main product surface. Favor small, composable question-shaped tools over dumping raw payloads; keep raw access available for inspection. The MCP layer should return bounded results and metadata: source, date range, units, freshness, sampling and coverage. Don't include location by default in a generic summary. Make exact location and other sensitive fields available when the user asks for them. A query must distinguish absent data from a real zero. The tool should remain useful if MCP is never enabled.

## Validation and launch bar

- Successfully complete a clean first-run setup using only the documentation and a user-created key.
- Backfill a chosen range, run the sync twice without duplication, and recover after an interrupted or rate-limited request.
- Compare representative daily health results and at least one watch and one Edge activity with Garmin Connect and the original FIT files. Report actual date coverage and gaps; don't promise full history or specific sensors until tested.
- Show that CSV and MCP queries agree with the local database and include data provenance and completeness.
- Run tests using synthetic data in public CI; keep credentials, health records, routes, logs and downloaded files out of the public repo and its entire history.
- Document supported platforms based on actual clean-install tests. Review license and dependencies and audit public artifacts before publication.

The Personal API is for an individual accessing their own data, and its key is for tools the user develops or operates for personal use. [Garmin FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/) · [Personal-key terms](https://connect.garmin.com/web-translations/partner_portal/partner_portal.properties).

## Decisions to make after the first usable slice

- Which activity fields, health metrics and analysis questions are most valuable to expose first?
- Which existing libraries can we reuse after evaluating coverage, licenses and maintenance?
- Which additional data sources or export formats fill real gaps in the Personal API?

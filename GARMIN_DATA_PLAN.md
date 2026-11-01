# Garmin Data Workbench: data plan

Research checked: November 1, 2026. A first manual-sync CLI and SQLite archive have been implemented and verified against one day of live data. The broader plan below includes work not yet built, including scheduler installation beyond macOS, full historical reconciliation and richer MCP analysis. Local MCP, macOS scheduler setup and a scheduler-friendly catch-up command are now implemented.

## Goal and recommendation

Build a public, open-source, local-first tool for power users to download, own and query their Garmin Connect data using their own Personal API key. Support SQL, scripts, notebooks, exports and an optional MCP interface over a durable local archive. The first real-world target is a Fenix, Edge, and heart-rate strap, but setup and examples must not depend on a particular person's devices. Use Garmin Connect as the initial aggregation point, Garmin's **Personal API** for recurring reads, an account export for an independent historical copy, and direct device FIT files when they fill a proven gap. Keep the original responses and files so users can reprocess them without asking Garmin again.

Garmin now provides a [Personal API](https://developer.garmin.com/gc-developer-program/overview/) for an individual's own activity data (JSON and FIT) and health data (JSON), with pull access. Its [official Python client](https://github.com/garmin/connect-personal-api-python) provides authentication, health endpoints, activity search, and activity-file downloads. This is newly available, so actual history, precision, and field coverage need to be measured against this account. It does not promise access to every sensor stream or Garmin-derived score.

The intended distribution is public code that people install and operate themselves, with **their own Garmin account and personal key**. Garmin says its Personal API is for individual users' own data and is not intended for commercial applications serving multiple end users. Its [personal-key terms](https://connect.garmin.com/web-translations/partner_portal/partner_portal.properties) say a key may only be used by its owner with tools they develop or operate for their own use, and may not be shared with third parties. Publishing reusable code and each individual operating it with their own key is the intended design; this is not a claim of Garmin endorsement or a legal ruling. A hosted multi-user product would need a separate access and terms review. [Personal API FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/).

## Public repository contract

- **Public:** application source, configuration templates without secrets, schema and migrations, synthetic fixtures, example queries, tests, setup and troubleshooting documentation, and an open-source license. Garmin's client is Apache-2.0; choose the project license after reviewing dependency and attribution requirements.
- **Private by default:** every user's API key and bearer-token cache, account export, raw responses, FIT files, locations, database, backups, and real logs or diagnostic reports. Store runtime data and credentials outside the checkout, in OS-appropriate user directories, with restrictive permissions. Add `.gitignore` and packaging exclusions as defense in depth; avoid logging authorization headers and health payloads.
- **No central account or collection service:** users authenticate directly with Garmin and operate their own installation. No shared project key, default telemetry, or automatic uploads. Any future external analysis integration should be explicit and documented.
- **Reproducible install:** package a Python CLI with declared supported versions and pinned/locked development and release dependencies. Garmin's current official client requires Python 3.12+. Start by validating macOS and Linux; document any Windows limitations instead of claiming untested support. Provide a clean-environment quickstart, configuration reference, upgrades, backup/restore, scheduler examples, and uninstall instructions.
- **Contributor-safe testing:** use fully synthetic health/GPS data and mocked API responses for offline tests and CI; no credentials, real account exports, routes, or network access to Garmin in public CI. Include tests for parsing, pagination, deduplication, retries, rate limits, timezone handling, migrations, and restart recovery. Live account checks are optional, local, and never upload results.
- **Before making a repository public:** inspect the complete Git history, tracked files, assets, example output, and release artifacts for personal information or secrets; run secret scanning and manually inspect anything suspicious. Verify a fresh clone and documented install on each supported platform. Do not assume removing a file from the current tree removes it from history. Publishing is a separate action from preparing the repository.

## Inputs and expected coverage

| Source | Expected contribution | What we need to establish |
| --- | --- | --- |
| Fenix → Connect | All-day wellness, sleep, heart rate, HRV and watch-recorded activities, subject to model and settings. | Exact model, enabled features, sync behavior, date range, and returned detail. |
| Strap → paired recorder → Connect | Heart rate and potentially additional activity data in a watch or Edge recording. Some straps support storing data for later transfer. | Exact strap model, which recorder is paired, and whether stored or beat-to-beat data actually appears in its FIT files. A BPM series is not an RR-interval series. |
| Edge → Connect | Cycling activities and supported paired-sensor streams such as heart rate, power and cadence. | Exact Edge and paired sensors; recorded fields and sampling cadence. |
| Full Connect account export | Historical archive and reconciliation source, including uploaded activity files. | What categories and dates the actual export contains; do not assume it includes every intraday series. |
| Direct watch / Edge files | Additional original activity FIT files if needed to validate or supplement cloud data. | Device and OS access, available files, and whether they differ from Connect's copies. |

Garmin's official client documents endpoints for daily heart rate, sleep, HRV, body battery, stress, steps, SpO2, weight and activity data. What appears in a response, its sampling interval, and how far back it goes must be tested for each category. Activity FIT files can contain GPS, HR, cadence, power, events and other fields when the device and sensors recorded them; none is guaranteed. Garmin's [FIT Python SDK](https://developer.garmin.com/fit/get-the-sdk/) can decode these files. Proprietary scores are Garmin estimates, not raw signals, and some may be unavailable through the personal endpoints.

As checked November 1, 2026, Garmin's [Personal API specification](https://developer.garmin.com/gc-developer-program/personal/swagger-docs/) limits each steps and stress range request to 28 days; sleep summaries, hydration, and Body Battery range requests to 31 days; and daily summaries to one year. These are limits per request, not proven limits on historical availability. Garmin's [personal-key terms](https://connect.garmin.com/web-translations/partner_portal/partner_portal.properties) reserve the right to set and change request limits, but do not specify a numeric request quota. Design for throttling and do not assume any fixed allowance.

## Architecture

```text
Fenix ─────────────────────┐
Strap ──> watch or Edge ───┼─> Garmin Connect ─> Personal API ─> raw JSON + FIT ZIPs
Edge ──────────────────────┘                           │                  │
                                                     scheduler            │
Account export / optional device FIT files ───────────────────────────────┤
                                                                         ▼
                                                      FIT decoder + normalizer
                                                                         │
                                                                         ▼
                                                   local SQLite + analysis views
                                                                         │
                                                        SQL / CSV / notebooks
```

**Storage:** Use a private directory outside the Git checkout, on an encrypted volume. Retain unchanged source files, content hashes, retrieval timestamps, endpoint/source and import manifests. SQLite is the initial analysis store: portable and sufficient for one person. Add Parquet/DuckDB later only if query volume warrants it. Maintain a separate encrypted backup, with a tested restore; do not upload health or location data to a third party by default.

**Analysis model:** Keep raw sources authoritative and maintain derived tables for daily metrics, timestamped wellness observations, sleep sessions/stages, activities, activity samples, laps/events, and source/import metadata. Store UTC instants alongside the original local date/time zone when available; distinguish unknown from zero. Preserve units, device/source, recording cadence and nulls. Treat Garmin scores, measured heart rate, and independently computed values as distinct. Preserve FIT developer/unknown fields through the original file even when the first parser does not understand them.

**Duplicate policy:** Upsert API activities by Garmin activity ID; identify identical imported files by hash and link them to an activity when supported by evidence. If watch and Edge recorded the same ride separately, retain both and flag overlapping candidates using time, type and duration. Choose a primary recording for aggregate analysis only after checking; never silently delete or merge source records. Wellness data from multiple devices may already be reconciled by Garmin, so do not sum sources blindly.

## Implementation phases

### 1. Inventory and access proof

1. Record the exact Fenix, Edge and strap models, other cycling sensors, desired metrics, earliest useful history, and which machine will run the sync. Confirm the devices synchronize to the same Garmin Connect account.
2. On [Garmin Connect Web](https://connect.garmin.com/app/settings/personalApiToken), each user creates their own Personal API key, reviews Garmin's terms, and saves it privately. The key is shown once; choose an expiry (up to one year) and set a rotation reminder. Never paste it into chat, shell history, logs or Git. Use a local secret store, or a user-only `0600` file for the official client, and protect its bearer-token cache too. The key is for tools the user develops or operates for personal use; review the current terms before any external service receives it or API data. [Garmin's FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/) describes key expiry, revocation and 24-hour access tokens.
3. With the official Python client, read a recent day of sleep, HRV and heart rate; list recent activities; and download one Edge ride and one watch activity. Test old dates as well. Save sanitized metadata and compare selected values and timestamps to Connect. Do not log the raw payloads or credentials.
4. Build a coverage matrix from observed results: date range, resolution, units, device provenance, missing fields and discrepancies. Decide whether any gap merits an additional source. Until this test, treat all detailed coverage as unverified.

**Exit:** Authentication works without sharing a password, at least one recent ride FIT decodes, and we know what the representative health calls return. If a category is empty, distinguish no recording, disabled feature, unsupported endpoint and failure before calling it missing.

### 2. Historical backfill and archive

1. Request a [full account data export](https://www.garmin.com/en-US/account/datamanagement/). Garmin says the download link is typically emailed within 48 hours but may take up to 30 days. Import locally when it arrives; retain the original archive. Garmin documents original uploaded activity files within the account export and a separate day-by-day wellness FIT export in Connect Web. See [Garmin's export instructions](https://support.garmin.com/zh-HK/?faq=W1TvTPW8JZ6LfJSfK512Q8).
2. Backfill the Personal API in bounded date windows respecting each endpoint's documented range, with activity pagination to exhaustion and independent checkpoints per category/window. Start at the oldest date proven available, rather than assuming all historical data is present. Pace requests; honor `Retry-After` when present and stop or back off on rate limits. Resume incomplete windows without redoing successful work.
3. Import the archive and API material side by side, keeping provenance. Compare counts and date coverage by month, and reconcile a sample of activity IDs and health dates. Preserve conflicts and flag unresolved gaps rather than silently choosing whichever source was last.
4. Decode activity FITs with Garmin's SDK, including records, laps and events where available. Preserve original ZIP/FIT and unknown fields. Exercise a sample from each device, and a strap recording if available.

**Exit:** A dated coverage report identifies each category's earliest/latest observations, missing periods and uncertain fields; sample totals match Connect or discrepancies are explained. Re-running backfill produces no duplicate rows, and interrupted jobs resume.

### 3. Ongoing sync and verification

1. Run a local scheduled job twice daily as a starting point, after normal device-to-Connect syncing. Use an always-on host if timely unattended collection matters; a sleeping Mac cannot run on schedule, so run a catch-up on wake/login and show freshness. Tune cadence after measuring request volume and delays.
2. Re-fetch a rolling seven-day health window to catch late syncs and revised sleep; reconcile a longer window periodically for late edits. Discover recent activity pages and download new or changed files when indicated. Periodically reconcile older activity metadata as well, since users can edit old activities. Adjust windows to observed behavior.
3. Maintain per-source/category/date success state. A failed request or decode is not an empty day: retry transient failures with bounded exponential backoff and jitter, respect rate limits, and surface permanent/authentication failures. Handle key rotation, offline runs, partial responses, schema changes and corrupted FITs without losing original files. Never advance a checkpoint past failed work.
4. Provide a local status command/report showing last successful sync, most recent data date by category, pending gaps, failed jobs, record counts and key expiry. Escalate persistent failures visibly when the user next opens the status; add notifications only if desired.
5. Verify a fresh watch day and a new Edge ride end-to-end, simulate an offline run and recovery, verify idempotent reruns, and restore a backup to a separate location. Check real dates across a time-zone or daylight-saving transition if available.

**Exit:** New synced data arrives automatically while the host is available; failures and stale data are visible; reruns and recovery do not duplicate or erase data.

### 4. Analysis and targeted gap-filling

Create documented SQL views and CSV exports for daily sleep, resting HR, HRV, stress, training load where available, and activity-level metrics. Start with a few useful analysis questions; label missing days and incomplete sources rather than inventing values. Add notebooks or a dashboard later if useful, with synthetic public examples.

If important fields are missing, test sources in order:

1. The account export or Connect Web's per-day wellness FIT export.
2. A read-only copy of available watch/Edge FIT files over USB. On Macs, MTP devices may not appear as disks; Garmin documents that limitation. Device files may have limited retention and need not include cloud-derived scores. [Garmin USB guidance](https://support.garmin.com/en-CA/?faq=Ht3ZP52Kju075uKvqTqu99).
3. A narrowly scoped unofficial Connect client only for a documented gap, after checking its current behavior and the applicable terms. For example, [python-garminconnect](https://github.com/cyberjunky/python-garminconnect) exposes many web-app methods but depends on undocumented interfaces; it may break or require additional authentication. Treat it as a replaceable source, not the backbone.
4. Direct protocol or app investigation only if the missing measurement is valuable and previous sources cannot provide it. First confirm the hardware actually records the signal. Avoid assuming that decoding can reconstruct unrecorded data, raw optical waveforms, or proprietary algorithms. Before distributing any derived implementation, separately review the applicable terms, licensing, and distribution rights; do not include copied proprietary app code or assets by default.

### 5. Public release readiness

1. Write a first-run guide for a person with no project context: create their own key, install locally, sync a small range, inspect status, query data, and optionally schedule the job. Document required privileges, paths, rate limits as observed, and known data-coverage gaps.
2. Provide a no-account demo using synthetic data, so contributors can exercise ingestion and analysis without exposing health information. Demonstrate offline tests and a clean install from the repository.
3. Add the chosen license, third-party notices as needed, contribution guidance, a security reporting route, and a supported-platform matrix based on actual testing.
4. Audit the full Git history and release contents for credentials and personal data, and perform a fresh-clone walkthrough. Fix any findings before a public release.

**Exit:** A new user can follow the documentation to run their own local instance, and a contributor can run the test suite without Garmin credentials. The public artifact contains no personal data or keys. Repository creation or publication happens only when explicitly requested.

### Replacing a hosted Garmin connector

An existing local MCP server, such as [Garmin Personal MCP](https://github.com/Mason-Levyy/garmin-personal-mcp), may offer a quicker AI interface while the archive is built. It uses the Personal API and can download original activity files; it has not been audited or tested as part of this project. Running an MCP server locally keeps its credentials local, but any data returned to a remote AI model is shared with that model provider. Client and mobile support depend on the actual host.

Before removing an existing hosted connector, compare its results with the personal setup for representative recent and older activities, FIT detail and priority health metrics. Note any service-specific analysis or cached/imported data. Garmin's Personal API is read-only; partner services may have separately authorized workout-writing capabilities. Removing an app or plugin, revoking Garmin access, canceling billing and deleting a service account/data are separate actions with potentially different consequences; handle only those a user requests.

## Recording setup to verify

- Set the Fenix as the primary wearable if it is the user's all-day device. Verify compatible device synchronization / TrueUp settings. [Garmin multi-device guidance](https://support.garmin.com/en-GB/?faq=UZRGMfTokn1TLQibO7nbn5).
- Pair the strap with the device that records each activity, and confirm it is connected when recording. For rides, choose the intended primary recorder; compatible devices may offer Extended Display mode. Garmin cautions that simultaneously recording an activity on multiple devices may affect training metrics. [Garmin guidance](https://support.garmin.com/en-US/?faq=HVMcrDvQ3m2xEFh1aVMbU8).
- Where supported and useful, prefer every-second activity recording for denser activity tracks; this has storage/battery tradeoffs and is not a promise of beat-to-beat intervals or increased all-day health sampling. Some newer Edges already record every second. [Garmin recording settings](https://support.garmin.com/en-US/?faq=s4w6kZmbmK0P6l20SgpW28&productID=854515&tab=topics).

## Open decisions and constraints

- **Exact device models and sensors:** determine supported measures, pairing and available FIT fields.
- **Host:** a personal computer is the easiest starting point; an always-on machine makes scheduled collection more dependable. Availability and backup destination remain to be chosen.
- **Priorities:** identify the first health/training questions and any must-have raw signals so the coverage proof tests what matters.
- **Unknowns:** actual historical depth, API quotas, precision, original-file fidelity, device provenance and access to proprietary or raw physiology are unverified until tested on this account. The Personal API is read-only/pull-based and depends on data arriving in Connect; it is not a live sensor feed.
- **Distribution:** choose a project license, initial supported platforms, and a release destination. This is an individual personal-data workflow, not a hosted multi-user service. Verify the accepted Personal API terms before routing API data to other services. A Personal API key has been configured locally and a manual one-day archive sync has succeeded; the optional recurring schedule and an assistant connection have not been installed or tested with this account.

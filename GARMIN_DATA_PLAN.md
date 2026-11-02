# Data plan

Research snapshot: November 1, 2026. [Product direction](PRODUCT_BRIEF.md#available-today) tracks implemented features; this document covers coverage, fidelity and remaining validation.

## Sources

Start with Garmin Connect as the aggregation point and the official [Personal API](https://developer.garmin.com/gc-developer-program/overview/) for recurring collection. Keep original responses and activity files so they can be reprocessed offline.

| Source | Useful for | Check before relying on it |
| --- | --- | --- |
| Watch → Connect | Wellness, sleep, HRV, heart rate, activities | Device settings, available dates, fields and sampling |
| Strap → watch/Edge → Connect | Recorded heart rate and supported sensor data | Pairing, recorder and actual FIT fields; BPM isn't beat-to-beat intervals |
| Edge → Connect | Cycling and paired-sensor recordings | Which sensors recorded, units and cadence of samples |
| Account export | Independent history and reconciliation | Actual categories/dates; import isn't implemented |
| Direct device FIT files | Validation or proven gaps in cloud copies | Device/OS access, retention and differences from Connect |

The official client exposes more endpoints than the workbench currently collects. Availability depends on account, device and recording. Proprietary scores aren't raw signals; decoding can't recover unrecorded measurements.

## API constraints

The Personal API is pull-only and read-only. Devices upload to Connect first. Each person operates their installation with their own key; a hosted multi-user service requires a separate access/terms review. See [Garmin's FAQ](https://developer.garmin.com/gc-developer-program/personal/personal-faq/) and [key terms](https://connect.garmin.com/web-translations/partner_portal/partner_portal.properties).

At the research date, the [API specification](https://developer.garmin.com/gc-developer-program/personal/swagger-docs/) limited range calls to 28 days for steps/stress, 31 for sleep summaries/hydration/Body Battery and one year for daily summaries. These are request windows, not established history limits. The terms provide no fixed numeric request quota. Current sync makes per-day requests.

## Fidelity rules

- Preserve originals, source units and timestamps. Future imports should add hashes and manifests for provenance.
- Keep missing, empty, failed and zero distinct. Document observed resolution and unknown fields.
- Upsert API activities by Garmin ID. Future imports should identify identical files by hash and preserve conflicts.
- Retain overlapping watch/Edge recordings; don't silently merge or delete them. Don't sum wellness sources Garmin may have reconciled.
- Keep raw sources authoritative. Richer daily tables, sleep stages, laps/events and derived analysis need explicit definitions and validation.
- Store data outside Git, with private permissions, encrypted storage and separate backups. Test restores. See [security](SECURITY.md).

## Validation priorities

1. **Prove coverage.** Test recent and older health dates plus representative watch and Edge activities. Compare values, timestamps and originals with Connect. Record fields, units, date coverage and discrepancies without publishing private records.
2. **Prove recovery.** Check idempotent reruns, interrupted work, rate limits, failed downloads, corrupted FITs and key rotation. Verify catch-up and a backup restore.
3. **Prove ongoing collection.** Test late uploads, time-zone transitions and an actual opted-in job on each supported host. Show freshness and failures.
4. **Prove analysis.** Compare CLI, SQL, CSV and MCP results. Add activity comparisons and sample-gap reporting before making richer training/recovery claims.

Use the user's actual device models and priority questions to choose representative checks. Every-second activity recording may improve track density, with device/storage tradeoffs; it doesn't establish beat-to-beat or all-day sampling. See [Garmin's recording guidance](https://support.garmin.com/en-US/?faq=s4w6kZmbmK0P6l20SgpW28&productID=854515&tab=topics).

## Fill demonstrated gaps

Evaluate [account exports and wellness FIT](https://support.garmin.com/zh-HK/?faq=W1TvTPW8JZ6LfJSfK512Q8) first, then read-only device copies. Keep sources and conflicts traceable. Import paths remain planned.

Consider unofficial endpoints only for a specific unresolved gap, with their maintenance and terms reviewed. Direct protocol investigation is a last option after confirming the hardware records the signal; don't distribute proprietary code/assets.

Before replacing another connector, compare priority metrics and recent/older activities. Disconnecting an app, revoking access, canceling billing and deleting data are separate user-authorized actions.

## Release bar

A fresh user can install, privately supply a key, sync, inspect coverage and query the archive. A contributor can run synthetic tests without an account. Supported-host claims require actual tests; scheduling requires an observed execution. Audit Git history and release artifacts for secrets/private data, verify the MIT license and dependency notices, and follow [TESTING.md](docs/TESTING.md). Publication requires separate authorization.

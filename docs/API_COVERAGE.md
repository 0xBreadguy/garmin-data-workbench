# Personal API coverage

The MVP collects from Garmin's **official Personal API only**. No unofficial Connect login, Grafana collector, extra authentication flow or invented readiness score is included.

Audited against [Garmin's published Personal API Swagger](https://developer.garmin.com/gc-developer-program/personal/swagger-docs/) on November 3, 2026: **26 GET endpoints, 109 response definitions and 1,587 declared object properties**. Properties are counted once per schema definition, not once for every endpoint reusing it. Garmin also documents open-ended objects and sample arrays whose individual fields are not enumerated.

## What support means

- Sync collects each documented response and preserves all returned JSON fields, including fields unknown to this version. Original activity ZIPs are retained separately.
- `api-catalog` / MCP `api_catalog` discovers every source and traverses its native response definitions, including descriptions, units where Garmin documents them, enums, formats and bounds.
- `source-data` / `source_data` navigates every stored JSON field and pages objects, arrays and long strings. Large children return a pointer to expand instead of a truncated value. Unknown fields remain accessible without a catalog definition.
- `source-series` / `source_series` reads any native scalar over 1–90 request dates. Signed values, flags, strings, nulls and source sentinels retain their native meaning. It does not invent daily averages or convert undocumented units.
- `day`, `trend`, `sleep` and `body-battery` provide interpreted conveniences with shared CLI/MCP definitions. These are a subset of native fields; identifiers, notes, samples and assessments do not automatically become numerical trend metrics. `day` lists named metrics and their units.

Missing, null, empty, failed and zero remain distinct. A failed refresh masks retained values; the original response stays available for local recovery. Native queries include scope and fetch/attempt metadata. Request dates are not automatically measurement dates: inspect payload dates and timestamps. Current profile and heart-rate zones have no fabricated historical date.

## Collected sources

Daily sources use the same start/end date for range endpoints and retain the complete response envelope. Overlapping endpoints are kept separately: similar names do not establish identical fields or semantics.

| Source name | Scope | Personal API endpoint |
| --- | --- | --- |
| `daily_summary` | Daily | `/usersummary-service/v2/dailysummaries` |
| `daily_summary_legacy` | Daily | `/usersummary-service/usersummary/daily` |
| `sleep` | Daily | `/sleep-service/sleep/dailySleep` |
| `sleep_summaries` | Daily | `/sleep-service/sleep/dailySleepSummariesByDate` |
| `hrv` | Daily | `/hrv-service/hrv/{calendarDate}` |
| `hrv_summaries` | Daily | `/hrv-service/hrv/daily/{fromDate}/{toDate}` |
| `heart_rate` | Daily | `/wellness-service/wellness/dailyHeartRate` |
| `body_battery` | Daily | `/wellness-service/wellness/bodyBattery/reports/daily` |
| `steps` | Daily | `/usersummary-service/stats/steps/daily/{startDate}/{endDate}` |
| `stress` | Daily | `/usersummary-service/stats/stress/daily/{startDate}/{endDate}` |
| `hydration` | Daily | `/usersummary-service/stats/hydration/daily/{startDate}/{endDate}` |
| `weight` | Daily | `/weight-service/weight/range/{startDate}/{endDate}` |
| `weight_measurements` | Daily | `/weight-service/weight/all/{startDate}/{endDate}` |
| `weight_goals` | Daily | `/goal-service/goal/user/effective/weightgoal/{startDate}/{endDate}` |
| `nutrition` | Daily | `/nutrition-service/food/logs/{date}` |
| `fitness_age` | Daily | `/fitnessage-service/fitnessage/v2/{calendarDate}` |
| `spo2` | Daily | `/wellness-service/wellness/daily/spo2acclimation/{calendarDate}` |
| `menstrual_summary` | Daily | `/periodichealth-service/menstrualcycle/summary/{calendarDate}` |
| `menstrual_day` | Daily | `/periodichealth-service/menstrualcycle/dayview/{calendarDate}` |
| `wellness_activity` | Daily | `/wellnessactivity-service/activity/summary/range/{fromDate}/{untilDate}` |
| `profile` | Current | `/userprofile-service/userprofile/settings` |
| `heart_rate_zones` | Current | `/biometric-service/heartRateZones/v2` |
| `activities` | Search result, selected by ID | `/activitylist-service/activities/search/activities` |
| `activity` | Activity ID | `/activity-service/activity/{activityId}` |
| `activity_workouts` | Activity ID | `/activity-service/activity/{activityId}/workouts` |
| `original` | Retained file by activity ID | `/download-service/files/activity/{activityId}` |

Search explicitly includes multisport children (`excludeChildren=false`). Menstrual day views request the full response, including analysis and baby-movement fields (`reducedResponse=false`, `skipbm=false`, `includeAnalysis=true`); `todayDate` uses the collection run's current date, not the historical request date. Nutrition keeps the documented defaults including goals, nutrition and media. Weight ranges use `includeAll=true`. Fitness age keeps the documented full-history scan default; the payload can represent the latest available assessment rather than a new measurement on the requested date. Heart-rate zones keep the API's documented default-zone behavior; returned zones do not prove the user configured them manually.

## Query examples

```sh
# No archive or key needed: list sources, then inspect nap field definitions.
garmin-archive api-catalog
garmin-archive api-catalog sleep --pointer '/dailyNapDTOS/*'

# Root schema, array-item schema, then native values for one stored date.
garmin-archive api-catalog hydration
garmin-archive api-catalog hydration --pointer '/*'
garmin-archive source-data hydration --day 2026-01-01
garmin-archive source-data hydration --day 2026-01-01 --pointer /0/valueInML

# Page a large array using the returned next_offset.
garmin-archive source-data heart_rate --day 2026-01-01 --pointer /heartRateValues --limit 100
garmin-archive source-data heart_rate --day 2026-01-01 --pointer /heartRateValues --offset 100

# Current settings, complete activity detail fields and workouts.
garmin-archive source-data profile
garmin-archive source-data activity --activity-id 123456789
garmin-archive source-data activity_workouts --activity-id 123456789

# Native scalar series preserving signed values.
garmin-archive source-series daily_summary_legacy /remainingKilocalories --from 2026-01-01 --to 2026-01-07
```

Global `--data-dir DIR` goes before the command. MCP uses the same parameters with underscores: `activity_id`, `include_location`. Pointers follow JSON Pointer escaping (`~1` for `/`, `~0` for `~`). Catalog array items use `*`; stored data uses concrete indices. Array order does not establish a stable entity across dates or an appropriate daily aggregation.

Pages contain up to 100 entries and a bounded byte budget. Always follow `next_offset`, which can advance by fewer than `limit` entries. Large child values include `expand: true`; call their pointer for the next level. Strings page by characters; containers page by keys/items. Compare `fetched_at` across pages and restart if a sync replaced the response. Default native/MCP output omits coordinate fields at every depth; `source-data --include-location` explicitly includes them. Notes, identifiers and other native fields may also be private: query the smallest relevant field. Original bytes use `export-original`; MCP reports retention metadata and provides decoded samples through `activity_records`, without embedding a binary ZIP. The older archive format has no separate original-file fetch timestamp; this remains explicit rather than using the activity search time.

## Existing archives and collection cost

Read-only queries do not migrate old archives. Newly supported sources report `not_checked` until collected. The next sync creates an additive `source_snapshots` table while preserving existing daily responses, originals and decoded data. To fill older source gaps, explicitly sync the desired historical range; catch-up alone only revisits its checkpoint/lookback range. No live sync happens merely by querying the catalog or upgrading the code.

A selected date now requires **20 health requests**, plus activity pagination. Each run refreshes two current sources; each new/recent/refreshed activity also requests details and workouts, with original downloads as needed. Requests retain existing pacing, retries, stop conditions and serialized archive access. Completed older sources are skipped independently; errors remain retryable and visible. Empty responses do not prove complete device/history coverage, and HTTP errors are never reclassified as empty data.

`status` and MCP `archive_status` include snapshot coverage alongside daily coverage. Profile preference failures can continue using explicitly dated cached defaults; the native profile snapshot has its own status. Missing fields must be reported, not replaced by an unofficial source.

## Verification and contract maintenance

Offline tests exercise all 26 paths through the official SDK with a fake HTTP session, exact response preservation, schema traversal, pagination, unknown fields, coordinates, native scalar types, old-archive compatibility, failed refreshes and retries. Installed-wheel checks exercise catalog packaging and CLI/MCP native access outside the checkout.

This is **documented-contract coverage**, not evidence of live availability for every account, device or historical date. No real health data or credentials were used for this expansion. Representative live comparisons with Garmin Connect, actual endpoint access/quotas and recurring execution remain separate checks.

`personal_api_contract.json` is generated from the public OpenAPI document. It contains response definitions and provenance, not account data. After obtaining a fresh public schema JSON and reviewing vendor changes:

```sh
python scripts/update_personal_api_contract.py /path/to/openapi.json --reviewed YYYY-MM-DD
uv run --quiet --locked python -m unittest discover -s tests -p test_api_data.py -v
```

Review changed routes, field definitions and the schema checksum; update the deliberate endpoint/property-count assertions when Garmin changes the contract. Runtime queries never fetch Swagger. Collection mappings need separate review: regenerating the catalog does not add collection for a new endpoint.

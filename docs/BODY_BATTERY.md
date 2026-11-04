# Body Battery summaries

```sh
garmin-archive body-battery --from 2026-01-01 --to 2026-01-07
garmin-archive trend body_battery_last --from 2026-01-01 --to 2026-01-07
garmin-archive chart body_battery_last --from 2026-01-01 --to 2026-01-07 --output battery.png
```

Global `--data-dir DIR` belongs before the command. MCP `get_body_battery(start, end)` uses the same query. Ranges contain 1–90 inclusive archive dates, defaulting to seven ending today in the saved Garmin profile zone (host date as fallback). Today may be partial. No key, sync, migration or new API call is needed: collection already saves daily Body Battery reports.

## Source and definitions

The [official Personal API Swagger](https://developer.garmin.com/gc-developer-program/personal/swagger-docs/) documents `GET /wellness-service/wellness/bodyBattery/reports/daily` as an array of `BodyBatteryDailyReportDTO` reports (reviewed November 3, 2026). Only the unique report whose `date` matches the archive date is used. Duplicate matching reports, missing dates and unrecognized shapes remain unavailable; we do not substitute `BodyBatteryV2DTO` from another endpoint.

| Metric | Definition | Unit |
| --- | --- | --- |
| `body_battery_charged` | Report's `charged` amount for the reporting day | scale points |
| `body_battery_drained` | Report's `drained` amount for the reporting day | scale points |
| `body_battery_min` | Lowest valid observed reading | Body Battery level |
| `body_battery_max` | Highest valid observed reading | Body Battery level |
| `body_battery_first` | First valid observed reading by UTC timestamp | Body Battery level |
| `body_battery_last` | Last valid observed reading by UTC timestamp | Body Battery level |

Levels are on Garmin's 0–100 scale, not percentages, medical measurements or a new recovery score. Daily charge/drain amounts are nonnegative int32 scale-point totals; they are not inferred from last minus first or capped at 100. The query never interpolates, estimates wake-up/bedtime levels, or computes an unweighted average of irregularly spaced readings. Cross-day means average each available daily statistic, with its denominator.

The last reading is **last observed**, not a live current value or necessarily the day's final value. First/last metrics include their observation timestamp. `day` and `trend` retain that context. The detailed summary returns fetched_at, last_attempt, dataset/report/readings status, valid/invalid sample counts, duplicate counts, conflicting-timestamp counts, any source UTC reporting-window bounds and missing_fields. Counts are observations, not a full-day coverage guarantee.

## Descriptor and missing-data handling

`bodyBatteryValueDescriptorDTOList` names the `timestamp` and `bodyBatteryLevel` column indices into `bodyBatteryValuesArray`. Their positions can change. We require unambiguous names/indices, with no fixed-column fallback. Missing or conflicting descriptors leave derived levels null while valid reported charge/drain totals remain available.

Sample timestamps are epoch milliseconds or ISO instants with an explicit offset. We do not guess seconds from a value's size or assign the current profile zone. UTC samples more than one calendar date away from the associated report date are invalid; samples are not required to have the same UTC date as the local report. Valid source window bounds also constrain readings. A reversed source window disables derived levels. Exact duplicates are deduplicated; timestamps with conflicting levels are excluded. `conflicting_timestamps` counts ambiguous timestamp groups, not rows. Boolean, string, negative, nonfinite and above-100 levels are unavailable. Numeric zero remains a reading.

The parser processes at most 100,000 sample rows per stored daily report. Larger reports keep source totals but explicitly mark derived readings unavailable; no truncated min/max/last is reported. Raw readings, free-form event text, IDs and coordinates are not returned by these summaries.

Failed refreshes mask retained data. Empty, unchecked, response-missing, unknown shapes, missing fields and zero remain distinct. The built-in scalar charts use fixed 0–100 level axes; charge/drain bars start at zero and can exceed 100 points. All retain branding, date gaps and fetch context. Use the [generated demo](VISUALIZATION.md#try-generated-demo-data) with `--synthetic` to test without personal data.

Schema-based and synthetic verification is complete. Representative values still need comparison with Garmin Connect for a user's device; installed commands and offline tests alone do not establish live measurement accuracy.

# Sleep summaries and reports

Use one bounded query for an ordinary question about sleep:

```sh
garmin-archive sleep --from 2026-01-01 --to 2026-01-07
garmin-archive chart sleep --from 2026-01-01 --to 2026-01-07 --output sleep.png
garmin-archive trend sleep_score --from 2026-01-01 --to 2026-01-07
```

Global `--data-dir DIR` belongs before the command. MCP exposes the same summary as `get_sleep(start, end)` and the same scalar metrics through `get_trend`. No credential, sync or archive migration is involved. Ranges contain 1–90 **inclusive** dates; default is seven dates ending today according to the saved Garmin profile (host date as fallback). Today can be incomplete. For seven completed dates, explicitly select yesterday and the six preceding dates.

`sleep` returns small scalar values rather than sample arrays or personal notes. Each night includes refresh status, fetched_at, last_attempt, values, missing_fields, source sleep-window times and whether its stage breakdown is complete. Field definitions include source paths and units. Per-field coverage counts and means use only valid available values. Dataset status `ok` does not mean every metric was returned. Null values never become zero; failed/empty/unchecked responses and missing responses remain distinct. Retained values and times after a failed refresh are masked.

## Source definitions

Mappings follow the [official Personal API Swagger](https://developer.garmin.com/gc-developer-program/personal/swagger-docs/) `GET /sleep-service/sleep/dailySleep` response, `DailySleepDTO`, and `SleepScoreItem` (reviewed November 3, 2026). The collector already stores that endpoint's response. No new collection calls are needed.

| Query metric | Source field | Unit / meaning |
| --- | --- | --- |
| `sleep_duration` | `sleepTimeSeconds` | seconds; measured sleep, excluding naps |
| `sleep_deep` | `deepSleepSeconds` | seconds in deep sleep |
| `sleep_light` | `lightSleepSeconds` | seconds in light sleep |
| `sleep_rem` | `remSleepSeconds` | seconds in REM sleep |
| `sleep_unmeasurable` | `unmeasurableSleepSeconds` | seconds not classified into a sleep level |
| `sleep_awake` | `awakeSleepSeconds` | seconds awake during the sleep window; not added to sleep |
| `nap_duration` | `napTimeSeconds` | seconds of naps associated with the date; separate from nightly sleep |
| `sleep_score` | `sleepScores.overall.value` | Garmin score, 0–100; only the recognized `overall` entry is used |
| `sleep_stress` | `avgSleepStress` | Garmin overnight stress scale; not a percentage or diagnosis |

Booleans, strings, negative/nonfinite values, explicitly INVALID scores and scores/stress above 100 are unavailable, not coerced. Unknown response shapes/score keys remain missing. Garmin's schema describes a score-component map; we do not guess alternatives to `overall`. These mappings and synthetic tests do not establish accuracy for every device. Compare representative values with Garmin Connect before claiming live validation.

## Dates and sleep-window times

The associated date is Garmin's `calendarDate`. It need not be the bedtime date. `sleepStartTimestampGMT` / `sleepEndTimestampGMT` become UTC ISO timestamps. Numeric values in these timestamp fields are milliseconds, not seconds; ISO date-time strings are also accepted. Documented GMT strings without an explicit offset are interpreted as UTC.

`sleepStartTimestampLocal` / `sleepEndTimestampLocal` retain recorded local wall time and an offset **only when supplied**. Numeric local values are decoded as wall-clock fields, not UTC instants. An offset-free local value has an unspecified historical timezone. We do not convert it using today's Garmin profile zone, derive a zone from an activity, or silently substitute auto-detected windows. Unparseable times are null; a reversed UTC window is marked invalid and masked. No mean bedtime is computed.

## Report behavior

`chart sleep` uses the supplied brand, a chat/phone layout by default, and a wide report layout with `--layout wide`. Duration appears as an unsmoothed blue line in hours. Stage bars appear only when all four stage values exist and their sum agrees with total sleep within 60 seconds. Missing stages are not inferred as zero and inconsistent totals are not repaired. Awake time and naps are excluded from the stack. The score panel has its own labeled 0–100 axis and available-night count. Gaps, missing score dates and incomplete-stage dates are explicit. Wearable estimates, source and fetch context accompany the report.

Use the [demo archive](VISUALIZATION.md#try-generated-demo-data) and `--synthetic` to test without health data. The flag labels supplied synthetic data; it does not anonymize real measurements.

## Interpretation and remaining work

Installed `agent-guide` guidance distinguishes measurements, Garmin assessments and hypotheses. A short history does not establish a baseline or causality. Show coverage, dates and freshness, and avoid turning an association into a precise prescription. The workbench supplies measurements, not a new readiness/recovery score.

Sleep need is deferred: the published `SleepNeedDTO.actual`/`baseline` descriptions do not give a usable unit contract. Body Battery summaries are deferred until daily aggregation and field meanings are validated. Detailed nap episodes, clock-time statistics and derived recovery scores are also outside this change; the documented daily nap duration is included. Actual provider secret entry, representative Connect comparisons and the first recurring execution need separate live validation.

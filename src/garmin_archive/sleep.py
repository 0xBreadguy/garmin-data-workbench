"""Small, dated sleep summaries over stored DailySleepDTO responses only.

Field definitions: docs/SLEEP.md. No raw samples, personal notes or coordinates
are returned. Historical wall times are never assigned today's profile zone.
"""
from __future__ import annotations

import math
import sqlite3
from datetime import UTC, datetime

from .queries import METRICS, METRIC_TITLES, get_trend

SLEEP_METRICS = tuple(name for name, spec in METRICS.items() if spec[0] == "sleep")
TIME_FIELDS = {"start_utc": "sleepStartTimestampGMT", "end_utc": "sleepEndTimestampGMT",
               "start_local": "sleepStartTimestampLocal", "end_local": "sleepEndTimestampLocal"}
STAGES = ("sleep_deep", "sleep_rem", "sleep_light", "sleep_unmeasurable")


def _timestamp(value, *, utc: bool) -> str | None:
    try:
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)) and math.isfinite(value):
            stamp = datetime.fromtimestamp(value / 1000, UTC)
            if not utc:
                stamp = stamp.replace(tzinfo=None)
        elif isinstance(value, str) and len(value) <= 64 and "T" in value:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if utc:
                stamp = stamp.replace(tzinfo=UTC) if stamp.tzinfo is None else stamp.astimezone(UTC)
        else:
            return None
        return stamp.isoformat()
    except (ValueError, OverflowError, OSError):
        return None


def complete_stages(values: dict) -> bool:
    """Stack only complete stages which reconcile to measured sleep time.

Awake time is deliberately excluded. Missing stages are never inferred as zero.
One minute of rounding tolerance is allowed; mismatches remain explicit.
"""
    return (all(values.get(key) is not None for key in (*STAGES, "sleep_duration"))
            and abs(sum(values[key] for key in STAGES) - values["sleep_duration"]) <= 60)


def get_sleep(db: sqlite3.Connection, start: str = "", end: str = "") -> dict:
    # One snapshot prevents a concurrent refresh from mixing a night's old
    # duration with its new score/status. Respect an existing caller transaction.
    if db.in_transaction:
        return _get_sleep(db, start, end)
    db.execute("BEGIN")
    try:
        return _get_sleep(db, start, end)
    finally:
        db.rollback()


def _get_sleep(db: sqlite3.Connection, start: str, end: str) -> dict:
    duration = get_trend(db, "sleep_duration", start, end)
    trends = {name: duration if name == "sleep_duration" else get_trend(db, name, duration["from"], duration["to"])
              for name in SLEEP_METRICS}
    nights = []
    for i, point in enumerate(duration["points"]):
        day = point["day"]
        # Only extract the four timestamp scalars after a successful refresh.
        # A response can contain large sample arrays; don't load the payload.
        row = db.execute(
            "SELECT s.status, d.data_json IS NOT NULL AS has_data, " + ", ".join(
                "CASE WHEN s.status='ok' THEN json_extract(d.data_json, '$." + field + "') END AS " + name
                for name, field in TIME_FIELDS.items()) +
            " FROM (SELECT 1) LEFT JOIN daily_data d ON d.dataset='sleep' AND d.day=?"
            " LEFT JOIN sync_state s ON s.dataset='sleep' AND s.day=?", (day, day)).fetchone()
        status = row["status"] or "not_checked"
        if status == "ok" and not row["has_data"]:
            status = "response_missing"
        # The scalar query already checks the associated Garmin calendarDate.
        valid_day = db.execute(
            "SELECT CASE WHEN s.status='ok' THEN json_extract(d.data_json, '$.calendarDate') END AS day "
            "FROM daily_data d LEFT JOIN sync_state s ON s.dataset=d.dataset AND s.day=d.day "
            "WHERE d.dataset='sleep' AND d.day=?", (day,)).fetchone()
        timing = {name: _timestamp(row[name], utc=name.endswith("utc"))
                  if status == "ok" and valid_day and valid_day["day"] in (None, day) else None
                  for name in TIME_FIELDS}
        timing_status = ("unavailable" if status != "ok" else
                         "available" if any(value is not None for value in timing.values()) else "not_returned")
        if (timing["start_utc"] and timing["end_utc"]
                and datetime.fromisoformat(timing["end_utc"]) < datetime.fromisoformat(timing["start_utc"])):
            timing = dict.fromkeys(TIME_FIELDS)
            timing_status = "invalid_window"
        values = {name: trend["points"][i]["value"] for name, trend in trends.items()}
        nights.append({"day": day, "status": status, "values": values,
            "missing_fields": [name for name, value in values.items() if value is None],
            "fetched_at": point["fetched_at"], "last_attempt": point["last_attempt"],
            "timing": timing, "timing_status": timing_status,
            "stages_complete": complete_stages(values)})
    statuses = {}
    for night in nights:
        statuses[night["status"]] = statuses.get(night["status"], 0) + 1
    return {"source": duration["source"], "dataset": "sleep", "from": duration["from"], "to": duration["to"],
        "preferences": duration["preferences"], "today_source": duration["today_source"],
        "fields": {name: {"field": ".".join(METRICS[name][1]), "unit": METRICS[name][2],
                          "label": METRIC_TITLES[name]} for name in SLEEP_METRICS},
        "timing_fields": TIME_FIELDS,
        "coverage": {"requested_days": len(nights), "statuses": statuses,
                     "fields": {name: {**trend["coverage"],
                          "mean_of_available_days": trend["mean_of_available_days"]} for name, trend in trends.items()}},
        "nights": nights,
        "notes": ["Dates are Garmin's associated calendarDate, not inferred bedtime dates.",
                  "UTC fields are instants; local fields retain source wall time and any supplied offset. "
                  "A local value without an offset has an unspecified historical timezone; never apply the current profile zone.",
                  "Total sleep excludes naps and awake time. Missing stages are not zero. "
                  "stages_complete requires all four stages and totals within 60 seconds of total sleep.",
                  "Non-ok refreshes mask retained values and timings. On ok responses, missing_fields are unreturned or invalid metrics.",
                  "Sleep stages and scores are wearable estimates. Separate observations, Garmin assessments and hypotheses; "
                  "a short history does not establish causes or a personal baseline."]}

"""Small, dated sleep summaries over stored DailySleepDTO responses only.

Field definitions: docs/SLEEP.md. No raw samples, personal notes or coordinates
are returned. Historical wall times are never assigned today's profile zone.
"""
from __future__ import annotations

import sqlite3
import json
from datetime import datetime, timedelta, timezone

from .queries import METRICS, METRIC_TITLES, get_trend, parse_day
from .timestamps import source_timestamp as _timestamp

SLEEP_METRICS = tuple(name for name, spec in METRICS.items() if spec[0] == "sleep")
TIME_FIELDS = {"start_utc": "sleepStartTimestampGMT", "end_utc": "sleepEndTimestampGMT",
               "start_local": "sleepStartTimestampLocal", "end_local": "sleepEndTimestampLocal"}
STAGES = ("sleep_deep", "sleep_rem", "sleep_light", "sleep_unmeasurable")
NEXT_NEED_FIELDS = {"next_day": "nextSleepNeed.calendarDate", "next_actual": "nextSleepNeed.actual",
                    "next_baseline": "nextSleepNeed.baseline"}


def _naps(raw, *, day, available, limit=20):
    result = {"status": "unavailable", "episodes": [], "total": None, "next_offset": None,
              "source_pointer": "/dailyNapDTOS", "duration_unit": "s", "offset_unit": "min"}
    if not available:
        return result
    if raw is None:
        result["status"] = "not_returned"
        return result
    try:
        items = json.loads(raw)
    except (TypeError, ValueError):
        items = None
    if not isinstance(items, list):
        result["status"] = "invalid"
        return result
    result.update(status="ok" if items else "empty", total=len(items), next_offset=limit if len(items) > limit else None)
    for i, item in enumerate(items[:limit]):
        episode = {"index": i, "status": "ok", "duration": None, "start_utc": None, "end_utc": None,
                   "start_local": None, "end_local": None, "source_code": None, "feedback": None}
        if not isinstance(item, dict):
            episode["status"] = "invalid"
        elif item.get("calendarDate") not in (None, day):
            episode["status"] = "date_mismatch"
        else:
            seconds = item.get("napTimeSec")
            if isinstance(seconds, int) and not isinstance(seconds, bool) and 0 <= seconds <= 86400:
                episode["duration"] = seconds
            episode["source_code"] = item.get("napSource") if type(item.get("napSource")) is int else None
            feedback = item.get("napFeedback")
            # Long/unknown source fields stay accessible through source-data.
            episode["feedback"] = feedback if isinstance(feedback, str) and len(feedback) <= 256 else None
            for name, field in (("start", "Start"), ("end", "End")):
                stamp = _timestamp(item.get(f"nap{field}TimestampGMT"), utc=True)
                episode[f"{name}_utc"] = stamp
                offset = item.get(f"nap{field}TimeOffset")
                if stamp and type(offset) is int and -840 <= offset <= 840:
                    episode[f"{name}_local"] = datetime.fromisoformat(stamp).astimezone(timezone(timedelta(minutes=offset))).isoformat()
            if (episode["start_utc"] and episode["end_utc"]
                    and datetime.fromisoformat(episode["end_utc"]) < datetime.fromisoformat(episode["start_utc"])):
                episode.update(status="invalid_window", start_utc=None, end_utc=None, start_local=None, end_local=None)
        result["episodes"].append(episode)
    return result


def _next_need(row, *, available: bool) -> dict:
    result = {"day": None, "actual": None, "baseline": None, "unit": "min", "status": "unavailable"}
    if not available:
        return result
    try:
        result["day"] = parse_day(row["next_day"]).isoformat()
    except ValueError:
        result["status"] = "date_not_returned"
        return result
    for name in ("actual", "baseline"):
        value = row["next_" + name]
        if row["next_" + name + "_type"] in {"integer", "real"} and 0 <= value <= 1440 and int(value) == value:
            result[name] = value
    result["status"] = ("ok" if result["actual"] is not None and result["baseline"] is not None else
                        "not_returned" if result["actual"] is None and result["baseline"] is None else "partial")
    return result


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
    nap_budget = 100
    for i, point in enumerate(duration["points"]):
        day = point["day"]
        # Only extract the four timestamp scalars after a successful refresh.
        # A response can contain large sample arrays; don't load the payload.
        row = db.execute(
            "SELECT s.status, d.data_json IS NOT NULL AS has_data, " + ", ".join(
                "CASE WHEN s.status='ok' THEN json_extract(d.data_json, '$." + field + "') END AS " + name
                for name, field in {**TIME_FIELDS, **NEXT_NEED_FIELDS, "naps": "dailyNapDTOS"}.items()) + ", " + ", ".join(
                "CASE WHEN s.status='ok' THEN json_type(d.data_json, '$." + field + "') END AS " + name + "_type"
                for name, field in NEXT_NEED_FIELDS.items() if name != "next_day") +
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
        naps = _naps(row["naps"], day=day,
                     available=status == "ok" and bool(valid_day) and valid_day["day"] in (None, day),
                     limit=min(20, nap_budget))
        nap_budget -= len(naps["episodes"])
        nights.append({"day": day, "status": status, "values": values,
            "missing_fields": [name for name, value in values.items() if value is None],
            "fetched_at": point["fetched_at"], "last_attempt": point["last_attempt"],
            "timing": timing, "timing_status": timing_status,
            "next_sleep_need": _next_need(row, available=status == "ok" and bool(valid_day) and valid_day["day"] in (None, day)),
            "naps": naps,
            "stages_complete": complete_stages(values)})
    statuses = {}
    for night in nights:
        statuses[night["status"]] = statuses.get(night["status"], 0) + 1
    return {"source": duration["source"], "dataset": "sleep", "from": duration["from"], "to": duration["to"],
        "preferences": duration["preferences"], "today_source": duration["today_source"],
        "fields": {name: {"field": ".".join(METRICS[name][1]), "unit": METRICS[name][2],
                          "label": METRIC_TITLES[name]} for name in SLEEP_METRICS},
        "timing_fields": TIME_FIELDS,
        "next_sleep_need_fields": {"day": "nextSleepNeed.calendarDate", "actual": "nextSleepNeed.actual",
                                   "baseline": "nextSleepNeed.baseline", "unit": "min"},
        "coverage": {"requested_days": len(nights), "statuses": statuses,
                     "fields": {name: {**trend["coverage"],
                          "mean_of_available_days": trend["mean_of_available_days"]} for name, trend in trends.items()}},
        "nights": nights,
        "notes": ["Dates are Garmin's associated calendarDate, not inferred bedtime dates.",
                  "UTC fields are instants; local fields retain source wall time and any supplied offset. "
                  "A local value without an offset has an unspecified historical timezone; never apply the current profile zone.",
                  "Total sleep excludes naps and awake time. Missing stages are not zero. "
                  "stages_complete requires all four stages and totals within 60 seconds of total sleep.",
                  "Nap episodes use dailyNapDTOS, napTimeSec and source UTC times. Local nap times use only the episode's explicit minute offsets. "
                  "Up to 20 episodes per day and 100 per report are summarized; use source_data at /dailyNapDTOS with next_offset for the remainder and full fields. "
                  "Daily nap duration is not reconstructed from missing or incomplete episodes.",
                  "Non-ok refreshes mask retained values and timings. On ok responses, missing_fields are unreturned or invalid metrics.",
                  "sleep_need is Garmin's dynamic actual recommendation in minutes; sleep_need_baseline is its baseline, not the adjusted recommendation. "
                  "next_sleep_need retains its own source date and is never shifted onto the associated night's trend. No deficit is inferred.",
                  "Sleep stages and scores are wearable estimates. Separate observations, Garmin assessments and hypotheses; "
                  "a short history does not establish causes or a personal baseline."]}

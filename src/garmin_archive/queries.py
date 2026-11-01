"""Bounded archive queries for agent-facing summaries and trends.

Mappings target fields in the Personal API daily summary and heart-rate
responses; unrecognized shapes remain missing instead of being guessed.
"""
from __future__ import annotations

import json
import math
import sqlite3
from datetime import date, timedelta
from typing import Any

# Output name -> (dataset, path within the dated response, unit).
METRICS = {
    "steps": ("daily_summary", ("movement", "steps"), "steps"),
    "distance": ("daily_summary", ("movement", "distanceMeters"), "m"),
    "resting_heart_rate": ("heart_rate", ("restingHeartRate",), "bpm"),
    "sleep_duration": ("sleep", ("sleepTimeSeconds",), "s"),
    "overnight_hrv": ("hrv", ("hrvSummary", "lastNightAvg"), "ms"),
}
DATASETS = ("daily_summary", "sleep", "hrv", "heart_rate", "body_battery", "activities")
MAX_TREND_DAYS = 90


def parse_day(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError
        return parsed
    except (TypeError, ValueError) as error:
        raise ValueError("Date must be YYYY-MM-DD") from error


def _dated_object(raw: Any, dataset: str, day: str) -> dict | None:
    if dataset == "daily_summary":
        if not isinstance(raw, dict) or not isinstance(raw.get("data"), list):
            return None
        matches = [item for item in raw["data"] if isinstance(item, dict) and item.get("calendarDate") == day]
        return matches[0] if len(matches) == 1 else None
    if not isinstance(raw, dict):
        return None
    # A single-day endpoint may omit calendarDate. If it supplies one, require a match.
    if raw.get("calendarDate") is not None and raw["calendarDate"] != day:
        return None
    if dataset == "hrv" and isinstance(raw.get("hrvSummary"), dict):
        summary_date = raw["hrvSummary"].get("calendarDate")
        if summary_date is not None and summary_date != day:
            return None
    return raw


def _point(db: sqlite3.Connection, dataset: str, path: tuple[str, ...], day: str) -> dict:
    row = db.execute(
        "SELECT d.data_json, d.fetched_at, s.status, s.error, s.updated_at AS last_attempt "
        "FROM (SELECT 1) LEFT JOIN daily_data d ON d.dataset=? AND d.day=? "
        "LEFT JOIN sync_state s ON s.dataset=? AND s.day=?", (dataset, day, dataset, day)
    ).fetchone()
    status = row["status"] or "not_checked"
    point = {"day": day, "status": status, "value": None, "fetched_at": row["fetched_at"],
             "last_attempt": row["last_attempt"], "error": row["error"]}
    # After an unsuccessful refresh, a previously stored value can still exist;
    # do not present that old value as a successful current observation.
    if status != "ok" or row["data_json"] is None:
        if status == "ok":
            point["status"] = "response_missing"
        return point
    obj: Any = _dated_object(json.loads(row["data_json"]), dataset, day)
    for key in path:
        obj = obj.get(key) if isinstance(obj, dict) else None
    if isinstance(obj, bool) or not isinstance(obj, (int, float)) or not math.isfinite(obj) or obj < 0:
        point["status"] = "metric_not_returned"
    else:
        point["value"] = obj
    return point


def metric_trend(db: sqlite3.Connection, metric: str, start: str, end: str) -> dict:
    if metric not in METRICS:
        raise ValueError("Unknown metric; available: " + ", ".join(METRICS))
    first, last = parse_day(start), parse_day(end)
    days = (last - first).days + 1
    if not 1 <= days <= MAX_TREND_DAYS:
        raise ValueError(f"Date range must be between 1 and {MAX_TREND_DAYS} days, inclusive")
    dataset, path, unit = METRICS[metric]
    points = [_point(db, dataset, path, (first + timedelta(days=i)).isoformat()) for i in range(days)]
    values = [p["value"] for p in points if p["value"] is not None]
    counts: dict[str, int] = {}
    for point in points:
        counts[point["status"]] = counts.get(point["status"], 0) + 1
    return {"metric": metric, "unit": unit, "source": "Garmin Personal API via local archive",
            "dataset": dataset, "field": ".".join(path), "from": start, "to": end,
            "coverage": {"requested_days": days, "days_with_value": len(values), "statuses": counts},
            "mean_of_available_days": round(sum(values) / len(values), 2) if values else None,
            "points": points}


def day_overview(db: sqlite3.Connection, day: str) -> dict:
    parse_day(day)
    metrics = {}
    for name, (dataset, path, unit) in METRICS.items():
        point = _point(db, dataset, path, day)
        metrics[name] = {"value": point["value"], "unit": unit, "status": point["status"],
                         "dataset": dataset, "field": ".".join(path), "fetched_at": point["fetched_at"]}
    states = {row["dataset"]: dict(row) for row in db.execute(
        "SELECT dataset, status, error, updated_at FROM sync_state WHERE day=?", (day,))}
    coverage = {dataset: states.get(dataset, {"dataset": dataset, "status": "not_checked",
                                               "error": None, "updated_at": None})
                for dataset in DATASETS}
    rows = [dict(row) for row in db.execute(
        "SELECT activity_id, day, json_extract(summary_json, '$.activityType.typeKey') AS type, "
        "json_extract(summary_json, '$.activityName') AS name, "
        "json_extract(summary_json, '$.distance') AS distance_m, "
        "json_extract(summary_json, '$.duration') AS duration_s, "
        "json_extract(summary_json, '$.averageHR') AS average_heart_rate_bpm, fit_status, updated_at "
        "FROM activities WHERE day=? ORDER BY activity_id DESC LIMIT 26", (day,))]
    return {"day": day, "source": "Garmin Personal API via local archive", "metrics": metrics,
            "coverage": coverage, "activities": rows[:25], "activities_truncated": len(rows) > 25,
            "activity_units": {"distance_m": "m", "duration_s": "s", "average_heart_rate_bpm": "bpm"},
            "note": "Values are returned only when recognized in a successfully fetched response."}

"""Bounded archive queries for agent-facing summaries and trends.

Mappings target recognized Personal API fields. Body Battery observations use
source column descriptors; unrecognized shapes remain missing instead of being guessed.
"""
from __future__ import annotations

import json
import math
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterator

from .provenance import archive_provenance
from .preferences import display_distance, local_today, profile_preferences
from .sources import DAILY_SOURCES

# Output name -> (dataset, path within the dated response, unit).
METRICS = {
    "steps": ("daily_summary", ("movement", "steps", "value"), "steps"),
    "distance": ("daily_summary", ("movement", "steps", "distanceInMeters"), "m"),
    "resting_heart_rate": ("heart_rate", ("restingHeartRate",), "bpm"),
    "sleep_duration": ("sleep", ("sleepTimeSeconds",), "s"),
    "overnight_hrv": ("hrv", ("hrvSummary", "lastNightAvg"), "ms"),
    "sleep_score": ("sleep", ("sleepScores", "overall", "value"), "score"),
    "sleep_deep": ("sleep", ("deepSleepSeconds",), "s"),
    "sleep_light": ("sleep", ("lightSleepSeconds",), "s"),
    "sleep_rem": ("sleep", ("remSleepSeconds",), "s"),
    "sleep_awake": ("sleep", ("awakeSleepSeconds",), "s"),
    "sleep_unmeasurable": ("sleep", ("unmeasurableSleepSeconds",), "s"),
    "sleep_stress": ("sleep", ("avgSleepStress",), "Garmin stress"),
    "nap_duration": ("sleep", ("napTimeSeconds",), "s"),
    "sleep_need": ("sleep", ("sleepNeed", "actual"), "min"),
    "sleep_need_baseline": ("sleep", ("sleepNeed", "baseline"), "min"),
    "body_battery_charged": ("body_battery", ("charged",), "points"),
    "body_battery_drained": ("body_battery", ("drained",), "points"),
    "body_battery_min": ("body_battery", ("observed_min",), "Body Battery"),
    "body_battery_max": ("body_battery", ("observed_max",), "Body Battery"),
    "body_battery_first": ("body_battery", ("observed_first",), "Body Battery"),
    "body_battery_last": ("body_battery", ("observed_last",), "Body Battery"),
}
METRIC_TITLES = {"steps": "Daily steps", "distance": "Daily distance",
    "sleep_duration": "Sleep duration", "resting_heart_rate": "Resting heart rate",
    "overnight_hrv": "Overnight HRV", "sleep_score": "Sleep score", "sleep_deep": "Deep sleep",
    "sleep_light": "Light sleep", "sleep_rem": "REM sleep", "sleep_awake": "Awake during sleep",
    "sleep_unmeasurable": "Unclassified sleep", "sleep_stress": "Overnight stress",
    "nap_duration": "Nap duration", "sleep_need": "Sleep need", "sleep_need_baseline": "Baseline sleep need",
    "body_battery_charged": "Body Battery charged", "body_battery_drained": "Body Battery drained",
    "body_battery_min": "Observed Body Battery min", "body_battery_max": "Observed Body Battery max",
    "body_battery_first": "Body Battery first reading", "body_battery_last": "Body Battery last reading"}

# Daily scalar conveniences over the legacy summary, whose documented fields
# have explicit units. Other native fields (including signed values, enums and
# arrays) remain available through source-data/source-series without guessing
# an interpretation or an aggregation.
DAILY_METRICS = {
    "calories_total": ("totalKilocalories", "kcal", "Total calories burned"),
    "calories_active": ("activeKilocalories", "kcal", "Active calories burned"),
    "calories_bmr": ("bmrKilocalories", "kcal", "Basal calories burned"),
    "calories_consumed": ("consumedKilocalories", "kcal", "Calories consumed"),
    "calorie_goal": ("netCalorieGoal", "kcal", "Net calorie goal"),
    "steps_goal": ("dailyStepGoal", "steps", "Daily step goal"),
    "distance_total": ("totalDistanceMeters", "m", "Total distance"),
    "wheelchair_pushes": ("totalPushes", "pushes", "Wheelchair pushes"),
    "wheelchair_push_goal": ("dailyPushesGoal", "pushes", "Daily push goal"),
    "wheelchair_distance": ("totalPushDistance", "m", "Wheelchair push distance"),
    "highly_active_duration": ("highlyActiveSeconds", "s", "Highly active time"),
    "active_duration": ("activeSeconds", "s", "Active time"),
    "sedentary_duration": ("sedentarySeconds", "s", "Sedentary time"),
    "intensity_moderate": ("moderateIntensityMinutes", "min", "Moderate intensity minutes"),
    "intensity_vigorous": ("vigorousIntensityMinutes", "min", "Vigorous intensity minutes"),
    "intensity_weekly_goal": ("intensityMinutesGoal", "min", "Weekly intensity minutes goal"),
    "floors_ascended": ("floorsAscended", "floors", "Floors ascended"),
    "floors_descended": ("floorsDescended", "floors", "Floors descended"),
    "floors_goal": ("userFloorsAscendedGoal", "floors", "Daily floors goal"),
    "ascent": ("floorsAscendedInMeters", "m", "Daily ascent"),
    "descent": ("floorsDescendedInMeters", "m", "Daily descent"),
    "stress_average": ("averageStressLevel", "Garmin stress", "Average stress"),
    "stress_max": ("maxStressLevel", "Garmin stress", "Maximum stress"),
    "stress_duration": ("stressDuration", "s", "Stress time"),
    "stress_rest_duration": ("restStressDuration", "s", "Rest time"),
    "stress_activity_duration": ("activityStressDuration", "s", "Activity stress time"),
    "stress_uncategorized_duration": ("uncategorizedStressDuration", "s", "Uncategorized stress time"),
    "stress_low_duration": ("lowStressDuration", "s", "Low stress time"),
    "stress_medium_duration": ("mediumStressDuration", "s", "Medium stress time"),
    "stress_high_duration": ("highStressDuration", "s", "High stress time"),
    "hydration": ("hydrationValueInML", "mL", "Hydration consumed"),
    "hydration_goal": ("hydrationGoalInML", "mL", "Hydration goal"),
    "spo2_average": ("averageSpo2", "%", "Average Pulse Ox"),
    "spo2_lowest": ("lowestSpo2", "%", "Lowest Pulse Ox"),
    "respiration_waking": ("avgWakingRespirationValue", "breaths/min", "Average waking respiration"),
    "respiration_highest": ("highestRespirationValue", "breaths/min", "Highest respiration"),
    "respiration_lowest": ("lowestRespirationValue", "breaths/min", "Lowest respiration"),
}
for _name, (_field, _unit, _title) in DAILY_METRICS.items():
    METRICS[_name] = ("daily_summary_legacy", (_field,), _unit)
    METRIC_TITLES[_name] = _title
for _name, _field, _unit, _title in (
    ("heart_rate_min", "minHeartRate", "bpm", "Minimum heart rate"),
    ("heart_rate_max", "maxHeartRate", "bpm", "Maximum heart rate"),
):
    METRICS[_name] = ("heart_rate", (_field,), _unit)
    METRIC_TITLES[_name] = _title
DATASETS = (*DAILY_SOURCES, "activities")
MAX_TREND_DAYS = 90


def health_response(db: sqlite3.Connection, dataset: str, day: str, *, max_bytes: int | None = None) -> dict:
    """Metadata-aware fallback, masking retained responses after failed refreshes."""
    if dataset not in DATASETS or dataset == "activities":
        raise ValueError("Unknown daily health dataset")
    parse_day(day)
    row = db.execute(
        "SELECT d.data_json, d.fetched_at, s.status, s.error, s.updated_at AS last_attempt "
        "FROM (SELECT 1) LEFT JOIN daily_data d ON d.dataset=? AND d.day=? "
        "LEFT JOIN sync_state s ON s.dataset=? AND s.day=?", (dataset, day, dataset, day)).fetchone()
    raw, status = row["data_json"], row["status"] or "not_checked"
    if status == "ok" and raw is None:
        status = "response_missing"
    if status in {"ok", "empty"} and raw is not None and max_bytes is not None and len(raw.encode("utf-8")) > max_bytes:
        raise ValueError("Stored response is too large for MCP; inspect it locally with health --metadata")
    return {"archive_provenance": archive_provenance(db), "source": "local archive", "dataset": dataset, "day": day, "status": status,
            "error": row["error"],
            "fetched_at": row["fetched_at"], "last_attempt": row["last_attempt"],
            "retained_data_available": raw is not None,
            "data": json.loads(raw) if raw is not None and status in {"ok", "empty"} else None}


@contextmanager
def open_archive(data_dir: Path) -> Iterator[sqlite3.Connection]:
    """Read an existing archive without creating or migrating it."""
    database = (data_dir.expanduser() / "archive.sqlite3").resolve()
    connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def get_day(db: sqlite3.Connection, day: str = "") -> dict:
    """Shared CLI/MCP overview with Garmin date and presentation defaults."""
    prefs = profile_preferences(db)
    today, today_source = local_today(prefs)
    result = day_overview(db, day or today.isoformat())
    distance = result["metrics"]["distance"]
    distance["display_value"], distance["display_unit"] = display_distance(distance["value"], prefs)
    for activity in result["activities"]:
        activity["display_distance"], activity["display_distance_unit"] = display_distance(activity["distance_m"], prefs)
    result.update({"preferences": prefs, "today_source": today_source})
    return result


def get_trend(db: sqlite3.Connection, metric: str, start: str = "", end: str = "") -> dict:
    """Shared CLI/MCP trend, bounded to 90 days by metric_trend."""
    first, last, prefs, today_source = query_range(db, start, end)
    result = metric_trend(db, metric, first.isoformat(), last.isoformat())
    if metric == "distance":
        _, unit = display_distance(None, prefs)
        result["display"] = {"unit": unit,
            "points": [{"day": point["day"], "value": display_distance(point["value"], prefs)[0]}
                       for point in result["points"]],
            "mean_of_available_days": display_distance(result["mean_of_available_days"], prefs)[0]}
    result.update({"preferences": prefs, "today_source": today_source})
    return result


def query_range(db: sqlite3.Connection, start: str = "", end: str = "") -> tuple:
    prefs = profile_preferences(db)
    today, today_source = local_today(prefs)
    last = parse_day(end) if end else today
    first = parse_day(start) if start else last - timedelta(days=6)
    if not 1 <= (last - first).days + 1 <= MAX_TREND_DAYS:
        raise ValueError(f"Date range must be between 1 and {MAX_TREND_DAYS} days, inclusive")
    return first, last, prefs, today_source


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


def _point(db: sqlite3.Connection, dataset: str, path: tuple[str, ...], day: str, *, body_result: dict | None = None) -> dict:
    if dataset == "body_battery":
        from .body_battery import BODY_FIELDS, body_battery_day
        result = body_result if body_result is not None else body_battery_day(db, day)
        name = next(name for name in BODY_FIELDS if METRICS[name][1] == path)
        value = result["values"][name]
        return {"day": day, "value": value, "status": result["status"] if result["status"] != "ok" else
                    ("ok" if value is not None else "metric_not_returned"),
                "observed_at": result["first_observed_at"] if name == "body_battery_first" else
                               result["last_observed_at"] if name == "body_battery_last" else None,
                "valid_readings": result["valid_readings"],
                "fetched_at": result["fetched_at"], "last_attempt": result["last_attempt"], "error": result["error"]}
    # Single-day responses can contain thousands of samples. Extract only the
    # summary scalar in SQLite instead of copying and parsing the full payload
    # in Python on every agent query. Daily summaries need their array checked
    # for duplicate/mismatched dates and use the conservative path below.
    if dataset == "daily_summary":
        row = db.execute(
            "SELECT d.data_json, d.fetched_at, s.status, s.error, s.updated_at AS last_attempt "
            "FROM (SELECT 1) LEFT JOIN daily_data d ON d.dataset=? AND d.day=? "
            "LEFT JOIN sync_state s ON s.dataset=? AND s.day=?", (dataset, day, dataset, day)
        ).fetchone()
    else:
        json_path = "$." + ".".join(path)
        row = db.execute(
            "SELECT d.data_json IS NOT NULL AS has_data, d.fetched_at, s.status, s.error, "
            "s.updated_at AS last_attempt, "
            "CASE WHEN s.status='ok' THEN json_extract(d.data_json, ?) END AS metric_value, "
            "CASE WHEN s.status='ok' THEN json_type(d.data_json, ?) END AS metric_type, "
            "CASE WHEN s.status='ok' THEN json_extract(d.data_json, '$.sleepScores.overall.qualifierKey') END AS score_qualifier, "
            "CASE WHEN s.status='ok' THEN json_extract(d.data_json, '$.calendarDate') END AS root_day, "
            "CASE WHEN s.status='ok' THEN json_extract(d.data_json, '$.sleepNeed.calendarDate') END AS need_day, "
            "CASE WHEN s.status='ok' THEN json_extract(d.data_json, '$.hrvSummary.calendarDate') END AS hrv_day "
            "FROM (SELECT 1) LEFT JOIN daily_data d ON d.dataset=? AND d.day=? "
            "LEFT JOIN sync_state s ON s.dataset=? AND s.day=?",
            (json_path, json_path, dataset, day, dataset, day),
        ).fetchone()
    status = row["status"] or "not_checked"
    point = {"day": day, "status": status, "value": None, "fetched_at": row["fetched_at"],
             "last_attempt": row["last_attempt"], "error": row["error"]}
    # After an unsuccessful refresh, a previously stored value can still exist;
    # do not present that old value as a successful current observation.
    has_data = row["data_json"] is not None if dataset == "daily_summary" else row["has_data"]
    if status != "ok" or not has_data:
        if status == "ok":
            point["status"] = "response_missing"
        return point
    if dataset == "daily_summary":
        obj: Any = _dated_object(json.loads(row["data_json"]), dataset, day)
        for key in path:
            obj = obj.get(key) if isinstance(obj, dict) else None
    else:
        matches_day = row["root_day"] in (None, day) and (dataset != "hrv" or row["hrv_day"] in (None, day))
        obj = row["metric_value"] if matches_day and row["metric_type"] in ("integer", "real") else None
        if path == ("sleepScores", "overall", "value") and row["score_qualifier"] == "INVALID":
            obj = None
        if path[0] == "sleepNeed" and row["need_day"] not in (None, day):
            obj = None
    bounded_score = path in (("sleepScores", "overall", "value"), ("avgSleepStress",),
                            ("averageStressLevel",), ("maxStressLevel",), ("averageSpo2",), ("lowestSpo2",))
    if (isinstance(obj, bool) or not isinstance(obj, (int, float)) or not math.isfinite(obj) or obj < 0
            or (bounded_score and obj > 100)
            or (path[0] == "sleepNeed" and (obj > 1440 or obj != int(obj)))):
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
    field_info = {"field": ".".join(path)}
    if dataset == "body_battery":
        from .body_battery import BODY_FIELDS
        field_info = BODY_FIELDS[metric]
    return {"archive_provenance": archive_provenance(db), "metric": metric, "unit": unit, "source": "Garmin Personal API via local archive",
            "dataset": dataset, **field_info, "from": start, "to": end,
            "coverage": {"requested_days": days, "days_with_value": len(values), "statuses": counts},
            "mean_of_available_days": round(sum(values) / len(values), 2) if values else None,
            "points": points}


def day_overview(db: sqlite3.Connection, day: str) -> dict:
    parse_day(day)
    metrics = {}
    from .body_battery import BODY_FIELDS, body_battery_day
    body_result = body_battery_day(db, day)
    for name, (dataset, path, unit) in METRICS.items():
        point = _point(db, dataset, path, day, body_result=body_result)
        metrics[name] = {"value": point["value"], "unit": unit, "status": point["status"],
                         "dataset": dataset, "field": ".".join(path), "fetched_at": point["fetched_at"]}
        if dataset == "body_battery":
            metrics[name].update(BODY_FIELDS[name])
            metrics[name].update({"observed_at": point["observed_at"], "valid_readings": point["valid_readings"]})
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
    return {"archive_provenance": archive_provenance(db), "day": day, "source": "Garmin Personal API via local archive", "metrics": metrics,
            "coverage": coverage, "activities": rows[:25], "activities_truncated": len(rows) > 25,
            "activity_units": {"distance_m": "m", "duration_s": "s", "average_heart_rate_bpm": "bpm"},
            "note": "Values are returned only when recognized in a successfully fetched response."}

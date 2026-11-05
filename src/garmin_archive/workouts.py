"""Bounded activity filtering and covered totals from stored search summaries."""
from __future__ import annotations

import math
import sqlite3
from datetime import timedelta

from .preferences import display_distance, profile_preferences
from .provenance import archive_provenance
from .queries import parse_day, query_range


def activity_filter(start: str = "", end: str = "", activity_type: str = "") -> tuple[str, list]:
    if start:
        parse_day(start)
    if end:
        parse_day(end)
    if start and end and start > end:
        raise ValueError("--from must not be after --to")
    if not isinstance(activity_type, str) or len(activity_type) > 100:
        raise ValueError("Activity type must be a native typeKey of at most 100 characters")
    clauses, values = [], []
    for clause, value in (("a.day >= ?", start), ("a.day <= ?", end),
                          ("json_extract(a.summary_json, '$.activityType.typeKey') = ?", activity_type)):
        if value:
            clauses.append(clause)
            values.append(value)
    return " AND ".join(clauses) or "1", values


def list_activities(db: sqlite3.Connection, start: str = "", end: str = "", activity_type: str = "",
                    *, limit: int = 20, offset: int = 0) -> dict:
    where, args = activity_filter(start, end, activity_type)
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10000:
        raise ValueError("Limit must be between 1 and 10000")
    if isinstance(offset, bool) or not isinstance(offset, int) or not 0 <= offset <= 2**63 - 1:
        raise ValueError("Offset must be a nonnegative SQLite integer")
    rows = [dict(row) for row in db.execute(
        "SELECT a.activity_id, a.day, json_extract(a.summary_json, '$.activityType.typeKey') AS type, "
        "json_extract(a.summary_json, '$.activityName') AS name, a.fit_status, a.updated_at, "
        "COALESCE(s.status, 'not_checked') AS status, s.updated_at AS last_attempt, "
        "CASE WHEN s.status='ok' AND json_type(a.summary_json, '$.distance') IN ('integer','real') THEN json_extract(a.summary_json, '$.distance') END AS distance_m, "
        "CASE WHEN s.status='ok' AND json_type(a.summary_json, '$.duration') IN ('integer','real') THEN json_extract(a.summary_json, '$.duration') END AS duration_s, "
        "CASE WHEN s.status='ok' AND json_type(a.summary_json, '$.averageHR') IN ('integer','real') THEN json_extract(a.summary_json, '$.averageHR') END AS average_heart_rate_bpm "
        "FROM activities a LEFT JOIN sync_state s ON s.dataset='activities' AND s.day=a.day "
        f"WHERE {where} ORDER BY a.day DESC, a.activity_id DESC LIMIT ? OFFSET ?", [*args, limit + 1, offset])]
    prefs = profile_preferences(db)
    for row in rows:
        for key in ("distance_m", "duration_s", "average_heart_rate_bpm"):
            value = row[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                row[key] = None
        row["display_distance"], row["display_distance_unit"] = display_distance(row["distance_m"], prefs)
    return {"archive_provenance": archive_provenance(db), "source": "local archive", "preferences": prefs,
            "activities": rows[:limit], "next_offset": offset + limit if len(rows) > limit else None,
            "units": {"distance_m": "m", "duration_s": "s", "average_heart_rate_bpm": "bpm"}}


def _totals(days: list[dict], prefs: dict) -> dict:
    available = [day for day in days if day["status"] in {"ok", "empty"}]
    count = sum(day["activity_count"] for day in available) if available else None
    result = {"activity_count": count}
    for metric in ("distance_m", "duration_s"):
        valid = sum(day[metric + "_activities"] for day in available)
        result[metric + "_activities"] = valid
        total = None
        if valid and not any(day[metric] is None and day[metric + "_activities"] for day in available):
            try:
                total = math.fsum(day[metric] for day in available if day[metric] is not None)
            except OverflowError:
                pass
        result[metric] = total if valid else 0 if count == 0 else None
    result["display_distance"], result["display_distance_unit"] = display_distance(result["distance_m"], prefs)
    return result


def get_workout_summary(db: sqlite3.Connection, start: str = "", end: str = "", activity_type: str = "") -> dict:
    first, last, prefs, today_source = query_range(db, start, end)
    where, args = activity_filter(first.isoformat(), last.isoformat(), activity_type)
    # Parent IDs are tested before sport/date filtering. Otherwise a parent and
    # its component activities could both contribute to volume totals.
    rows = {row["day"]: dict(row) for row in db.execute(
        "WITH selected AS (SELECT a.day, "
        "CASE WHEN json_type(a.summary_json, '$.distance') IN ('integer','real') "
        "AND json_extract(a.summary_json, '$.distance') BETWEEN 0 AND 1.7976931348623157e308 THEN json_extract(a.summary_json, '$.distance') END AS distance_m, "
        "CASE WHEN json_type(a.summary_json, '$.duration') IN ('integer','real') "
        "AND json_extract(a.summary_json, '$.duration') BETWEEN 0 AND 1.7976931348623157e308 THEN json_extract(a.summary_json, '$.duration') END AS duration_s "
        "FROM activities a JOIN sync_state s ON s.day=a.day AND s.dataset='activities' AND s.status='ok' "
        f"WHERE {where} AND a.activity_id NOT IN ("
        "SELECT json_extract(summary_json, '$.parentId') FROM activities "
        "WHERE json_type(summary_json, '$.parentId')='integer' AND json_extract(summary_json, '$.parentId') > 0)) "
        "SELECT day, COUNT(*) AS activity_count, SUM(CAST(distance_m AS REAL)) AS distance_m, SUM(CAST(duration_s AS REAL)) AS duration_s, "
        "COUNT(distance_m) AS distance_m_activities, COUNT(duration_s) AS duration_s_activities "
        "FROM selected GROUP BY day", args)}
    states = {row["day"]: dict(row) for row in db.execute(
        "SELECT day, status, error, updated_at AS last_attempt FROM sync_state "
        "WHERE dataset='activities' AND day BETWEEN ? AND ?", (first.isoformat(), last.isoformat()))}
    days, weeks, statuses = [], {}, {}
    for index in range((last - first).days + 1):
        day = first + timedelta(days=index)
        iso = day.isoformat()
        state = states.get(iso, {"status": "not_checked", "error": None, "last_attempt": None})
        point = {"day": iso, **state}
        point.update(rows.get(iso, {"activity_count": 0, "distance_m": 0, "duration_s": 0,
                                   "distance_m_activities": 0, "duration_s_activities": 0}))
        for metric in ("distance_m", "duration_s"):
            if point[metric] is not None and not math.isfinite(point[metric]):
                point[metric] = None
        if state["status"] not in {"ok", "empty"}:
            point.update({"activity_count": None, "distance_m": None, "duration_s": None})
        days.append(point)
        weeks.setdefault((day - timedelta(days=day.weekday())).isoformat(), []).append(point)
        statuses[point["status"]] = statuses.get(point["status"], 0) + 1
    return {"archive_provenance": archive_provenance(db), "source": "stored Garmin activity search summaries",
            "from": first.isoformat(), "to": last.isoformat(), "activity_type": activity_type or None,
            "preferences": prefs, "today_source": today_source, "units": {"distance_m": "m", "duration_s": "s"},
            "coverage": {"requested_days": len(days), "days_available": sum(statuses.get(s, 0) for s in ("ok", "empty")),
                         "statuses": statuses}, "totals": _totals(days, prefs), "days": days,
            "weeks": [{"week_start": monday, "from": group[0]["day"], "to": group[-1]["day"],
                       "days_available": sum(d["status"] in {"ok", "empty"} for d in group),
                       **_totals(group, prefs)} for monday, group in weeks.items()],
            "notes": ["Weeks begin Monday and are clipped to the requested dates. Dates are stored activity dates; no historical zone is inferred.",
                      "Totals use available summaries only; missing fields and failed/unchecked dates are not zero. Field counts show missing measurements.",
                      "Nonfinite source values and totals outside the numeric range are unavailable.",
                      "Parents with stored child activities are excluded before filtering. Missing children can leave multisport totals incomplete.",
                      "Other overlapping recordings remain separate. Duration is Garmin's summary duration, not elapsed time or time deduplicated across recordings.",
                      "An empty search is not proof Garmin has returned complete history; retained activity rows do not track deletions."]}

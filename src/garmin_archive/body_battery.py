"""Descriptor-aware summaries of stored BodyBatteryDailyReportDTO arrays.

Only observed daily statistics are derived. No interpolation, live requests,
raw readings, event text or assumed fixed column positions reach the output.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timedelta

from .timestamps import source_timestamp

BODY_FIELDS = {
    "body_battery_charged": {"field": "charged", "aggregation": "reported daily charge", "unit": "points"},
    "body_battery_drained": {"field": "drained", "aggregation": "reported daily drain", "unit": "points"},
    "body_battery_min": {"field": "bodyBatteryValuesArray", "aggregation": "minimum observed level", "unit": "Body Battery"},
    "body_battery_max": {"field": "bodyBatteryValuesArray", "aggregation": "maximum observed level", "unit": "Body Battery"},
    "body_battery_first": {"field": "bodyBatteryValuesArray", "aggregation": "first observed level by UTC timestamp", "unit": "Body Battery"},
    "body_battery_last": {"field": "bodyBatteryValuesArray", "aggregation": "last observed level by UTC timestamp", "unit": "Body Battery"},
}
MAX_READING_ROWS = 100_000


def _number(value, *, level: bool = False):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    # Reported amounts are int32 in Garmin's schema. Bounded comparisons also
    # reject NaN/infinity and huge integers without float-conversion overflow.
    if not 0 <= value <= (100 if level else 2**31 - 1) or (not level and value != int(value)):
        return None
    return value


def _columns(descriptors) -> dict | None:
    if not isinstance(descriptors, list):
        return None
    columns, used = {}, set()
    for item in descriptors:
        if not isinstance(item, dict):
            return None
        key, index = item.get("bodyBatteryValueDescriptorKey"), item.get("bodyBatteryValueDescriptorIndex")
        if not isinstance(key, str) or isinstance(index, bool) or not isinstance(index, int) or index < 0 or index in used:
            return None
        used.add(index)
        if key in {"timestamp", "bodyBatteryLevel"}:
            if key in columns:
                return None
            columns[key] = index
    return columns if len(columns) == 2 else None


def body_battery_day(db: sqlite3.Connection, day: str) -> dict:
    row = db.execute(
        "SELECT s.status, s.error, s.updated_at AS last_attempt, d.fetched_at, "
        "d.data_json IS NOT NULL AS has_data, CASE WHEN s.status='ok' THEN d.data_json END AS payload "
        "FROM (SELECT 1) LEFT JOIN daily_data d ON d.dataset='body_battery' AND d.day=? "
        "LEFT JOIN sync_state s ON s.dataset='body_battery' AND s.day=?", (day, day)).fetchone()
    status = row["status"] or "not_checked"
    if status == "ok" and not row["has_data"]:
        status = "response_missing"
    result = {"day": day, "status": status, "error": row["error"], "fetched_at": row["fetched_at"],
        "last_attempt": row["last_attempt"], "values": dict.fromkeys(BODY_FIELDS), "report_status": "unavailable",
        "readings_status": "unavailable", "readings_seen": 0, "valid_readings": 0, "invalid_readings": 0,
        "duplicate_readings": 0, "conflicting_timestamps": 0, "first_observed_at": None, "last_observed_at": None,
        "window_start_utc": None, "window_end_utc": None}
    if status != "ok":
        return result
    payload = json.loads(row["payload"])
    if not isinstance(payload, list):
        result["report_status"] = "unrecognized_response"
        return result
    matches = [item for item in payload if isinstance(item, dict) and item.get("date") == day]
    if len(matches) != 1:
        result["report_status"] = "ambiguous_date" if matches else "date_not_returned"
        return result
    report = matches[0]
    result["report_status"] = "ok"
    for field in ("charged", "drained"):
        result["values"]["body_battery_" + field] = _number(report.get(field))
    for side in ("start", "end"):
        result["window_" + side + "_utc"] = source_timestamp(report.get(side + "TimestampGMT"), utc=True)
    first, last = result["window_start_utc"], result["window_end_utc"]
    if first and last and datetime.fromisoformat(first) > datetime.fromisoformat(last):
        result["readings_status"] = "invalid_window"
        return result
    rows = report.get("bodyBatteryValuesArray")
    if not isinstance(rows, list):
        result["readings_status"] = "readings_not_returned"
        return result
    result["readings_seen"] = len(rows)
    if len(rows) > MAX_READING_ROWS:
        result["readings_status"] = "too_many_readings"
        return result
    columns = _columns(report.get("bodyBatteryValueDescriptorDTOList"))
    if columns is None:
        result["readings_status"] = "descriptors_unavailable_or_ambiguous"
        return result
    samples: dict[datetime, set] = {}
    for reading in rows:
        if not isinstance(reading, list) or len(reading) <= max(columns.values()):
            result["invalid_readings"] += 1
            continue
        raw_time = reading[columns["timestamp"]]
        # Sample timestamps are milliseconds or explicit-offset ISO instants.
        if isinstance(raw_time, str):
            try:
                if len(raw_time) > 64 or datetime.fromisoformat(raw_time.replace("Z", "+00:00")).tzinfo is None:
                    raw_time = None
            except ValueError:
                raw_time = None
        stamp = source_timestamp(raw_time, utc=True)
        level = _number(reading[columns["bodyBatteryLevel"]], level=True)
        instant = datetime.fromisoformat(stamp) if stamp else None
        if (instant is None or level is None or abs((instant.date() - date.fromisoformat(day)).days) > 1
                or (first and instant < datetime.fromisoformat(first))
                or (last and instant > datetime.fromisoformat(last))):
            result["invalid_readings"] += 1
            continue
        if instant in samples and level in samples[instant]:
            result["duplicate_readings"] += 1
        samples.setdefault(instant, set()).add(level)
    result["conflicting_timestamps"] = sum(len(levels) != 1 for levels in samples.values())
    valid = sorted((instant, next(iter(levels))) for instant, levels in samples.items() if len(levels) == 1)
    result["valid_readings"] = len(valid)
    result["readings_status"] = "available" if valid else "no_valid_readings"
    if valid:
        values = result["values"]
        values["body_battery_min"] = min(level for _, level in valid)
        values["body_battery_max"] = max(level for _, level in valid)
        values["body_battery_first"], values["body_battery_last"] = valid[0][1], valid[-1][1]
        result["first_observed_at"], result["last_observed_at"] = valid[0][0].isoformat(), valid[-1][0].isoformat()
    return result


def get_body_battery(db: sqlite3.Connection, start: str = "", end: str = "") -> dict:
    if db.in_transaction:
        return _get_body_battery(db, start, end)
    db.execute("BEGIN")
    try:
        return _get_body_battery(db, start, end)
    finally:
        db.rollback()


def _get_body_battery(db: sqlite3.Connection, start: str, end: str) -> dict:
    from .queries import query_range
    from .provenance import archive_provenance
    first, last, prefs, today_source = query_range(db, start, end)
    days = [body_battery_day(db, (first + timedelta(days=i)).isoformat()) for i in range((last - first).days + 1)]
    coverage = {}
    for name in BODY_FIELDS:
        values = [day["values"][name] for day in days if day["values"][name] is not None]
        coverage[name] = {"days_with_value": len(values),
                          "mean_of_available_days": round(sum(values) / len(values), 2) if values else None}
    statuses = {}
    for day in days:
        day["missing_fields"] = [name for name in BODY_FIELDS if day["values"][name] is None]
        statuses[day["status"]] = statuses.get(day["status"], 0) + 1
    return {"archive_provenance": archive_provenance(db), "source": "Garmin Personal API via local archive", "dataset": "body_battery", "from": first.isoformat(),
        "to": last.isoformat(), "preferences": prefs, "today_source": today_source, "fields": BODY_FIELDS,
        "coverage": {"requested_days": len(days), "statuses": statuses, "fields": coverage}, "days": days,
        "notes": ["Levels use Garmin's 0–100 Body Battery scale; charge/drain are reported amounts in scale points, not percentages.",
                  "Min/max/first/last summarize valid observed samples only. They are not a complete-day guarantee or a live current value.",
                  "Columns use source descriptors; no fixed-position fallback. Conflicting timestamps and invalid samples are excluded.",
                  "First/last refer to UTC sample order within any supplied reporting window, not wake-up/bedtime or the current profile timezone.",
                  "Failed refreshes mask retained data. Means average available daily statistics, not an intraday/time-weighted average."]}

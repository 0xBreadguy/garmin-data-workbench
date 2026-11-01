"""Garmin profile defaults, retained locally for offline agent queries."""
from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def clean_profile(payload: Any) -> tuple[str | None, str | None]:
    if not isinstance(payload, dict):
        raise ValueError("Unexpected profile settings response")
    measurement = payload.get("measurementSystem")
    if not isinstance(measurement, str) or not measurement or len(measurement) > 64:
        measurement = None
    zone = payload.get("timeZone")
    if not isinstance(zone, str) or not zone or len(zone) > 128:
        zone = None
    if zone is not None:
        try:
            ZoneInfo(zone)
        except (ZoneInfoNotFoundError, ValueError):
            zone = None
    if measurement is None and zone is None:
        raise ValueError("Profile settings contain no usable defaults")
    return measurement, zone


def profile_preferences(connection: sqlite3.Connection) -> dict:
    has_table = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='profile_preferences'"
    ).fetchone()
    row = connection.execute(
        "SELECT measurement_system, time_zone, fetched_at FROM profile_preferences WHERE id=1"
    ).fetchone() if has_table else None
    if row is None:
        return {"source": "unavailable", "measurement_system": None, "time_zone": None, "fetched_at": None}
    return {"source": "Garmin profile", "measurement_system": row["measurement_system"],
            "time_zone": row["time_zone"], "fetched_at": row["fetched_at"]}


def local_today(preferences: dict, instant: datetime | None = None) -> tuple[date, str]:
    zone = preferences.get("time_zone")
    if zone:
        try:
            current = instant or datetime.now(UTC)
            return current.astimezone(ZoneInfo(zone)).date(), "Garmin profile"
        except (ZoneInfoNotFoundError, ValueError):
            pass
    # Host local date is a fallback only, not a claim about the user's location.
    if instant is not None:
        return instant.astimezone().date(), "host local timezone"
    return date.today(), "host local timezone"


def display_distance(meters: Any, preferences: dict) -> tuple[float | None, str | None]:
    """Return a labeled presentation value without changing the source value."""
    system = preferences.get("measurement_system")
    if system in ("statute_us", "statute_uk"):
        factor, unit = 1 / 1609.344, "mi"
    elif system == "metric":
        factor, unit = 1 / 1000, "km"
    else:
        return None, None
    if isinstance(meters, bool) or not isinstance(meters, (int, float)):
        return None, unit
    return round(meters * factor, 3), unit

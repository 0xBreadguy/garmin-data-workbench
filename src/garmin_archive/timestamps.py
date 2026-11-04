"""Decode source UTC instants and local wall-clock fields without profile guesses."""
import math
from datetime import UTC, datetime


def source_timestamp(value, *, utc: bool) -> str | None:
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

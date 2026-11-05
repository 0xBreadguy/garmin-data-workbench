"""Covered comparisons of two explicit, nonoverlapping metric periods."""
from __future__ import annotations

import math
import sqlite3

from .queries import MAX_TREND_DAYS, get_trend, parse_day
from .preferences import local_today


def validate_periods(start: str, end: str, baseline_start: str, baseline_end: str) -> None:
    first, last, before, after = map(parse_day, (start, end, baseline_start, baseline_end))
    if any(not 1 <= (b - a).days + 1 <= MAX_TREND_DAYS for a, b in ((first, last), (before, after))):
        raise ValueError("Each comparison period must be between 1 and 90 days, inclusive")
    if after >= first:
        raise ValueError("The baseline must end before the comparison period begins")


def compare_periods(db: sqlite3.Connection, metric: str, start: str, end: str,
                    baseline_start: str, baseline_end: str) -> dict:
    """Compare available-day means; retained failed values use existing trend masking."""
    validate_periods(start, end, baseline_start, baseline_end)
    baseline = get_trend(db, metric, baseline_start, baseline_end)
    period = get_trend(db, metric, start, end)
    means = []
    warnings = []
    today, _ = local_today(period["preferences"])
    for name, result in (("baseline", baseline), ("period", period)):
        values = [p["value"] for p in result["points"] if p["value"] is not None]
        # Divide before summing to avoid overflowing otherwise finite means.
        means.append(math.fsum(v / len(values) for v in values) if values else None)
        if len(values) != result["coverage"]["requested_days"]:
            warnings.append(name + "_incomplete_coverage")
        if result["to"] >= today.isoformat():
            warnings.append(name + "_includes_today_or_future")
    if baseline["coverage"]["requested_days"] != period["coverage"]["requested_days"]:
        warnings.append("unequal_period_lengths")
    old, new = means
    difference = percent = None
    percent_status = "unavailable"
    if old is not None and new is not None:
        difference = round(new - old, 2)
        # Percentages of scores, bounded scales and percentages imply a ratio
        # interpretation those units do not support.
        if period["unit"] in {"score", "Garmin stress", "Body Battery", "points", "%"}:
            percent_status = "not_applicable_to_scale"
        elif old == 0:
            percent_status = "zero_baseline"
        else:
            candidate = (new / old - 1) * 100
            percent_status = "available" if math.isfinite(candidate) else "out_of_range"
            percent = round(candidate, 2) if math.isfinite(candidate) else None
    return {"archive_provenance": period["archive_provenance"], "metric": metric, "unit": period["unit"],
            "source": period["source"], "baseline": baseline, "period": period,
            "change": {"status": "available" if difference is not None else "unavailable",
                       "mean_difference": difference, "mean_percent_change": percent,
                       "percent_change_status": percent_status}, "warnings": warnings,
            "basis": "Period minus baseline; each mean uses its own available-day denominator. "
                     "Changes use unrounded source values and are rounded to two decimals. "
                     "Incomplete coverage can bias comparisons; these are descriptive changes, not causes or personal baselines."}

"""Bounded sleep/recovery views composed from the existing shared queries.

No new metric interpretation, collection, archive writes or frontend aggregation.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import timedelta

from .comparisons import compare_periods
from .queries import get_trend, query_range
from .sleep import get_sleep

RECOVERY_METRICS = ("sleep_duration", "overnight_hrv", "resting_heart_rate", "sleep_score",
                    "body_battery_charged")
EXTRA_METRICS = ("overnight_hrv", "resting_heart_rate", "body_battery_charged")


@contextmanager
def _snapshot(db):
    owns = not db.in_transaction
    if owns:
        db.execute("BEGIN")
    try:
        yield
    finally:
        if owns:
            db.rollback()


def get_sleep_recovery(db, start: str = "", end: str = "") -> dict:
    """A coherent read snapshot, 1–90 inclusive days; default fourteen days."""
    with _snapshot(db):
        first, last, _, _ = query_range(db, start, end)
        if not start:
            first = last - timedelta(days=13)
        start, end = first.isoformat(), last.isoformat()
        sleep = get_sleep(db, start, end)
        return {"schema_version": 1, "view": "sleep_recovery", "from": start, "to": end,
                "archive_provenance": sleep["archive_provenance"], "sleep": sleep,
                "trends": {metric: get_trend(db, metric, start, end) for metric in EXTRA_METRICS}}


def compare_sleep_recovery(db, start: str, end: str, baseline_start: str, baseline_end: str) -> dict:
    """Use the canonical comparison and its independent coverage for every metric."""
    with _snapshot(db):
        metrics = {metric: compare_periods(db, metric, start, end, baseline_start, baseline_end)
                   for metric in RECOVERY_METRICS}
        # Views need summaries, not another copy of all the underlying observations.
        for result in metrics.values():
            for key in ("baseline", "period"):
                period = result[key]
                points = period.pop("points")
                stamps = sorted({p["fetched_at"] for p in points
                                 if p["value"] is not None and p.get("fetched_at")})
                period["freshness"] = {"oldest_available_fetch": stamps[0] if stamps else None,
                                       "newest_available_fetch": stamps[-1] if stamps else None}
        return {"schema_version": 1, "view": "sleep_recovery_comparison",
                "archive_provenance": metrics["sleep_duration"]["archive_provenance"],
                "metrics": metrics}

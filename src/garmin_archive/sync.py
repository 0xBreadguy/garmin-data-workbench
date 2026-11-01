"""Bounded, resumable Personal API synchronization."""

from __future__ import annotations

import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import requests
from garmin_personal_api.errors import HttpError

from .archive import Archive
from .fit import UnsupportedActivity, decode_activity

DATASETS: dict[str, Callable[[Any, date], Any]] = {
    "daily_summary": lambda client, day: client.get_daily_summaries(day, day),
    "sleep": lambda client, day: client.get_daily_sleep(day),
    "hrv": lambda client, day: client.get_daily_hrv(day),
    "heart_rate": lambda client, day: client.get_daily_heart_rate(day),
    "body_battery": lambda client, day: client.get_daily_body_battery(day, day),
}
PAGE_SIZE = 50
MAX_PAGES_PER_DAY = 500


class SyncStopped(RuntimeError):
    """A condition where making more requests would be unsafe or unhelpful."""


@dataclass
class SyncReport:
    checked: int = 0
    skipped: int = 0
    activities: int = 0
    decoded: int = 0
    unsupported: int = 0
    errors: list[str] = field(default_factory=list)
    stopped: bool = False


def _error_label(error: Exception) -> str:
    # Garmin response bodies can contain private data. Do not log exception text.
    if isinstance(error, HttpError):
        return f"HTTP {error.status_code}"
    return type(error).__name__


def _call(operation: Callable[[], Any], pause: float, sleep: Callable[[float], None]) -> Any:
    """Retry transient failures twice; stop immediately on auth or rate limits.

    Garmin's current Python client doesn't expose response headers on HttpError,
    so a 429 is surfaced immediately rather than guessing a Retry-After delay.
    """
    for attempt in range(3):
        if pause:
            sleep(pause)
        try:
            return operation()
        except HttpError as error:
            if error.status_code in (401, 403, 429):
                raise SyncStopped(_error_label(error)) from error
            if error.status_code < 500:
                raise
            if attempt == 2:
                raise SyncStopped(_error_label(error)) from error
        except (requests.RequestException, OSError) as error:
            if attempt == 2:
                raise SyncStopped(_error_label(error)) from error
        sleep(2**attempt)
    raise AssertionError("unreachable")


def _list_activities(client: Any, day: date, call: Callable[[Callable[[], Any]], Any]) -> list[dict[str, Any]]:
    activities: list[dict[str, Any]] = []
    seen: set[int] = set()
    offset = 0
    for _ in range(MAX_PAGES_PER_DAY):
        page = call(lambda offset=offset: client.search_activities(
            start=offset, limit=PAGE_SIZE, start_date=day, end_date=day
        ))
        if not isinstance(page, list):
            raise TypeError("Activity search returned an unexpected response")
        if not page:
            return activities
        count = 0
        for item in page:
            if not isinstance(item, dict):
                raise TypeError("Activity search returned an invalid item")
            activity_id = item.get("activityId")
            if isinstance(activity_id, bool) or not isinstance(activity_id, int) or activity_id <= 0:
                raise ValueError("Activity search returned an invalid activity ID")
            if activity_id not in seen:
                seen.add(activity_id)
                activities.append(item)
                count += 1
        if count == 0:
            raise ValueError("Activity pagination repeated a page")
        offset += len(page)
    raise ValueError("Activity pagination exceeded its safety limit")


def sync(
    archive: Archive,
    client: Any,
    start: date,
    end: date,
    *,
    refresh: bool = False,
    today: date | None = None,
    pause: float = 0.3,
    sleep: Callable[[float], None] = time.sleep,
) -> SyncReport:
    if start > end:
        raise ValueError("Start date must not be after end date")
    if pause < 0:
        raise ValueError("Pause must not be negative")
    today = today or date.today()
    recent = today - timedelta(days=7)
    report = SyncReport()
    call = lambda operation: _call(operation, pause, sleep)
    day = start
    while day <= end:
        day_text = day.isoformat()
        for dataset, fetch in DATASETS.items():
            if not refresh and day < recent and archive.state(dataset, day_text) in ("ok", "empty"):
                report.skipped += 1
                continue
            try:
                data = call(lambda fetch=fetch, day=day: fetch(client, day))
            except SyncStopped as error:
                archive.mark_error(dataset, day_text, str(error))
                report.errors.append(f"{dataset} {day_text}: {error}")
                report.stopped = True
                return report
            except (HttpError, ValueError, TypeError) as error:
                label = _error_label(error)
                archive.mark_error(dataset, day_text, label)
                report.errors.append(f"{dataset} {day_text}: {label}")
            else:
                archive.save_daily(dataset, day_text, data)
                report.checked += 1
        if not refresh and day < recent and archive.state("activities", day_text) in ("ok", "empty"):
            report.skipped += 1
        else:
            try:
                activities = _list_activities(client, day, call)
            except SyncStopped as error:
                archive.mark_error("activities", day_text, str(error))
                report.errors.append(f"activities {day_text}: {error}")
                report.stopped = True
                return report
            except (HttpError, ValueError, TypeError) as error:
                label = _error_label(error)
                archive.mark_error("activities", day_text, label)
                report.errors.append(f"activities {day_text}: {label}")
            else:
                archive.save_activities(day_text, activities)
                report.activities += len(activities)
        day += timedelta(days=1)

    for activity_id in archive.activities_needing_fit(start.isoformat(), end.isoformat()):
        row = archive.connection.execute(
            "SELECT original_zip, fit_status FROM activities WHERE activity_id=?", (activity_id,)
        ).fetchone()
        try:
            content = row["original_zip"]
            # A failed download/parse is retried from preserved bytes by default;
            # an explicit refresh lets the user request a new copy from Garmin.
            if content is None or (refresh and row["fit_status"] == "error"):
                content = call(lambda activity_id=activity_id: client.download_activity(activity_id))
                archive.save_original(activity_id, content)
            messages = decode_activity(content)
        except UnsupportedActivity:
            archive.set_fit_status(activity_id, "unsupported", "Original ZIP contains no FIT file")
            report.unsupported += 1
        except SyncStopped as error:
            archive.set_fit_status(activity_id, "error", str(error))
            report.errors.append(f"activity {activity_id}: {error}")
            report.stopped = True
            return report
        except sqlite3.Error:
            raise
        except Exception as error:  # noqa: BLE001 -- corrupt third-party FIT decoders may raise varied errors
            label = _error_label(error)
            archive.set_fit_status(activity_id, "error", label)
            report.errors.append(f"activity {activity_id}: {label}")
        else:
            archive.save_messages(activity_id, messages)
            report.decoded += 1
    return report

"""Local MCP data access and explicit schedule configuration."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .archive import default_data_dir
from .preferences import display_distance, local_today, profile_preferences
from .queries import get_day as query_day, get_trend as query_trend, health_response, open_archive
from .sleep import get_sleep as query_sleep
from .body_battery import get_body_battery as query_body_battery
from .guidance import agent_guide as read_agent_guide
from .schedule import configure_schedule, schedule_status

DATASETS = {"daily_summary", "sleep", "hrv", "heart_rate", "body_battery"}
MAX_HEALTH_BYTES = 64_000
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)


def create_server(data_dir: Path) -> FastMCP:
    server = FastMCP(
        "Garmin Data Workbench",
        instructions=("Local Garmin archive. Data tools are read-only; configure_sync changes the local schedule. "
                      "On first use, check setup_status. If the schedule is not configured, ask how often the user "
                      "wants Garmin data updated; call configure_sync only after they choose. "
                      "Recommend 6 hours with a 2-day lookback. Check archive_status for freshness and coverage. "
                      "Start with get_day for a day, get_trend for changes, and archive_status for sync health. "
                      "Present distances and other measurements using Garmin profile preferences when available; "
                      "respect an explicit user request for other units. Numerical tool values use their labeled "
                      "source units and must be converted before presentation. "
                      "Missing or empty data is not zero; report coverage and stale or failed syncs. "
                      "Responses may be sent to your AI provider. Read agent_guide for detailed sleep, chart and interpretation guidance. "
                      "A configured schedule is not verified recurring execution. " + read_agent_guide()),
    )

    @server.tool(annotations=READ_ONLY)
    def agent_guide() -> dict:
        """Read installed query, branded visualization and interpretation guidance."""
        return {"guide": read_agent_guide()}

    @server.tool(annotations=READ_ONLY)
    def setup_receipt() -> dict:
        """Read installation/coverage/schedule evidence; does not inspect keys or provider routines."""
        from .onboarding import setup_receipt as receipt
        return receipt(data_dir)

    @server.tool(annotations=READ_ONLY)
    def get_sleep(start: str = "", end: str = "") -> dict:
        """Get 1–90 inclusive dates of sleep stages, score, stress, naps, sleep need and source times.

        YYYY-MM-DD dates default to seven dates ending today (which may be incomplete).
        Missing/failed values remain null; local times never use the current profile zone.
        """
        with open_archive(data_dir) as db:
            return query_sleep(db, start, end)

    @server.tool(annotations=READ_ONLY)
    def get_body_battery(start: str = "", end: str = "") -> dict:
        """Get 1–90 inclusive dates of Body Battery charge/drain and observed min/max/first/last.

        Uses stored reports and source column descriptors; no raw readings or events.
        Defaults to seven dates ending today; last reading is not a live current value.
        """
        with open_archive(data_dir) as db:
            return query_body_battery(db, start, end)

    @server.tool(annotations=READ_ONLY)
    def setup_status() -> dict:
        """Check whether the local automatic sync schedule is configured; requires no Garmin access."""
        return schedule_status(data_dir=data_dir)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, openWorldHint=False))
    def configure_sync(
        every_hours: Annotated[int, Field(ge=1, le=168)],
        lookback_days: Annotated[int, Field(ge=1, le=31)] = 2,
    ) -> dict:
        """Install or change the local macOS sync schedule after the user chooses a frequency.

        every_hours is the interval between syncs. lookback_days is the recent
        window rechecked for late uploads. This starts no immediate sync and
        changes no Garmin data. Only call on explicit user instruction.
        """
        return configure_schedule(data_dir, every_hours, lookback_days)

    @server.tool(annotations=READ_ONLY)
    def get_day(day: str = "") -> dict:
        """Get one day at a glance: supported metrics, activities, and dataset coverage.

        day is YYYY-MM-DD, defaulting to today in Garmin's profile timezone
        or the host timezone if unavailable.
        Missing values are null. Raw responses can be requested separately
        with daily_health.
        """
        with open_archive(data_dir) as db:
            return query_day(db, day)

    @server.tool(annotations=READ_ONLY)
    def get_trend(metric: str, start: str = "", end: str = "") -> dict:
        """Get daily values and coverage over 1–90 days inclusive.

        metric is steps, distance, resting_heart_rate, sleep_duration, overnight_hrv,
        sleep_score, sleep_deep, sleep_light, sleep_rem, sleep_awake,
        sleep_unmeasurable, sleep_stress, nap_duration, sleep_need, sleep_need_baseline,
        body_battery_charged, body_battery_drained, body_battery_min, body_battery_max,
        body_battery_first, or body_battery_last. start and end are YYYY-MM-DD. End defaults to today in
        Garmin's profile timezone (or host timezone if unavailable); start
        defaults to six days before end.
        Means use only days with values, never missing days.
        """
        with open_archive(data_dir) as db:
            return query_trend(db, metric, start, end)

    @server.tool(annotations=READ_ONLY)
    def archive_status() -> dict:
        """Summarize sync coverage and failures, including the last catch-up run."""
        with open_archive(data_dir) as db:
            coverage = [dict(row) for row in db.execute(
                "SELECT dataset, status, COUNT(*) AS days, MIN(day) AS first_day, "
                "MAX(day) AS last_day, MAX(updated_at) AS last_attempt "
                "FROM sync_state GROUP BY dataset, status ORDER BY dataset, status"
            )]
            fit = [dict(row) for row in db.execute(
                "SELECT fit_status, COUNT(*) AS activities FROM activities GROUP BY fit_status"
            )]
            has_catchup = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='catchup_state'"
            ).fetchone()
            catchup = db.execute("SELECT * FROM catchup_state WHERE id=1").fetchone() if has_catchup else None
            prefs = profile_preferences(db)
            today, today_source = local_today(prefs)
            return {"source": "local archive", "local_today": today.isoformat(), "today_source": today_source,
                    "preferences": prefs,
                    "coverage": coverage, "activity_files": fit,
                    "catch_up": dict(catchup) if catchup else None}

    @server.tool(annotations=READ_ONLY)
    def list_activities(
        limit: Annotated[int, Field(ge=1, le=100)] = 20,
        offset: Annotated[int, Field(ge=0)] = 0,
    ) -> dict:
        """List activity summaries, newest first. Page with offset and limit."""
        with open_archive(data_dir) as db:
            prefs = profile_preferences(db)
            rows = [dict(row) for row in db.execute(
                "SELECT activity_id, day, json_extract(summary_json, '$.activityType.typeKey') AS type, "
                "json_extract(summary_json, '$.activityName') AS name, "
                "json_extract(summary_json, '$.distance') AS distance_m, "
                "json_extract(summary_json, '$.duration') AS duration_s, "
                "json_extract(summary_json, '$.averageHR') AS average_heart_rate_bpm, fit_status, updated_at "
                "FROM activities ORDER BY day DESC, activity_id DESC LIMIT ? OFFSET ?", (limit + 1, offset)
            )]
        for activity in rows:
            activity["display_distance"], activity["display_distance_unit"] = display_distance(activity["distance_m"], prefs)
        return {"source": "local archive", "preferences": prefs, "activities": rows[:limit],
                "units": {"distance_m": "m", "duration_s": "s", "average_heart_rate_bpm": "bpm"},
                "next_offset": offset + limit if len(rows) > limit else None}

    @server.tool(annotations=READ_ONLY)
    def daily_health(dataset: str, day: str) -> dict:
        """Read one stored daily response: daily_summary, sleep, hrv, heart_rate, or body_battery.

        day is YYYY-MM-DD. Large responses are rejected rather than silently truncated.
        """
        if dataset not in DATASETS:
            raise ValueError("Unknown dataset")
        try:
            if date.fromisoformat(day).isoformat() != day:
                raise ValueError
        except ValueError as error:
            raise ValueError("day must be YYYY-MM-DD") from error
        with open_archive(data_dir) as db:
            return health_response(db, dataset, day, max_bytes=MAX_HEALTH_BYTES)

    @server.tool(annotations=READ_ONLY)
    def activity_records(
        activity_id: Annotated[int, Field(gt=0)],
        limit: Annotated[int, Field(ge=1, le=500)] = 100,
        offset: Annotated[int, Field(ge=0)] = 0,
    ) -> dict:
        """Return a page of recorded FIT samples; excludes precise location and raw fields."""
        with open_archive(data_dir) as db:
            prefs = profile_preferences(db)
            activity = db.execute("SELECT day, fit_status, updated_at FROM activities WHERE activity_id=?",
                                  (activity_id,)).fetchone()
            if activity is None:
                raise ValueError("Activity not found")
            rows = [dict(row) for row in db.execute(
                "SELECT record_index, timestamp, heart_rate_bpm, power_w, cadence_rpm, distance_m, "
                "enhanced_speed_mps FROM activity_records WHERE activity_id=? "
                "ORDER BY record_index LIMIT ? OFFSET ?", (activity_id, limit + 1, offset)
            )]
        return {"source": "decoded original FIT", "preferences": prefs, "activity_id": activity_id, "day": activity["day"],
                "fit_status": activity["fit_status"], "activity_updated_at": activity["updated_at"],
                "units": {"heart_rate_bpm": "bpm", "power_w": "W", "cadence_rpm": "rpm",
                          "distance_m": "m", "enhanced_speed_mps": "m/s"},
                "records": rows[:limit], "next_offset": offset + limit if len(rows) > limit else None}

    return server


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the local Garmin archive over MCP stdio.")
    parser.add_argument("--data-dir", type=Path, default=default_data_dir())
    args = parser.parse_args()
    create_server(args.data_dir).run(transport="stdio")


if __name__ == "__main__":
    main()

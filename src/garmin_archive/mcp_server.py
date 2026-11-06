"""Local MCP data access and explicit schedule configuration."""

from __future__ import annotations

import argparse
import base64
import json
import sys
from datetime import date
from importlib import import_module
from importlib.util import find_spec
from pathlib import Path
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations, CallToolResult, ImageContent, TextContent
from .provenance import archive_provenance
from pydantic import Field

from .archive import default_data_dir
from .api_data import (api_catalog as query_catalog, source_data as query_source, source_series as query_series,
                       snapshot_coverage, without_coordinates)
from .sources import DAILY_SOURCES
from .preferences import display_distance, local_today, profile_preferences
from .queries import get_day as query_day, get_trend as query_trend, health_response, open_archive
from .sleep import get_sleep as query_sleep
from .body_battery import get_body_battery as query_body_battery
from .comparisons import compare_periods as query_comparison
from .workouts import get_workout_summary as query_workouts, list_activities as query_activities
from .recovery import get_sleep_recovery as query_recovery, compare_sleep_recovery as query_recovery_comparison
from .mcp_apps import APP_META, APP_MIME, RECOVERY_URI, recovery_app_html
from .guidance import agent_guide as read_agent_guide
from .schedule import configure_schedule, schedule_status

DATASETS = DAILY_SOURCES
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

    @server.resource(RECOVERY_URI, name="sleep_recovery_app", mime_type=APP_MIME, meta=APP_META)
    def sleep_recovery_app() -> str:
        """Self-contained interactive sleep/recovery UI. No archive access or network assets."""
        return recovery_app_html()

    @server.tool(annotations=READ_ONLY, meta={"ui": {"resourceUri": RECOVERY_URI}})
    def explore_sleep_recovery(start: str = "", end: str = "") -> CallToolResult:
        """Open an interactive sleep/recovery explorer inside an MCP Apps-capable chat.

        Linked sleep stages/estimated need, HRV, resting HR, score and daily Body Battery
        charge, night details and period comparison. 1–90 inclusive dates; default 14 days.
        Reads the archive only, never syncs. Synthetic archives remain labeled.
        The host displays the linked app separately from the model's text response.
        After success, briefly state the requested dates and provenance; let the app
        provide the detail. Missing browser/computer-use access is not evidence of
        display failure. Do not claim either visible success or failure without evidence.
        Use PNG/table fallback only for an explicit host error, known lack of MCP Apps,
        or a user-reported missing app; honor requests to keep delivery interactive.
        Do not open an external browser.
        """
        with open_archive(data_dir) as db:
            result = query_recovery(db, start, end)
        return CallToolResult(structuredContent=result,
                              content=[TextContent(type="text", text=json.dumps(result))])

    @server.tool(annotations=READ_ONLY, meta={"ui": {"visibility": ["app"]}})
    def compare_sleep_recovery(start: str, end: str, baseline_start: str, baseline_end: str) -> CallToolResult:
        """Compare five recovery metrics with shared units, missingness and covered means.

        Explicit inclusive periods, each 1–90 days; baseline must end before start.
        Read-only archive query; never refreshes Garmin data or changes scheduling.
        """
        with open_archive(data_dir) as db:
            result = query_recovery_comparison(db, start, end, baseline_start, baseline_end)
        return CallToolResult(structuredContent=result,
                              content=[TextContent(type="text", text=json.dumps(result))])

    @server.tool(annotations=READ_ONLY)
    def chart(metric: str, start: str = "", end: str = "", layout: str = "chat") -> CallToolResult:
        """Render a branded PNG and caption/coverage metadata over 1–90 inclusive dates.

        metric accepts sleep for the duration/stages/score overview, or any get_trend metric.
        layout is chat or wide. Synthetic provenance labels images automatically.
        No file paths, credentials, sync or archive writes. Display the returned image
        through the host image interface; if unavailable, state that and give a small table.
        """
        with open_archive(data_dir) as db:
            result = query_sleep(db, start, end) if metric == 'sleep' else query_trend(db, metric, start, end)
        try:
            from .charts import render_png
            png, metadata = render_png(result, layout=layout)
        except ImportError:
            metadata = {'error': {'code': 'dependency_unavailable',
                                  'message': 'Charts require the optional charts extra; no chart was produced. Use query data for a small table.'}}
            return CallToolResult(isError=True, structuredContent=metadata,
                                  content=[TextContent(type='text', text=json.dumps(metadata))])
        return CallToolResult(structuredContent=metadata, content=[
            ImageContent(type='image', data=base64.b64encode(png).decode('ascii'), mimeType='image/png'),
            TextContent(type='text', text=json.dumps(metadata))])

    @server.tool(annotations=READ_ONLY)
    def brand() -> dict:
        """Read shared chart colors/settings and retrievable logo asset URIs; no charts extra needed."""
        from .brand import get_brand
        settings = get_brand()
        settings['assets'] = {name: {'uri': 'garmin-brand://assets/' + name,
                                    'mime_type': 'image/png' if name.endswith('png') else 'image/svg+xml'}
                              for name in settings['assets']}
        return settings

    def read_brand_asset(name: str) -> bytes:
        from .brand import get_brand
        return Path(get_brand()['assets'][name]).read_bytes()

    @server.resource('garmin-brand://assets/icon_png', mime_type='image/png')
    def icon_png() -> bytes:
        return read_brand_asset('icon_png')

    @server.resource('garmin-brand://assets/logo_svg', mime_type='image/svg+xml')
    def logo_svg() -> bytes:
        return read_brand_asset('logo_svg')

    @server.resource('garmin-brand://assets/icon_svg', mime_type='image/svg+xml')
    def icon_svg() -> bytes:
        return read_brand_asset('icon_svg')

    @server.tool(annotations=READ_ONLY)
    def agent_guide() -> dict:
        """Read installed query, branded visualization and interpretation guidance."""
        return {"guide": read_agent_guide()}

    @server.tool(annotations=READ_ONLY)
    def api_catalog(dataset: str = "", pointer: str = "",
                    limit: Annotated[int, Field(ge=1, le=100)] = 100,
                    offset: Annotated[int, Field(ge=0)] = 0) -> dict:
        """Discover all 26 Personal API sources and their native field definitions, without an archive.

        Start with no arguments. Set dataset to browse its response schema.
        pointer is a JSON Pointer; use * for array items in this schema tool.
        Descriptions preserve Garmin's units, formats, enums and caveats.
        """
        return query_catalog(dataset, pointer, limit=limit, offset=offset)

    @server.tool(annotations=READ_ONLY)
    def source_data(dataset: str, day: str = "", activity_id: int = 0, pointer: str = "",
                    limit: Annotated[int, Field(ge=1, le=100)] = 100,
                    offset: Annotated[int, Field(ge=0)] = 0, include_location: bool = False) -> dict:
        """Page any native Personal API response, including samples, episodes and nested fields.

        Daily sources require day (YYYY-MM-DD). Current sources omit day;
        activity sources require activity_id. Use api_catalog to discover sources.
        pointer is a JSON Pointer with concrete array indices. Large children
        return pointers to expand. Strings page by characters, arrays by items,
        objects by keys. next_offset continues the same node. Coordinates require
        explicit include_location. Failed refreshes mask retained data.
        """
        with open_archive(data_dir) as db:
            return query_source(db, dataset, day, activity_id, pointer,
                                limit=limit, offset=offset, include_location=include_location)

    @server.tool(annotations=READ_ONLY)
    def source_series(dataset: str, pointer: str, start: str = "", end: str = "") -> dict:
        """Read any native scalar field across 1–90 inclusive request dates.

        Discover fields/units with api_catalog. pointer is a JSON Pointer.
        Defaults to seven dates ending today. Values preserve source types and
        sentinels; no unit conversion or daily aggregation is inferred. Use
        get_trend for interpreted metrics. Array indices reflect source order.
        """
        with open_archive(data_dir) as db:
            return query_series(db, dataset, pointer, start, end)

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
        Normally accompany a multi-day sleep overview with the chart tool (metric sleep);
        see agent_guide for exceptions and image delivery.
        """
        with open_archive(data_dir) as db:
            return query_sleep(db, start, end)

    @server.tool(annotations=READ_ONLY)
    def get_body_battery(start: str = "", end: str = "") -> dict:
        """Get 1–90 inclusive dates of Body Battery charge/drain and observed min/max/first/last.

        Uses stored reports and source column descriptors; no raw readings or events.
        Defaults to seven dates ending today; last reading is not a live current value.
        Normally chart multi-day comparisons; agent_guide defines presentation exceptions.
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

        metric is a named metric from get_day: steps, sleep_duration, sleep_score,
        sleep_need, body_battery_last, calories_total, hydration, stress_average,
        spo2_average, intensity_moderate and others. start and end are YYYY-MM-DD. End defaults to today in
        Garmin's profile timezone (or host timezone if unavailable); start
        defaults to six days before end.
        Means use only days with values, never missing days.
        Normally accompany a multi-day trend with the chart tool when available;
        see agent_guide for exceptions and image delivery.
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
            return {"archive_provenance": archive_provenance(db), "source": "local archive", "local_today": today.isoformat(), "today_source": today_source,
                    "preferences": prefs,
                    "source_snapshots": snapshot_coverage(db),
                    "coverage": coverage, "activity_files": fit,
                    "catch_up": dict(catchup) if catchup else None}

    @server.tool(annotations=READ_ONLY)
    def compare_periods(metric: str, start: str, end: str, baseline_start: str, baseline_end: str) -> dict:
        """Compare available-day metric means over two explicit periods of 1–90 inclusive dates each.

        Baseline must end before start. Changes are period minus baseline, in source
        units. Read warnings and each period's coverage/fetch times before interpreting.
        Percent changes are unavailable for scores/bounded scales or a zero baseline.
        """
        with open_archive(data_dir) as db:
            return query_comparison(db, metric, start, end, baseline_start, baseline_end)

    @server.tool(annotations=READ_ONLY)
    def get_workout_summary(start: str = "", end: str = "", activity_type: str = "") -> dict:
        """Get distance/duration totals and Monday-based weekly buckets over 1–90 inclusive dates.

        Defaults to seven dates ending today. activity_type is an exact native typeKey,
        not a sport family. Parents with stored children are excluded before filtering.
        Failed dates are masked; totals use available summaries and report field counts.
        Duration is the source summary duration; overlapping recordings remain separate.
        """
        with open_archive(data_dir) as db:
            return query_workouts(db, start, end, activity_type)

    @server.tool(annotations=READ_ONLY)
    def list_activities(
        limit: Annotated[int, Field(ge=1, le=100)] = 20,
        offset: Annotated[int, Field(ge=0)] = 0,
        start: str = "", end: str = "", activity_type: str = "",
    ) -> dict:
        """List activity summaries, newest first. Optional inclusive date bounds and exact typeKey.

        Page with offset and limit. Includes parent/child recordings; use
        get_workout_summary for totals. Failed refreshes mask numeric measurements.
        """
        with open_archive(data_dir) as db:
            return query_activities(db, start, end, activity_type, limit=limit, offset=offset)

    @server.tool(annotations=READ_ONLY)
    def daily_health(dataset: str, day: str) -> dict:
        """Read one stored daily response; discover datasets with api_catalog.

        day is YYYY-MM-DD. Large responses are rejected; use source_data to page
        them by field or array. Coordinates can occur in native responses.
        """
        if dataset not in DATASETS:
            raise ValueError("Unknown dataset")
        try:
            if date.fromisoformat(day).isoformat() != day:
                raise ValueError
        except ValueError as error:
            raise ValueError("day must be YYYY-MM-DD") from error
        with open_archive(data_dir) as db:
            result = health_response(db, dataset, day, max_bytes=MAX_HEALTH_BYTES)
            result["data"] = without_coordinates(result["data"])
            result["location_policy"] = "Coordinates omitted; use source_data with include_location for native fields."
            return result

    @server.tool(annotations=READ_ONLY)
    def activity_records(
        activity_id: Annotated[int, Field(gt=0)],
        limit: Annotated[int, Field(ge=1, le=500)] = 100,
        offset: Annotated[int, Field(ge=0)] = 0,
    ) -> dict:
        """Return a page of recorded FIT samples; excludes precise location and raw fields."""
        with open_archive(data_dir) as db:
            prefs = profile_preferences(db)
            provenance = archive_provenance(db)
            activity = db.execute("SELECT day, fit_status, updated_at FROM activities WHERE activity_id=?",
                                  (activity_id,)).fetchone()
            if activity is None:
                raise ValueError("Activity not found")
            rows = [dict(row) for row in db.execute(
                "SELECT record_index, timestamp, heart_rate_bpm, power_w, cadence_rpm, distance_m, "
                "enhanced_speed_mps FROM activity_records WHERE activity_id=? "
                "ORDER BY record_index LIMIT ? OFFSET ?", (activity_id, limit + 1, offset)
            )]
        return {"archive_provenance": provenance, "source": "decoded original FIT", "preferences": prefs, "activity_id": activity_id, "day": activity["day"],
                "fit_status": activity["fit_status"], "activity_updated_at": activity["updated_at"],
                "units": {"heart_rate_bpm": "bpm", "power_w": "W", "cadence_rpm": "rpm",
                          "distance_m": "m", "enhanced_speed_mps": "m/s"},
                "records": rows[:limit], "next_offset": offset + limit if len(rows) > limit else None}

    return server


def _prepare_windows_charts() -> None:
    # NumPy's Windows native loader can deadlock behind an active piped-stdin
    # reader. Load it before stdio starts, only when optional charts are installed.
    # https://github.com/numpy/numpy/issues/24290
    if sys.platform == 'win32' and find_spec('matplotlib') is not None:
        try:
            import_module('numpy')
        except ImportError:
            # Preserve ordinary archive queries; chart reports missing/broken
            # optional dependencies through its existing error contract.
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the local Garmin archive over MCP stdio.")
    parser.add_argument("--data-dir", type=Path, default=default_data_dir())
    args = parser.parse_args()
    _prepare_windows_charts()
    create_server(args.data_dir).run(transport="stdio")


if __name__ == "__main__":
    main()

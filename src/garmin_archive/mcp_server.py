"""Read-only, local MCP access to a previously synced archive."""

from __future__ import annotations

import argparse
import json
import sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Annotated, Iterator

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

from .archive import default_data_dir

DATASETS = {"daily_summary", "sleep", "hrv", "heart_rate", "body_battery"}
MAX_HEALTH_BYTES = 64_000
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)


def create_server(data_dir: Path) -> FastMCP:
    server = FastMCP(
        "Garmin Data Workbench",
        instructions=("Read-only local Garmin archive. Check archive_status for freshness and coverage. "
                      "Missing or empty data is not zero. Responses may be sent to your AI provider."),
    )
    database = (data_dir.expanduser() / "archive.sqlite3").resolve()

    @contextmanager
    def open_archive() -> Iterator[sqlite3.Connection]:
        # mode=ro neither creates nor migrates a database and lets a sync run separately.
        connection = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
        finally:
            connection.close()

    @server.tool(annotations=READ_ONLY)
    def archive_status() -> dict:
        """Summarize sync coverage and failures, including the last catch-up run."""
        with open_archive() as db:
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
            return {"source": "local archive", "coverage": coverage, "activity_files": fit,
                    "catch_up": dict(catchup) if catchup else None}

    @server.tool(annotations=READ_ONLY)
    def list_activities(
        limit: Annotated[int, Field(ge=1, le=100)] = 20,
        offset: Annotated[int, Field(ge=0)] = 0,
    ) -> dict:
        """List activity summaries, newest first. Page with offset and limit."""
        with open_archive() as db:
            rows = [dict(row) for row in db.execute(
                "SELECT activity_id, day, json_extract(summary_json, '$.activityType.typeKey') AS type, "
                "json_extract(summary_json, '$.activityName') AS name, fit_status, updated_at "
                "FROM activities ORDER BY day DESC, activity_id DESC LIMIT ? OFFSET ?", (limit + 1, offset)
            )]
        return {"source": "local archive", "activities": rows[:limit],
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
        with open_archive() as db:
            row = db.execute(
                "SELECT d.data_json, d.fetched_at, s.status, s.error, s.updated_at AS last_attempt "
                "FROM (SELECT 1) LEFT JOIN daily_data d ON d.dataset=? AND d.day=? "
                "LEFT JOIN sync_state s ON s.dataset=? AND s.day=?", (dataset, day, dataset, day)
            ).fetchone()
        raw = row["data_json"]
        if raw is not None and len(raw.encode("utf-8")) > MAX_HEALTH_BYTES:
            raise ValueError("Stored response is too large for MCP; inspect it locally with the health command")
        return {"source": "local archive", "dataset": dataset, "day": day,
                "status": row["status"] or "not_checked", "last_attempt": row["last_attempt"],
                "error": row["error"], "fetched_at": row["fetched_at"],
                "data": json.loads(raw) if raw is not None else None}

    @server.tool(annotations=READ_ONLY)
    def activity_records(
        activity_id: Annotated[int, Field(gt=0)],
        limit: Annotated[int, Field(ge=1, le=500)] = 100,
        offset: Annotated[int, Field(ge=0)] = 0,
    ) -> dict:
        """Return a page of recorded FIT samples; excludes precise location and raw fields."""
        with open_archive() as db:
            activity = db.execute("SELECT day, fit_status, updated_at FROM activities WHERE activity_id=?",
                                  (activity_id,)).fetchone()
            if activity is None:
                raise ValueError("Activity not found")
            rows = [dict(row) for row in db.execute(
                "SELECT record_index, timestamp, heart_rate_bpm, power_w, cadence_rpm, distance_m, "
                "enhanced_speed_mps FROM activity_records WHERE activity_id=? "
                "ORDER BY record_index LIMIT ? OFFSET ?", (activity_id, limit + 1, offset)
            )]
        return {"source": "decoded original FIT", "activity_id": activity_id, "day": activity["day"],
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

"""Exercise the stdio MCP server against a synthetic archive, without Garmin access."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from garmin_archive.archive import Archive
from test_archive import FakeClient
from garmin_archive.sync import sync
from datetime import date


class MCPTest(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_reads_archive_with_bounds_and_no_location(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Archive(Path(temp))
            sync(archive, FakeClient(), date(2026, 1, 1), date(2026, 1, 1),
                 today=date(2026, 1, 10), pause=0)
            archive.save_daily("daily_summary", "2026-01-01", {"data": [{"calendarDate": "2026-01-01",
                "movement": {"steps": {"value": 0, "distanceInMeters": 1609.344}}}]})
            archive.save_daily("sleep", "2026-01-01", {"calendarDate": "2026-01-01", "sleepTimeSeconds": 27000})
            archive.save_daily("hrv", "2026-01-01", {"hrvSummary": {"calendarDate": "2026-01-01", "lastNightAvg": 42}})
            archive.save_daily("heart_rate", "2026-01-01", {"calendarDate": "2026-01-01", "restingHeartRate": 55})
            archive.save_daily("daily_summary", "2026-01-02", {"data": [{"calendarDate": "2026-01-02",
                "movement": {"steps": {"value": 8000}}}]})
            archive.mark_error("daily_summary", "2026-01-02", "HTTP 429")
            archive.save_preferences("statute_us", "America/Los_Angeles")
            archive.close()
            params = StdioServerParameters(command=sys.executable,
                args=["-m", "garmin_archive.mcp_server", "--data-dir", temp])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as client:
                    initialized = await client.initialize()
                    self.assertIn("using Garmin profile preferences", initialized.instructions)
                    tools = await client.list_tools()
                    self.assertEqual({t.name for t in tools.tools},
                                     {"archive_status", "list_activities", "daily_health", "activity_records", "get_day", "get_trend", "setup_status", "configure_sync"})
                    self.assertTrue(all(t.annotations.readOnlyHint for t in tools.tools if t.name != 'configure_sync'))
                    self.assertFalse(next(t for t in tools.tools if t.name == 'configure_sync').annotations.readOnlyHint)
                    async def call(name, args):
                        result = await client.call_tool(name, args)
                        self.assertFalse(result.isError, result.content)
                        return result.structuredContent or json.loads(result.content[0].text)
                    first = await call("activity_records", {"activity_id": 42, "limit": 1})
                    self.assertEqual(first["records"][0]["heart_rate_bpm"], 123)
                    self.assertEqual(first["next_offset"], 1)
                    self.assertNotIn("data_json", first["records"][0])
                    self.assertNotIn("position_lat", str(first))
                    second = await call("activity_records", {"activity_id": 42, "offset": 1})
                    self.assertEqual(second["records"][0]["heart_rate_bpm"], 124)
                    self.assertIsNone(second["next_offset"])
                    missing = await call("daily_health", {"dataset": "sleep", "day": "2026-01-02"})
                    self.assertEqual(missing["status"], "not_checked")
                    self.assertIsNone(missing["data"])
                    empty = await call("daily_health", {"dataset": "body_battery", "day": "2026-01-01"})
                    self.assertEqual(empty["status"], "empty")
                    overview = await call("get_day", {"day": "2026-01-01"})
                    self.assertEqual(overview["preferences"]["measurement_system"], "statute_us")
                    self.assertEqual(overview["preferences"]["time_zone"], "America/Los_Angeles")
                    self.assertEqual(overview["today_source"], "Garmin profile")
                    self.assertEqual(overview["metrics"]["steps"]["value"], 0)
                    self.assertEqual(overview["metrics"]["distance"]["value"], 1609.344)
                    self.assertEqual(overview["metrics"]["distance"]["display_value"], 1.0)
                    self.assertEqual(overview["metrics"]["distance"]["display_unit"], "mi")
                    self.assertEqual(overview["metrics"]["sleep_duration"]["value"], 27000)
                    self.assertEqual(overview["metrics"]["overnight_hrv"]["value"], 42)
                    self.assertEqual(overview["activities"][0]["activity_id"], 42)
                    today = await call("get_day", {})
                    from datetime import datetime
                    from zoneinfo import ZoneInfo
                    self.assertEqual(today["day"], datetime.now(ZoneInfo("America/Los_Angeles")).date().isoformat())
                    default_trend = await call("get_trend", {"metric": "steps", "end": "2026-01-07"})
                    self.assertEqual((default_trend["from"], default_trend["to"]),
                                     ("2026-01-01", "2026-01-07"))
                    trend = await call("get_trend", {"metric": "steps", "start": "2026-01-01", "end": "2026-01-03"})
                    self.assertEqual([p["status"] for p in trend["points"]], ["ok", "error", "not_checked"])
                    self.assertEqual([p["value"] for p in trend["points"]], [0, None, None])
                    self.assertEqual(trend["coverage"]["days_with_value"], 1)
                    self.assertEqual(trend["mean_of_available_days"], 0)
                    distance = await call("get_trend", {"metric": "distance", "start": "2026-01-01", "end": "2026-01-01"})
                    self.assertEqual(distance["points"][0]["value"], 1609.344)
                    self.assertEqual(distance["display"]["points"][0]["value"], 1.0)
                    self.assertEqual(distance["display"]["unit"], "mi")
                    bad_range = await client.call_tool("get_trend", {"metric": "steps", "start": "2025-01-01", "end": "2026-01-01"})
                    self.assertTrue(bad_range.isError)
                    bad = await client.call_tool("activity_records", {"activity_id": 42, "limit": 501})
                    self.assertTrue(bad.isError)

    async def test_missing_archive_is_not_created(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "missing"
            params = StdioServerParameters(command=sys.executable,
                args=["-m", "garmin_archive.mcp_server", "--data-dir", str(target)])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as client:
                    await client.initialize()
                    result = await client.call_tool("archive_status", {})
                    self.assertTrue(result.isError)
            self.assertFalse(target.exists())

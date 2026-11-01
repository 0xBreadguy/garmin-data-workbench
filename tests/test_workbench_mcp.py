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
            archive.close()
            params = StdioServerParameters(command=sys.executable,
                args=["-m", "garmin_archive.mcp_server", "--data-dir", temp])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as client:
                    await client.initialize()
                    tools = await client.list_tools()
                    self.assertEqual({t.name for t in tools.tools},
                                     {"archive_status", "list_activities", "daily_health", "activity_records"})
                    self.assertTrue(all(t.annotations.readOnlyHint for t in tools.tools))
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
                    empty = await call("daily_health", {"dataset": "hrv", "day": "2026-01-01"})
                    self.assertEqual(empty["status"], "empty")
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

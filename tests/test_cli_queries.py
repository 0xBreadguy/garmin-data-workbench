"""Headless assistants can query bounded summaries without credentials or writes."""
from __future__ import annotations

import contextlib
import io
import importlib.util
import json
import sqlite3
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from garmin_archive import cli
from garmin_archive.archive import Archive
from garmin_archive.queries import open_archive


class CLIQueryTest(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.data_dir = self.root / "archive"
        archive = Archive(self.data_dir)
        archive.save_preferences("statute_us", "America/Los_Angeles")
        archive.save_daily("daily_summary", "2026-01-01", {"data": [{"calendarDate": "2026-01-01",
            "movement": {"steps": {"value": 0, "distanceInMeters": 1609.344}}, "position_lat": "PRIVATE"}]})
        archive.save_daily("sleep", "2026-01-01", {"sleepTimeSeconds": 27000})
        archive.save_daily("sleep", "2026-01-02", {"sleepTimeSeconds": 28000})
        archive.mark_error("sleep", "2026-01-02", "HTTP 429")
        archive.close()
        self.database = self.data_dir / "archive.sqlite3"
        self.initial_bytes = self.database.read_bytes()
        # Any attempt at network/key access is a test failure.
        for name in ("PersonalApiAuthenticator", "GarminPersonalApiClient", "resolve_api_key", "_sync"):
            mock = self.stack.enter_context(patch(f"garmin_archive.cli.{name}", side_effect=AssertionError("Query attempted sync/auth")))
            self.addCleanup(mock.assert_not_called)

    def run_query(self, *args, data_dir=None):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = cli.main(["--data-dir", str(data_dir or self.data_dir), *args])
        self.assertEqual(self.database.read_bytes(), self.initial_bytes)
        return code, output.getvalue(), errors.getvalue()

    def test_day_json_has_units_zero_missingness_preferences_and_no_raw_location(self):
        code, output, errors = self.run_query("day", "2026-01-01")
        self.assertEqual((code, errors), (0, ""))
        result = json.loads(output)
        self.assertEqual(result["day"], "2026-01-01")
        self.assertEqual(result["metrics"]["steps"]["value"], 0)
        self.assertEqual(result["metrics"]["distance"]["value"], 1609.344)
        self.assertEqual(result["metrics"]["distance"]["display_unit"], "mi")
        self.assertEqual(result["metrics"]["distance"]["display_value"], 1.0)
        self.assertEqual(result["metrics"]["resting_heart_rate"]["status"], "not_checked")
        self.assertIsNotNone(result["metrics"]["sleep_duration"]["fetched_at"])
        self.assertEqual(result["preferences"]["time_zone"], "America/Los_Angeles")
        self.assertNotIn("PRIVATE", output)
        self.assertNotIn("position_lat", output)

    def test_trend_masks_failed_refresh_and_reports_coverage(self):
        code, output, errors = self.run_query("trend", "sleep_duration", "--from", "2026-01-01", "--to", "2026-01-03")
        self.assertEqual((code, errors), (0, ""))
        result = json.loads(output)
        self.assertEqual([p["value"] for p in result["points"]], [27000, None, None])
        self.assertEqual([p["status"] for p in result["points"]], ["ok", "error", "not_checked"])
        self.assertEqual(result["unit"], "s")
        self.assertEqual(result["coverage"]["days_with_value"], 1)
        self.assertEqual(result["mean_of_available_days"], 27000)

    def test_default_dates_use_profile_and_default_trend_is_seven_days(self):
        with patch("garmin_archive.queries.local_today", return_value=(date(2026, 1, 7), "Garmin profile")):
            code, output, _ = self.run_query("day")
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(output)["day"], "2026-01-07")
            code, output, _ = self.run_query("trend", "distance")
            self.assertEqual(code, 0)
            result = json.loads(output)
        self.assertEqual((result["from"], result["to"]), ("2026-01-01", "2026-01-07"))
        self.assertEqual(result["display"]["points"][0]["value"], 1.0)
        self.assertEqual(result["display"]["unit"], "mi")

    def test_reversed_and_overlong_ranges_fail_without_traceback(self):
        for start, end in (("2026-01-02", "2026-01-01"), ("2026-01-01", "2026-04-01")):
            code, output, errors = self.run_query("trend", "steps", "--from", start, "--to", end)
            self.assertEqual((code, output), (2, ""))
            self.assertIn("between 1 and 90", errors)
            self.assertNotIn("Traceback", errors)

    def test_missing_archive_is_not_created(self):
        target = self.root / "missing"
        for args in (("day",), ("trend", "steps")):
            code, output, errors = self.run_query(*args, data_dir=target)
            self.assertEqual((code, output), (1, ""))
            self.assertIn("Cannot read existing archive", errors)
            self.assertFalse(target.exists())

    @unittest.skipUnless(importlib.util.find_spec("matplotlib"), "charts extra not installed")
    def test_chart_writes_png_without_overwriting_and_keeps_archive_unchanged(self):
        target = self.root / "sleep.png"
        args = ("chart", "sleep_duration", "--from", "2026-01-01", "--to", "2026-01-03", "--output", str(target))
        code, output, errors = self.run_query(*args)
        self.assertEqual((code, errors), (0, ""))
        self.assertTrue(target.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
        original = target.read_bytes()
        code, _, _ = self.run_query(*args)
        self.assertEqual(code, 1)
        self.assertEqual(target.read_bytes(), original)

    def test_shared_query_connection_rejects_writes(self):
        with open_archive(self.data_dir) as db:
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("DELETE FROM daily_data")

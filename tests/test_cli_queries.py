"""Headless assistants can query bounded summaries without credentials or writes."""
from __future__ import annotations

import contextlib
import csv
import io
import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
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
        archive.save_daily("hrv", "2026-01-01", {})
        archive.save_activities("2026-01-01", [
            {"activityId": activity_id, "activityName": "Example", "activityType": {"typeKey": "cycling"}}
            for activity_id in (42, 43, 44, 45)
        ])
        archive.save_original(42, b"synthetic original")
        archive.save_messages(42, {"record_mesgs": [
            {"timestamp": "2026-01-01T10:00:00+00:00", "heart_rate": 123, "position_lat": "PRIVATE"},
            {"timestamp": "2026-01-01T10:00:01+00:00", "heart_rate": 124},
        ]})
        archive.set_fit_status(44, "error", "Synthetic decoding failure")
        archive.set_fit_status(45, "unsupported")
        archive.close()
        self.database = self.data_dir / "archive.sqlite3"
        self.initial_bytes = self.database.read_bytes()
        # Any attempt at network/key access is a test failure.
        for name in ("Archive", "PersonalApiAuthenticator", "GarminPersonalApiClient", "resolve_api_key", "_sync"):
            mock = self.stack.enter_context(patch(f"garmin_archive.cli.{name}", side_effect=AssertionError("Query attempted sync/auth")))
            self.addCleanup(mock.assert_not_called)

    def run_query(self, *args, data_dir=None):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            try:
                code = cli.main(["--data-dir", str(data_dir or self.data_dir), *args])
            except SystemExit as error:
                code = error.code
        self.assertEqual(self.database.read_bytes(), self.initial_bytes)
        return code, output.getvalue(), errors.getvalue()

    def assert_error(self, result, exit_code, error_code):
        code, output, errors = result
        self.assertEqual((code, output), (exit_code, ""))
        payload = json.loads(errors)
        self.assertEqual(payload["error"]["code"], error_code)
        self.assertTrue(payload["error"]["message"])
        self.assertNotIn("Traceback", errors)
        self.assertNotIn("PRIVATE", errors)

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
            self.assert_error((code, output, errors), 2, "invalid_argument")

    def archive_commands(self):
        return (("day",), ("trend", "steps"),
                ("chart", "steps", "--output", str(self.root / "chart.png")), ("status",), ("activities",),
                ("health", "hrv", "2026-01-01"), ("records", "42"),
                ("export-original", "42", str(self.root / "export.zip")))

    def test_missing_archive_is_not_created(self):
        for directory_exists in (False, True):
            target = self.root / str(directory_exists)
            if directory_exists:
                target.mkdir()
            for args in self.archive_commands():
                with self.subTest(args=args, directory_exists=directory_exists):
                    self.assert_error(self.run_query(*args, data_dir=target), 1, "archive_unavailable")
                    self.assertFalse((target / "archive.sqlite3").exists())
                    self.assertEqual(target.exists(), directory_exists)
            self.assertFalse((self.root / "export.zip").exists())

    def test_status_activities_and_health_read_existing_data_as_json(self):
        code, output, errors = self.run_query("status")
        self.assertEqual((code, errors), (0, ""))
        result = json.loads(output)
        self.assertEqual(result["database"], str(self.database))
        self.assertEqual(result["errors"][0]["error"], "HTTP 429")
        self.assertEqual(result["fit_errors"], [{"activity_id": 44, "error": "Synthetic decoding failure"}])
        for offset, expected in ((0, [45, 44]), (2, [43, 42]), (4, [])):
            code, output, errors = self.run_query("activities", "--limit", "2", "--offset", str(offset))
            self.assertEqual((code, errors), (0, ""))
            self.assertEqual([item["activity_id"] for item in json.loads(output)], expected)
        for dataset, expected in (("sleep", {"sleepTimeSeconds": 27000}), ("hrv", {})):
            code, output, errors = self.run_query("health", dataset, "2026-01-01")
            self.assertEqual((code, errors), (0, ""))
            self.assertEqual(json.loads(output), expected)

    def test_records_preserve_json_csv_pagination_and_explicit_full_fields(self):
        code, output, errors = self.run_query("records", "42", "--limit", "1")
        self.assertEqual((code, errors), (0, ""))
        records = json.loads(output)
        self.assertEqual([r["heart_rate_bpm"] for r in records], [123])
        self.assertNotIn("PRIVATE", output)
        code, output, errors = self.run_query("records", "42", "--offset", "1", "--format", "csv")
        self.assertEqual((code, errors), (0, ""))
        self.assertEqual([r["heart_rate_bpm"] for r in csv.DictReader(io.StringIO(output))], ["124"])
        code, output, errors = self.run_query("records", "42", "--full", "--limit", "1")
        self.assertEqual((code, errors), (0, ""))
        self.assertEqual(json.loads(output)[0]["data"]["position_lat"], "PRIVATE")
        code, output, errors = self.run_query("records", "42", "--offset", "2")
        self.assertEqual((code, errors, json.loads(output)), (0, "", []))

    def test_not_found_is_distinct_from_unavailable_records(self):
        for args in (("health", "hrv", "2026-01-02"), ("records", "1"),
                     ("records", "1", "--format", "csv"),
                     ("export-original", "1", str(self.root / "export.zip")),
                     ("export-original", "43", str(self.root / "export.zip"))):
            with self.subTest(args=args):
                self.assert_error(self.run_query(*args), 3, "not_found")
        for activity_id in (43, 44, 45):
            with self.subTest(activity_id=activity_id):
                self.assert_error(self.run_query("records", str(activity_id)), 1, "records_unavailable")
        self.assertFalse((self.root / "export.zip").exists())

    def test_empty_archive_returns_success_for_empty_summaries_and_lists(self):
        target = self.root / "empty"
        Archive(target).close()
        before = (target / "archive.sqlite3").read_bytes()
        for args in (("day", "2026-01-01"), ("trend", "steps"), ("status",), ("activities",)):
            code, output, errors = self.run_query(*args, data_dir=target)
            self.assertEqual((code, errors), (0, ""))
            result = json.loads(output)
            if args[0] == "day":
                self.assertTrue(all(m["status"] == "not_checked" and m["value"] is None
                                    for m in result["metrics"].values()))
            elif args[0] == "trend":
                self.assertEqual(result["coverage"]["days_with_value"], 0)
            elif args[0] == "status":
                self.assertEqual((result["coverage"], result["errors"]), ([], []))
            else:
                self.assertEqual(result, [])
        self.assertEqual((target / "archive.sqlite3").read_bytes(), before)

    def test_uninitialized_and_corrupt_archives_are_not_repaired(self):
        for kind in ("uninitialized", "corrupt"):
            target = self.root / kind
            target.mkdir()
            database = target / "archive.sqlite3"
            if kind == "uninitialized":
                with sqlite3.connect(database) as db:
                    db.execute("CREATE TABLE old_schema (id INTEGER)")
            else:
                database.write_bytes(b"PRIVATE corrupt archive")
            before = database.read_bytes()
            for args in self.archive_commands():
                with self.subTest(kind=kind, args=args):
                    self.assert_error(self.run_query(*args, data_dir=target), 1, "archive_unavailable")
                    self.assertEqual(database.read_bytes(), before)
                    self.assertEqual(list(target.iterdir()), [database])

    def test_archive_errors_do_not_echo_private_exception_details(self):
        for error in (PermissionError("PRIVATE"), sqlite3.OperationalError("PRIVATE")):
            with patch("garmin_archive.cli.open_archive", side_effect=error):
                self.assert_error(self.run_query("status"), 1, "archive_unavailable")

    def test_invalid_stored_json_has_a_structured_error(self):
        target = self.root / "invalid-json"
        archive = Archive(target)
        archive.save_daily("hrv", "2026-01-01", {})
        archive.connection.execute("UPDATE daily_data SET data_json='PRIVATE invalid JSON'")
        archive.connection.commit()
        archive.close()
        self.assert_error(self.run_query("health", "hrv", "2026-01-01", data_dir=target), 1, "invalid_data")

    def test_invalid_arguments_are_json_without_opening_the_archive(self):
        target = self.root / "missing"
        for args in (("day", "bad-date"), ("trend", "hrv"), ("activities", "--limit", "0"),
                     ("records", "-1"), ("records", "42", "--format", "bad"),
                     ("records",), ("health", "bad-dataset", "2026-01-01"),
                     ("status", "--unknown"), ("unknown-command",), ("sync", "--from", "bad-date")):
            with self.subTest(args=args):
                self.assert_error(self.run_query(*args, data_dir=target), 2, "invalid_argument")
                self.assertFalse(target.exists())

    def test_path_reports_location_without_creating_an_archive(self):
        target = self.root / "missing"
        code, output, errors = self.run_query("path", data_dir=target)
        self.assertEqual((code, output, errors), (0, str(target / "archive.sqlite3") + "\n", ""))
        self.assertFalse(target.exists())

    def test_original_export_keeps_source_unchanged_and_never_overwrites(self):
        destination = self.root / "export.zip"
        code, output, errors = self.run_query("export-original", "42", str(destination))
        self.assertEqual((code, errors), (0, ""))
        self.assertIn(str(destination), output)
        self.assertEqual(destination.read_bytes(), b"synthetic original")
        if os.name != "nt":
            self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
        destination.write_bytes(b"keep this file")
        self.assert_error(self.run_query("export-original", "42", str(destination)), 1, "output_error")
        self.assertEqual(destination.read_bytes(), b"keep this file")

    def test_help_identifies_json_and_csv_formats(self):
        code, output, errors = self.run_query("--help")
        self.assertEqual((code, errors), (0, ""))
        for command in ("status", "activities", "records"):
            self.assertIn("JSON", output[output.index("    " + command):].split("\n    ", 1)[0])
            help_code, help_output, help_errors = self.run_query(command, "--help")
            self.assertEqual((help_code, help_errors), (0, ""))
            self.assertIn("JSON", help_output)
        code, output, errors = self.run_query("records", "--help")
        self.assertEqual((code, errors), (0, ""))
        self.assertIn("default: json", output)

    def test_module_entry_point_preserves_error_streams_and_exit_codes(self):
        # Run the module in a child process too: main() return values alone
        # don't establish shell-visible exit codes and stderr behavior.
        for args, expected_exit, expected_error in (
            (("health", "hrv", "2026-01-02"), 3, "not_found"),
            (("status", "--unknown"), 2, "invalid_argument"),
        ):
            result = subprocess.run(
                [sys.executable, "-m", "garmin_archive.cli", "--data-dir", str(self.data_dir), *args],
                capture_output=True, text=True, encoding="utf-8", timeout=30,
            )
            self.assert_error((result.returncode, result.stdout, result.stderr), expected_exit, expected_error)
        self.assertEqual(self.database.read_bytes(), self.initial_bytes)

    @unittest.skipUnless(importlib.util.find_spec("matplotlib"), "charts extra not installed")
    def test_chart_writes_png_without_overwriting_and_keeps_archive_unchanged(self):
        target = self.root / "sleep.png"
        args = ("chart", "sleep_duration", "--from", "2026-01-01", "--to", "2026-01-03", "--output", str(target))
        code, output, errors = self.run_query(*args)
        self.assertEqual((code, errors), (0, ""))
        self.assertTrue(target.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
        original = target.read_bytes()
        self.assert_error(self.run_query(*args), 1, "output_error")
        self.assertEqual(target.read_bytes(), original)

    def test_chart_reports_dependency_and_output_errors_without_private_details(self):
        target = self.root / "chart.png"
        args = ("chart", "steps", "--output", str(target))
        for error, exit_code, error_code in (
            (ImportError("PRIVATE"), 2, "dependency_unavailable"),
            (PermissionError("PRIVATE"), 1, "output_error"),
        ):
            with self.subTest(error=type(error).__name__):
                with patch("garmin_archive.charts.render_trend", side_effect=error):
                    self.assert_error(self.run_query(*args), exit_code, error_code)
                self.assertFalse(target.exists())

    def test_shared_query_connection_rejects_writes(self):
        with open_archive(self.data_dir) as db:
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("DELETE FROM daily_data")

"""Synthetic sleep semantics, clocks, bounded queries and CLI behavior."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from garmin_archive import cli
from garmin_archive.archive import Archive
from garmin_archive.queries import get_trend, health_response, open_archive
from garmin_archive.sleep import get_sleep


def payload(day="2026-01-01"):
    return {"calendarDate": day, "sleepTimeSeconds": 27000, "deepSleepSeconds": 5000,
            "remSleepSeconds": 6000, "lightSleepSeconds": 16000, "unmeasurableSleepSeconds": 0,
            "awakeSleepSeconds": 600, "napTimeSeconds": 0, "avgSleepStress": 20,
            "sleepScores": {"overall": {"value": 80}},
            "sleepStartTimestampGMT": "2026-01-01T05:20:00Z", "sleepEndTimestampGMT": "2026-01-01T13:00:00Z",
            "sleepStartTimestampLocal": "2025-12-31T21:20:00", "sleepEndTimestampLocal": "2026-01-01T05:00:00",
            "userNote": "PRIVATE SYNTHETIC NOTE", "samples": ["unneeded"] * 10000}


class SleepTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = Archive(self.root / "archive")
        self.addCleanup(self.archive.close)
        self.db = self.archive.connection
        self.archive.save_preferences("metric", "Asia/Tokyo")

    def test_structured_fields_keep_zero_source_units_and_historical_wall_time(self):
        self.archive.save_daily("sleep", "2026-01-01", payload())
        before = self.archive.path.read_bytes()
        result = get_sleep(self.db, "2026-01-01", "2026-01-01")
        night = result["nights"][0]
        self.assertEqual(night["values"]["sleep_duration"], 27000)
        self.assertEqual(night["values"]["nap_duration"], 0)
        self.assertEqual(night["values"]["sleep_awake"], 600)
        self.assertTrue(night["stages_complete"])
        self.assertEqual(night["timing"]["start_local"], "2025-12-31T21:20:00")
        self.assertEqual(night["timing"]["start_utc"], "2026-01-01T05:20:00+00:00")
        self.assertEqual(result["fields"]["sleep_deep"]["unit"], "s")
        self.assertEqual(result["coverage"]["fields"]["sleep_score"]["days_with_value"], 1)
        self.assertNotIn("PRIVATE", json.dumps(result))
        self.assertNotIn("samples", json.dumps(result))
        self.assertEqual(before, self.archive.path.read_bytes())

    def test_failed_empty_unchecked_mismatched_and_missing_responses_are_distinct(self):
        self.archive.save_daily("sleep", "2026-01-01", payload())
        self.archive.mark_error("sleep", "2026-01-01", "synthetic error")
        self.archive.save_daily("sleep", "2026-01-02", {})
        self.archive.save_daily("sleep", "2026-01-04", payload("2026-01-05"))
        self.archive.set_state("sleep", "2026-01-05", "ok")
        self.db.commit()
        result = get_sleep(self.db, "2026-01-01", "2026-01-05")
        self.assertEqual([n["status"] for n in result["nights"]],
                         ["error", "empty", "not_checked", "ok", "response_missing"])
        for night in result["nights"]:
            self.assertTrue(all(v is None for v in night["values"].values()))
            self.assertTrue(all(v is None for v in night["timing"].values()))
        self.assertIsNone(health_response(self.db, "sleep", "2026-01-01")["data"])
        self.assertTrue(health_response(self.db, "sleep", "2026-01-01")["retained_data_available"])

    def test_missing_or_invalid_stages_never_become_a_complete_breakdown(self):
        for i, (field, value) in enumerate((("deepSleepSeconds", None), ("lightSleepSeconds", -1),
                                          ("remSleepSeconds", True), ("sleepTimeSeconds", 36000)), 1):
            day = f"2026-01-{i:02}"
            data = payload(day)
            data[field] = value
            self.archive.save_daily("sleep", day, data)
        result = get_sleep(self.db, "2026-01-01", "2026-01-04")
        self.assertTrue(all(not n["stages_complete"] for n in result["nights"]))
        data = payload("2026-01-05")
        data.update({"sleepScores": {"overall": {"value": 101}}, "avgSleepStress": "20"})
        self.archive.save_daily("sleep", "2026-01-05", data)
        night = get_sleep(self.db, "2026-01-05", "2026-01-05")["nights"][0]
        self.assertIsNone(night["values"]["sleep_score"])
        self.assertIsNone(night["values"]["sleep_stress"])
        data["sleepScores"] = {"overall": {"value": 0, "qualifierKey": "INVALID"}}
        self.archive.save_daily("sleep", "2026-01-05", data)
        self.assertIsNone(get_sleep(self.db, "2026-01-05", "2026-01-05")["nights"][0]["values"]["sleep_score"])

    def test_timestamp_milliseconds_offsets_and_invalid_windows(self):
        data = payload()
        data.update({"sleepStartTimestampGMT": 1767254400000, "sleepEndTimestampGMT": 1767258000000,
                     "sleepStartTimestampLocal": "2026-01-01T00:00:00-08:00", "sleepEndTimestampLocal": 1767243600000})
        self.archive.save_daily("sleep", "2026-01-01", data)
        night = get_sleep(self.db, "2026-01-01", "2026-01-01")["nights"][0]
        self.assertEqual(night["timing"]["start_utc"], "2026-01-01T08:00:00+00:00")
        self.assertTrue(night["timing"]["start_local"].endswith("-08:00"))
        self.assertEqual(night["timing"]["end_local"], "2026-01-01T05:00:00")
        data.update({"sleepStartTimestampGMT": "2026-01-01T20:00:00Z", "sleepEndTimestampGMT": "2026-01-01T08:00:00Z"})
        self.archive.save_daily("sleep", "2026-01-01", data)
        night = get_sleep(self.db, "2026-01-01", "2026-01-01")["nights"][0]
        self.assertEqual(night["timing_status"], "invalid_window")
        self.assertTrue(all(value is None for value in night["timing"].values()))

    def test_default_window_boundaries_and_scalar_trends(self):
        result = get_sleep(self.db, end="2026-01-07")
        self.assertEqual((result["from"], result["to"], len(result["nights"])), ("2026-01-01", "2026-01-07", 7))
        for start, end in (("2026-01-02", "2026-01-01"), ("2026-01-01", "2026-04-01")):
            with self.assertRaises(ValueError):
                get_sleep(self.db, start, end)
        self.archive.save_daily("sleep", "2026-01-01", payload())
        self.assertEqual(get_trend(self.db, "sleep_score", "2026-01-01", "2026-01-01")["points"][0]["value"], 80)

    def test_query_snapshot_respects_caller_transaction_and_bounds_raw_fallback(self):
        self.assertFalse(self.db.in_transaction)
        get_sleep(self.db, "2026-01-01", "2026-01-01")
        self.assertFalse(self.db.in_transaction)
        self.db.execute("BEGIN")
        self.db.execute("INSERT INTO daily_data VALUES ('sleep','2026-01-01',?, '2026-01-02T00:00:00Z')", (json.dumps(payload()),))
        self.db.execute("INSERT INTO sync_state VALUES ('sleep','2026-01-01','ok',NULL,'2026-01-02T00:00:00Z')")
        result = get_sleep(self.db, "2026-01-01", "2026-01-01")
        self.assertEqual(result["nights"][0]["values"]["sleep_duration"], 27000)
        self.assertTrue(self.db.in_transaction)
        with self.assertRaises(ValueError):
            health_response(self.db, "sleep", "2026-01-01", max_bytes=64)
        self.db.rollback()
        self.assertEqual(get_sleep(self.db, "2026-01-01", "2026-01-01")["nights"][0]["status"], "not_checked")

    def test_cli_sleep_and_metadata_are_read_only_and_use_error_contract(self):
        self.archive.save_daily("sleep", "2026-01-01", payload())
        self.archive.mark_error("sleep", "2026-01-01", "failed")
        before = self.archive.path.read_bytes()
        for args in (("sleep", "--from", "2026-01-01", "--to", "2026-01-01"),
                     ("health", "sleep", "2026-01-01", "--metadata")):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli.main(["--data-dir", str(self.archive.data_dir), *args]), 0)
            data = json.loads(output.getvalue())
            self.assertIsNone(data["nights"][0]["values"]["sleep_duration"] if "nights" in data else data["data"])
        self.assertEqual(before, self.archive.path.read_bytes())
        errors = io.StringIO()
        missing = self.root / "missing"
        with contextlib.redirect_stderr(errors):
            self.assertEqual(cli.main(["--data-dir", str(missing), "sleep"]), 1)
        self.assertEqual(json.loads(errors.getvalue())["error"]["code"], "archive_unavailable")
        self.assertFalse(missing.exists())

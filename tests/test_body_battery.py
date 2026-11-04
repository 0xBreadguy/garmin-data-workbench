"""Synthetic descriptor parsing, observation semantics and adapter contracts."""
import contextlib
import io
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from garmin_archive import cli
from garmin_archive.archive import Archive
from garmin_archive.body_battery import body_battery_day, get_body_battery
from garmin_archive.queries import get_day, get_trend


def stamp(hour):
    return int(datetime(2026, 1, 1, hour, tzinfo=UTC).timestamp() * 1000)


def payload():
    return [{"date": "2026-01-01", "charged": 60, "drained": 50,
        "startTimestampGMT": "2026-01-01T00:00:00Z", "endTimestampGMT": "2026-01-01T23:59:59Z",
        "bodyBatteryValueDescriptorDTOList": [
            {"bodyBatteryValueDescriptorIndex": 2, "bodyBatteryValueDescriptorKey": "timestamp"},
            {"bodyBatteryValueDescriptorIndex": 0, "bodyBatteryValueDescriptorKey": "bodyBatteryStatus"},
            {"bodyBatteryValueDescriptorIndex": 1, "bodyBatteryValueDescriptorKey": "bodyBatteryLevel"}],
        "bodyBatteryValuesArray": [["draining", 20, stamp(23)], ["charging", 10, stamp(0)], ["charging", 90, stamp(7)]],
        "bodyBatteryActivityEvent": [{"shortFeedback": "PRIVATE SYNTHETIC EVENT"}]}]


class BodyBatteryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Archive(Path(self.temp.name) / "archive")
        self.addCleanup(self.archive.close)
        self.db = self.archive.connection
        self.archive.save_preferences("metric", "Asia/Tokyo")

    def save(self, data=None):
        self.archive.save_daily("body_battery", "2026-01-01", payload() if data is None else data)

    def test_descriptors_order_timestamps_and_exclude_raw_event_text(self):
        self.save()
        before = self.archive.path.read_bytes()
        result = get_body_battery(self.db, "2026-01-01", "2026-01-01")
        day = result["days"][0]
        self.assertEqual(day["values"], {"body_battery_charged": 60, "body_battery_drained": 50,
            "body_battery_min": 10, "body_battery_max": 90, "body_battery_first": 10, "body_battery_last": 20})
        self.assertEqual(day["valid_readings"], 3)
        self.assertEqual(day["last_observed_at"], "2026-01-01T23:00:00+00:00")
        self.assertEqual(result["coverage"]["fields"]["body_battery_min"]["days_with_value"], 1)
        self.assertNotIn("PRIVATE", json.dumps(result))
        self.assertNotIn("bodyBatteryActivityEvent", json.dumps(result))
        self.assertEqual(before, self.archive.path.read_bytes())
        trend = get_trend(self.db, "body_battery_last", "2026-01-01", "2026-01-02")
        self.assertEqual([p["value"] for p in trend["points"]], [20, None])
        self.assertEqual(trend["field"], "bodyBatteryValuesArray")
        self.assertEqual(trend["points"][0]["observed_at"], day["last_observed_at"])
        self.assertEqual(get_day(self.db, "2026-01-01")["metrics"]["body_battery_charged"]["value"], 60)

    def test_zero_partial_day_and_charge_amounts_are_not_clamped(self):
        data = payload()
        data[0].update({"charged": 150, "drained": 0, "bodyBatteryValuesArray": [["charging", 0, stamp(12)]]})
        self.save(data)
        day = body_battery_day(self.db, "2026-01-01")
        self.assertEqual(day["values"]["body_battery_charged"], 150)
        self.assertEqual(day["values"]["body_battery_last"], 0)
        self.assertEqual(day["valid_readings"], 1)
        self.assertEqual(day["first_observed_at"], day["last_observed_at"])

    def test_invalid_amount_types_and_overflow_are_missing_instead_of_coerced(self):
        for value in (True, '60', -1, .5, float('inf'), 10**400):
            with self.subTest(value=value):
                data = payload()
                data[0]['charged'] = value
                self.save(data)
                self.assertIsNone(body_battery_day(self.db, '2026-01-01')['values']['body_battery_charged'])

    def test_invalid_duplicate_and_conflicting_samples_are_explicit(self):
        data = payload()
        data[0]["bodyBatteryValuesArray"] += [
            ["charging", 90, stamp(7)], ["draining", 91, stamp(7)],
            ["bad", -1, stamp(5)], ["bad", True, stamp(6)], ["bad", 101, stamp(8)],
            ["bad", "40", stamp(9)], ["bad", 40, "2026-01-01T09:00:00"],
            ["bad", 40, stamp(0) - 1000], ["short"], {}]
        self.save(data)
        day = body_battery_day(self.db, "2026-01-01")
        self.assertEqual(day["duplicate_readings"], 1)
        self.assertEqual(day["conflicting_timestamps"], 1)
        self.assertEqual(day["invalid_readings"], 8)
        self.assertEqual(day["valid_readings"], 2)
        self.assertEqual(day["values"]["body_battery_max"], 20)

    def test_missing_ambiguous_and_unrecognized_descriptors_never_use_fixed_columns(self):
        for descriptors in (None, [], [{"bodyBatteryValueDescriptorKey": "timestamp", "bodyBatteryValueDescriptorIndex": True}],
                            [{"bodyBatteryValueDescriptorKey": {}, "bodyBatteryValueDescriptorIndex": 0}],
                            [{"bodyBatteryValueDescriptorKey": key, "bodyBatteryValueDescriptorIndex": 0}
                             for key in ("timestamp", "bodyBatteryLevel")]):
            with self.subTest(descriptors=descriptors):
                data = payload()
                data[0]["bodyBatteryValueDescriptorDTOList"] = descriptors
                self.save(data)
                day = body_battery_day(self.db, "2026-01-01")
                self.assertIsNone(day["values"]["body_battery_last"])
                self.assertEqual(day["values"]["body_battery_charged"], 60)
                self.assertEqual(day["readings_status"], "descriptors_unavailable_or_ambiguous")

    def test_explicit_offsets_and_missing_windows_do_not_guess_timestamp_units(self):
        data = payload()
        data[0].pop("startTimestampGMT")
        data[0].pop("endTimestampGMT")
        data[0]["bodyBatteryValuesArray"] = [["valid", 40, "2025-12-31T20:00:00-05:00"],
                                             ["seconds not milliseconds", 99, stamp(7) // 1000]]
        self.save(data)
        day = body_battery_day(self.db, "2026-01-01")
        self.assertEqual(day["valid_readings"], 1)
        self.assertEqual(day["invalid_readings"], 1)
        self.assertEqual(day["values"]["body_battery_max"], 40)
        self.assertEqual(day["last_observed_at"], "2026-01-01T01:00:00+00:00")

    def test_dates_failures_empty_missing_and_sample_limits(self):
        self.save()
        self.archive.mark_error("body_battery", "2026-01-01", "HTTP 429")
        self.archive.save_daily("body_battery", "2026-01-02", [])
        self.archive.save_daily("body_battery", "2026-01-04", payload())
        self.archive.save_daily("body_battery", "2026-01-05", [{"date": "2026-01-05"}, {"date": "2026-01-05"}])
        self.archive.set_state("body_battery", "2026-01-06", "ok")
        self.db.commit()
        result = get_body_battery(self.db, "2026-01-01", "2026-01-06")
        self.assertEqual([d["status"] for d in result["days"]], ["error", "empty", "not_checked", "ok", "ok", "response_missing"])
        self.assertTrue(all(v is None for d in result["days"] for v in d["values"].values()))
        self.assertEqual(result["days"][4]["report_status"], "ambiguous_date")
        self.save()
        with patch("garmin_archive.body_battery.MAX_READING_ROWS", 2):
            self.assertEqual(body_battery_day(self.db, "2026-01-01")["readings_status"], "too_many_readings")
        data = payload()
        data[0]["startTimestampGMT"] = "2026-01-02T00:00:00Z"
        self.save(data)
        day = body_battery_day(self.db, "2026-01-01")
        self.assertEqual(day["readings_status"], "invalid_window")
        self.assertIsNone(day["values"]["body_battery_last"])

    def test_cli_defaults_bounds_and_no_archive_creation(self):
        self.save()
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(cli.main(["--data-dir", str(self.archive.data_dir), "body-battery", "--to", "2026-01-07"]), 0)
        result = json.loads(output.getvalue())
        self.assertEqual((result["from"], len(result["days"])), ("2026-01-01", 7))
        self.assertFalse(self.db.in_transaction)
        with self.assertRaises(ValueError):
            get_body_battery(self.db, "2026-01-01", "2026-04-01")
        missing = Path(self.temp.name) / "missing"
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            self.assertEqual(cli.main(["--data-dir", str(missing), "body-battery"]), 1)
        self.assertEqual(json.loads(errors.getvalue())["error"]["code"], "archive_unavailable")
        self.assertFalse(missing.exists())

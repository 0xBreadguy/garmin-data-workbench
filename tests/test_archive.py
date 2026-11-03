"""Offline tests using a generated FIT file and a fake Garmin client."""

from __future__ import annotations

import contextlib
import io
import json
import os
import stat
import struct
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path
from unittest.mock import patch

from garmin_fit_sdk import CrcCalculator
from garmin_personal_api.errors import HttpError

from garmin_archive.archive import Archive
from garmin_archive.cli import main
from garmin_archive.fit import UnsupportedActivity, decode_activity
from garmin_archive.sync import sync


def synthetic_fit() -> bytes:
    def definition(local: int, global_message: int, fields: list[tuple[int, int, int]]) -> bytes:
        return (
            bytes([0x40 | local, 0, 0]) + struct.pack("<H", global_message)
            + bytes([len(fields)]) + b"".join(bytes(field) for field in fields)
        )

    body = definition(0, 0, [(0, 1, 0), (1, 2, 0x84), (2, 2, 0x84)])
    body += b"\x00" + struct.pack("<BHH", 4, 1, 1)
    body += definition(1, 20, [(253, 4, 0x86), (3, 1, 0x02)])
    body += b"\x01" + struct.pack("<IB", 1000000000, 123)
    body += b"\x01" + struct.pack("<IB", 1000000001, 124)
    header = struct.pack("<BBHI4s", 14, 0x20, 2200, len(body), b".FIT")
    header += struct.pack("<H", CrcCalculator.calculate_crc(header, 0, len(header)))
    content = header + body
    return content + struct.pack("<H", CrcCalculator.calculate_crc(content, 0, len(content)))


def activity_zip(content: bytes | None = None, *, name: str = "activity.fit") -> bytes:
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w") as archive:
        # Original-byte assertions must not depend on the wall clock.
        entry = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
        archive.writestr(entry, synthetic_fit() if content is None else content)
    return result.getvalue()


class FakeClient:
    def __init__(self) -> None:
        self.downloads = 0
        self.requests = 0

    def get_daily_summaries(self, start, end):
        self.requests += 1
        return {"data": [{"calendarDate": start.isoformat(), "steps": 5000}]}

    def get_daily_sleep(self, day):
        return {"calendarDate": day.isoformat(), "sleep": 7}

    def get_daily_hrv(self, day):
        return None

    def get_daily_heart_rate(self, day):
        return {"calendarDate": day.isoformat(), "heartRateValues": [[1, 60]]}

    def get_daily_body_battery(self, start, end):
        return []

    def search_activities(self, *, start, limit, start_date, end_date):
        if start:
            return []
        return [{"activityId": 42, "activityName": "Example", "activityType": {"typeKey": "cycling"}}]

    def download_activity(self, activity_id):
        self.downloads += 1
        return activity_zip()


class ArchiveTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "private"
        self.archive = Archive(self.path)
        self.addCleanup(self.archive.close)
        self.client = FakeClient()
        self.day = date(2026, 1, 1)
        self.today = date(2026, 1, 10)

    def run_sync(self, **kwargs):
        return sync(self.archive, self.client, self.day, self.day, today=self.today, pause=0, **kwargs)

    def test_sync_keeps_source_and_decodes_records_without_duplicates(self):
        result = self.run_sync()
        self.assertEqual((result.checked, result.activities, result.decoded), (5, 1, 1))
        self.assertFalse(result.errors)
        self.assertEqual(self.archive.state("hrv", "2026-01-01"), "empty")
        rows = self.archive.connection.execute(
            "SELECT timestamp, heart_rate_bpm FROM activity_records ORDER BY record_index"
        ).fetchall()
        self.assertEqual([row["heart_rate_bpm"] for row in rows], [123, 124])
        self.assertTrue(rows[0]["timestamp"].endswith("+00:00"))
        self.assertEqual(self.archive.connection.execute(
            "SELECT original_zip FROM activities WHERE activity_id=42"
        ).fetchone()[0], activity_zip())
        if os.name == "posix":
            self.assertEqual(stat.S_IMODE(self.archive.path.stat().st_mode), 0o600)

        second = self.run_sync()
        self.assertEqual(second.skipped, 6)
        self.assertEqual(self.client.downloads, 1)
        self.assertEqual(self.archive.connection.execute("SELECT COUNT(*) FROM activity_records").fetchone()[0], 2)

    def test_rate_limit_stops_and_preserves_failure_without_response_body(self):
        secret_body = "PRIVATE_RESPONSE_BODY"
        self.client.get_daily_summaries = lambda *a: (_ for _ in ()).throw(HttpError(
            status_code=429, method="GET", url="https://example.invalid", response_text=secret_body
        ))
        result = self.run_sync()
        self.assertTrue(result.stopped)
        self.assertEqual(self.archive.state("daily_summary", "2026-01-01"), "error")
        self.assertNotIn(secret_body, str(result.errors))
        self.assertEqual(self.client.downloads, 0)

    def test_failed_refresh_keeps_existing_daily_data(self):
        self.run_sync()
        self.client.get_daily_sleep = lambda *a: (_ for _ in ()).throw(ValueError("sensitive detail"))
        result = self.run_sync(refresh=True)
        self.assertTrue(result.errors)
        self.assertEqual(self.archive.state("sleep", "2026-01-01"), "error")
        self.assertEqual(json.loads(self.archive.connection.execute(
            "SELECT data_json FROM daily_data WHERE dataset='sleep'"
        ).fetchone()[0])["sleep"], 7)

    def test_corrupt_original_is_kept_for_recovery(self):
        self.client.download_activity = lambda activity_id: activity_zip(b"broken")
        result = self.run_sync()
        self.assertTrue(result.errors)
        row = self.archive.connection.execute(
            "SELECT original_zip, fit_status FROM activities WHERE activity_id=42"
        ).fetchone()
        self.assertIsNotNone(row["original_zip"])
        self.assertEqual(row["fit_status"], "error")

        # A normal retry reprocesses the preserved bytes without downloading.
        replacement = FakeClient()
        self.client.download_activity = replacement.download_activity
        self.run_sync()
        self.assertEqual(replacement.downloads, 0)
        # Explicit refresh may replace the broken copy and recover.
        recovered = self.run_sync(refresh=True)
        self.assertFalse(recovered.errors)
        self.assertEqual(replacement.downloads, 1)
        self.assertEqual(self.archive.connection.execute(
            "SELECT COUNT(*) FROM activity_records WHERE activity_id=42"
        ).fetchone()[0], 2)

    def test_repeating_activity_page_is_a_failure_not_a_successful_checkpoint(self):
        self.client.search_activities = lambda **kwargs: [{"activityId": 42}]
        result = self.run_sync()
        self.assertTrue(result.errors)
        self.assertEqual(self.archive.state("activities", "2026-01-01"), "error")
        self.assertEqual(self.archive.connection.execute("SELECT COUNT(*) FROM activities").fetchone()[0], 0)

    def test_records_csv_and_original_export(self):
        self.run_sync()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["--data-dir", str(self.path), "records", "42", "--format", "csv"])
        self.assertEqual(code, 0)
        self.assertIn("heart_rate_bpm", out.getvalue())
        self.assertIn(",123,", out.getvalue())
        destination = Path(self.temp.name) / "original.zip"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["--data-dir", str(self.path), "export-original", "42", str(destination)]), 0)
        self.assertEqual(destination.read_bytes(), activity_zip())
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--data-dir", str(self.path), "export-original", "42", str(destination)]), 1)

    def test_newer_schema_is_not_downgraded(self):
        self.archive.connection.execute("PRAGMA user_version=2")
        self.archive.connection.commit()
        with self.assertRaises(ValueError):
            Archive(self.path)
        self.assertEqual(self.archive.connection.execute("PRAGMA user_version").fetchone()[0], 2)


class FitTest(unittest.TestCase):
    def test_real_sdk_decodes_generated_fit(self):
        messages = decode_activity(activity_zip())
        self.assertEqual([row["heart_rate"] for row in messages["record_mesgs"]], [123, 124])

    def test_non_fit_original_is_supported_as_an_archive_only(self):
        with self.assertRaises(UnsupportedActivity):
            decode_activity(activity_zip(b"data", name="activity.gpx"))

    def test_corrupt_fit_is_rejected(self):
        with self.assertRaises(ValueError):
            decode_activity(activity_zip(b"not a FIT file"))

    def test_oversized_fit_is_rejected_before_read(self):
        with patch("garmin_archive.fit.MAX_FIT_BYTES", 1), self.assertRaises(ValueError):
            decode_activity(activity_zip())


if __name__ == "__main__":
    unittest.main()

"""Independent sensor expectations over generated FIT bytes and archived queries."""
import contextlib
import io
import json
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path

from garmin_archive.archive import Archive
from garmin_archive.cli import main
from garmin_archive.fit import decode_activity
from garmin_archive.sync import sync
from corpus import DAY, activity_fit
from test_archive import FakeClient, activity_zip


class FitCorpusTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.archive = Archive(self.path)
        self.addCleanup(self.archive.close)

    def collect(self, original):
        client = FakeClient()
        client.download_activity = lambda activity_id: original
        report = sync(self.archive, client, date.fromisoformat(DAY), date.fromisoformat(DAY),
                      today=date(2026, 1, 10), pause=0)
        self.assertFalse(report.errors)
        self.assertEqual(report.decoded, 1)
        row = self.archive.connection.execute(
            "SELECT original_zip FROM activities WHERE activity_id=42").fetchone()
        self.assertEqual(row[0], original)

    def records(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["--data-dir", str(self.path), "records", "42", *args]), 0)
        return json.loads(output.getvalue())

    def test_scaled_sensors_zeroes_and_invalids_survive_decode_storage_and_cli(self):
        original = activity_zip(activity_fit())
        self.collect(original)
        before = self.archive.path.read_bytes()
        rows = self.records()
        expected = {"heart_rate_bpm": 123, "power_w": 250, "cadence_rpm": 95,
                    "distance_m": 123.45, "enhanced_speed_mps": 4.5}
        self.assertEqual(len(rows), 3)
        for field, value in expected.items():
            self.assertEqual([row[field] for row in rows], [value, 0, None], field)
        self.assertEqual(rows[0]["timestamp"], "2026-01-01T00:00:00+00:00")
        self.assertNotIn("position_lat", json.dumps(rows))
        self.assertNotIn("position_long", json.dumps(rows))
        full = self.records("--full")
        self.assertEqual(full[0]["data"]["position_lat"], 1_073_741_824)
        self.assertEqual(full[0]["data"]["position_long"], -1_073_741_824)
        self.assertEqual(full[0]["data"]["temperature"], -5)
        self.assertAlmostEqual(full[0]["data"]["enhanced_altitude"], 123.4)
        self.assertEqual(full[1]["data"]["enhanced_altitude"], 0)
        self.assertNotIn("heart_rate", full[2]["data"])
        for kind, field, value in (("session_mesgs", "total_elapsed_time", 120),
                                   ("session_mesgs", "total_timer_time", 60),
                                   ("lap_mesgs", "total_distance", 123.45),
                                   ("event_mesgs", "event_type", "start")):
            stored = self.archive.connection.execute(
                "SELECT data_json FROM activity_messages WHERE message_type=?", (kind,)).fetchone()
            self.assertEqual(json.loads(stored[0])[field], value)
        self.assertEqual(self.archive.path.read_bytes(), before)

    def test_indoor_fit_omits_position_fields_but_retains_sensors(self):
        self.collect(activity_zip(activity_fit(gps=False)))
        full = self.records('--full')
        self.assertEqual(full[0]['power_w'], 250)
        self.assertNotIn('position_lat', json.dumps(full))
        self.assertNotIn('position_long', json.dumps(full))

    def test_multiple_fit_files_preserve_sessions_and_overlapping_recordings(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            for name, sport in (("legs/run.FIT", 1), ("legs/cycle.fit", 2)):
                entry = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                archive.writestr(entry, activity_fit(sport))
        original = buffer.getvalue()
        decoded = decode_activity(original)
        self.assertEqual([session["sport"] for session in decoded["session_mesgs"]], ["running", "cycling"])
        self.collect(original)
        records = self.records()
        self.assertEqual([r["record_index"] for r in records], list(range(6)))
        self.assertEqual([r["timestamp"] for r in records[:3]], [r["timestamp"] for r in records[3:]])
        self.assertEqual(self.archive.connection.execute(
            "SELECT COUNT(*) FROM activity_messages WHERE message_type='session_mesgs'").fetchone()[0], 2)

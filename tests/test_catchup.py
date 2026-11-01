"""Catch-up checkpoints cover missed runs and advance only after complete success."""
from __future__ import annotations

import argparse
import contextlib
import io
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from filelock import FileLock
from garmin_archive.archive import Archive
from garmin_archive.cli import _sync, _sync_locked
from garmin_archive.sync import SyncReport


class FakeAuth:
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def obtain_token(self, key): return argparse.Namespace(access_token="fake")


class FakeClient:
    def __init__(self, token): pass
    def __enter__(self): return self
    def __exit__(self, *args): pass


class CatchupTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Archive(Path(self.temp.name))
        self.addCleanup(self.archive.close)
        self.args = argparse.Namespace(catch_up=True, start=None, end=None, refresh=False, pause=0)
        self.ranges = []

    def invoke(self, start, end, report):
        def fake_sync(archive, client, start, end, **kwargs):
            self.ranges.append((start, end))
            return report
        with patch("garmin_archive.cli.PersonalApiAuthenticator", FakeAuth), \
             patch("garmin_archive.cli.GarminPersonalApiClient", FakeClient), \
             patch("garmin_archive.cli.resolve_api_key", return_value="fake"), \
             patch("garmin_archive.cli.sync", side_effect=fake_sync), \
             contextlib.redirect_stdout(io.StringIO()):
            return _sync_locked(self.archive, self.args, start, end)

    def test_offline_gap_and_failure_do_not_advance_checkpoint(self):
        self.assertEqual(self.invoke(date(2026, 1, 1), date(2026, 1, 7), SyncReport()), 0)
        self.assertEqual(self.invoke(date(2026, 1, 24), date(2026, 1, 30),
                                     SyncReport(errors=["error"])), 1)
        row = self.archive.connection.execute("SELECT * FROM catchup_state").fetchone()
        self.assertEqual(row["last_success_day"], "2026-01-07")
        self.assertEqual(row["last_result"], "error")
        self.assertEqual(self.invoke(date(2026, 1, 25), date(2026, 1, 31), SyncReport()), 0)
        self.assertEqual(self.ranges, [(date(2026, 1, 1), date(2026, 1, 7)),
                                      (date(2026, 1, 1), date(2026, 1, 30)),
                                      (date(2026, 1, 1), date(2026, 1, 31))])
        row = self.archive.connection.execute("SELECT * FROM catchup_state").fetchone()
        self.assertEqual(row["last_success_day"], "2026-01-31")

    def test_initial_failure_retains_requested_anchor(self):
        self.invoke(date(2025, 12, 1), date(2026, 1, 7), SyncReport(errors=["error"]))
        self.invoke(date(2026, 1, 24), date(2026, 1, 30), SyncReport())
        self.assertEqual(self.ranges[-1][0], date(2025, 12, 1))

    def test_recent_refresh_never_fetches_before_initial_anchor(self):
        self.invoke(date(2026, 1, 5), date(2026, 1, 7), SyncReport())
        self.invoke(date(2026, 1, 2), date(2026, 1, 8), SyncReport())
        self.assertEqual(self.ranges[-1], (date(2026, 1, 5), date(2026, 1, 8)))

    def test_configurable_lookback_still_covers_missed_days(self):
        self.args.lookback_days = 2
        self.invoke(date(2026, 1, 1), date(2026, 1, 7), SyncReport())
        self.invoke(date(2026, 1, 24), date(2026, 1, 30), SyncReport())
        self.assertEqual(self.ranges[-1], (date(2026, 1, 6), date(2026, 1, 30)))

    def test_auth_failure_preserves_anchor(self):
        with patch("garmin_archive.cli.PersonalApiAuthenticator", side_effect=RuntimeError("secret")), \
             contextlib.redirect_stderr(io.StringIO()) as errors:
            self.assertEqual(_sync_locked(self.archive, self.args, date(2026, 1, 1), date(2026, 1, 7)), 1)
        row = self.archive.connection.execute("SELECT * FROM catchup_state").fetchone()
        self.assertEqual((row["start_day"], row["last_success_day"], row["last_result"]),
                         ("2026-01-01", None, "error"))
        self.assertNotIn("secret", errors.getvalue())

    def test_clock_going_back_does_not_move_checkpoint(self):
        self.invoke(date(2026, 1, 1), date(2026, 1, 7), SyncReport())
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.invoke(date(2026, 1, 1), date(2026, 1, 6), SyncReport()), 1)
        self.assertEqual(self.archive.connection.execute(
            "SELECT last_success_day FROM catchup_state").fetchone()[0], "2026-01-07")

    def test_concurrent_sync_fails_before_authentication(self):
        with FileLock(str(self.archive.data_dir / "sync.lock"), timeout=0), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(_sync(self.archive, self.args), 1)
        self.assertIsNone(self.archive.connection.execute("SELECT * FROM catchup_state").fetchone())

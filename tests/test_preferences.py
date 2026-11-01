"""Garmin profile defaults are cached, bounded and used across timezone boundaries."""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import tempfile
import unittest
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import patch

from garmin_personal_api.errors import HttpError
from garmin_archive.archive import Archive
from garmin_archive.cli import _sync_locked
from garmin_archive.preferences import clean_profile, local_today, profile_preferences
from garmin_archive.sync import SyncReport
from test_catchup import FakeAuth, FakeClient


class PreferenceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Archive(Path(self.temp.name))
        self.addCleanup(self.archive.close)
        self.args = argparse.Namespace(catch_up=True, start=None, end=None, refresh=False, pause=0, lookback_days=2)

    def test_garmin_zone_controls_today_at_midnight(self):
        instant = datetime(2026, 1, 1, 1, tzinfo=UTC)
        value, source = local_today({'time_zone': 'America/Los_Angeles'}, instant)
        self.assertEqual((value, source), (date(2025, 12, 31), 'Garmin profile'))
        value, source = local_today({'time_zone': 'Asia/Tokyo'}, instant)
        self.assertEqual((value, source), (date(2026, 1, 1), 'Garmin profile'))

    def test_invalid_preferences_are_not_assumed(self):
        self.assertEqual(clean_profile({'measurementSystem': 'statute_us', 'timeZone': 'bad/timezone'}), ('statute_us', None))
        with self.assertRaises(ValueError): clean_profile({'measurementSystem': 5, 'timeZone': None})
        with self.assertRaises(ValueError): clean_profile([])
        self.assertEqual(profile_preferences(self.archive.connection)['source'], 'unavailable')

    def test_profile_refresh_is_used_for_catchup_dates(self):
        captured = []
        def fake_sync(archive, client, start, end, **kwargs):
            captured.append((start, end, kwargs['today']))
            return SyncReport()
        with patch('garmin_archive.cli.PersonalApiAuthenticator', FakeAuth), \
             patch('garmin_archive.cli.GarminPersonalApiClient', FakeClient), \
             patch('garmin_archive.cli.resolve_api_key', return_value='fake'), \
             patch('garmin_archive.cli.local_today', return_value=(date(2026, 1, 2), 'Garmin profile')), \
             patch('garmin_archive.cli.sync', side_effect=fake_sync), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(_sync_locked(self.archive, self.args, date(2025, 12, 26), date(2026, 1, 1), use_profile_default=True), 0)
        self.assertEqual(captured, [(date(2025, 12, 27), date(2026, 1, 2), date(2026, 1, 2))])
        state = self.archive.connection.execute('SELECT start_day, last_success_day FROM catchup_state').fetchone()
        self.assertEqual(tuple(state), ('2025-12-27', '2026-01-02'))
        prefs = profile_preferences(self.archive.connection)
        self.assertEqual((prefs['measurement_system'], prefs['time_zone']), ('statute_us', 'America/Los_Angeles'))

    def test_rate_limit_during_profile_stops_before_any_health_requests(self):
        class RateLimited(FakeClient):
            def get_user_profile_settings(self):
                raise HttpError(status_code=429, method='GET', url='https://example.invalid', response_text='PRIVATE')
        with patch('garmin_archive.cli.PersonalApiAuthenticator', FakeAuth), \
             patch('garmin_archive.cli.GarminPersonalApiClient', RateLimited), \
             patch('garmin_archive.cli.resolve_api_key', return_value='fake'), \
             patch('garmin_archive.cli.sync') as sync, \
             contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(_sync_locked(self.archive, self.args, date(2026, 1, 1), date(2026, 1, 7)), 1)
        sync.assert_not_called()
        self.assertNotIn('PRIVATE', err.getvalue())
        self.assertEqual(self.archive.connection.execute('SELECT last_result FROM catchup_state').fetchone()[0], 'error')

    def test_nonfatal_profile_failure_keeps_cached_settings(self):
        self.archive.save_preferences('metric', 'Europe/London')
        class MissingProfile(FakeClient):
            def get_user_profile_settings(self):
                raise HttpError(status_code=404, method='GET', url='https://example.invalid', response_text='PRIVATE')
        with patch('garmin_archive.cli.PersonalApiAuthenticator', FakeAuth), \
             patch('garmin_archive.cli.GarminPersonalApiClient', MissingProfile), \
             patch('garmin_archive.cli.resolve_api_key', return_value='fake'), \
             patch('garmin_archive.cli.sync', return_value=SyncReport()), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(_sync_locked(self.archive, self.args, date(2026, 1, 1), date(2026, 1, 7)), 0)
        self.assertEqual(profile_preferences(self.archive.connection)['measurement_system'], 'metric')
        report = json.loads(out.getvalue())
        self.assertIn('cached settings', report['profile_warning'])
        self.assertNotIn('PRIVATE', out.getvalue())

"""Agent summaries should never turn missing or mismatched data into measurements."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from garmin_archive.archive import Archive
from garmin_archive.queries import day_overview, metric_trend


class QueryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Archive(Path(self.temp.name))
        self.addCleanup(self.archive.close)
        self.db = self.archive.connection

    def test_metric_ranges_report_missing_empty_failed_and_mismatched(self):
        self.archive.save_daily('daily_summary', '2026-01-01', {'data': [{'calendarDate': '2026-01-01', 'movement': {'steps': {'value': 100}}}]})
        self.archive.save_daily('daily_summary', '2026-01-02', {'data': []})
        self.archive.save_daily('daily_summary', '2026-01-03', {'data': [{'calendarDate': '2026-01-04', 'movement': {'steps': {'value': 500}}}]})
        self.archive.mark_error('daily_summary', '2026-01-04', 'HTTP 429')
        result = metric_trend(self.db, 'steps', '2026-01-01', '2026-01-05')
        self.assertEqual([p['status'] for p in result['points']],
                         ['ok', 'empty', 'metric_not_returned', 'error', 'not_checked'])
        self.assertEqual(result['coverage']['days_with_value'], 1)
        self.assertEqual(result['mean_of_available_days'], 100)
        self.assertEqual(result['unit'], 'steps')

    def test_ambiguous_or_invalid_values_are_not_measurements(self):
        for day, items in [
            ('2026-01-01', [{'calendarDate': '2026-01-01', 'movement': {'steps': {'value': 1}}},
                            {'calendarDate': '2026-01-01', 'movement': {'steps': {'value': 2}}}]),
            ('2026-01-02', [{'calendarDate': '2026-01-02', 'movement': {'steps': {'value': True}}}]),
            ('2026-01-03', [{'calendarDate': '2026-01-03', 'movement': {'steps': {'value': -1}}}]),
        ]:
            self.archive.save_daily('daily_summary', day, {'data': items})
        result = metric_trend(self.db, 'steps', '2026-01-01', '2026-01-03')
        self.assertTrue(all(p['value'] is None and p['status'] == 'metric_not_returned' for p in result['points']))
        self.assertIsNone(result['mean_of_available_days'])

    def test_hrv_date_mismatch_is_not_used(self):
        self.archive.save_daily('hrv', '2026-01-01', {'hrvSummary': {'calendarDate': '2026-01-02', 'lastNightAvg': 42}})
        overview = day_overview(self.db, '2026-01-01')
        self.assertIsNone(overview['metrics']['overnight_hrv']['value'])
        self.assertEqual(overview['metrics']['overnight_hrv']['status'], 'metric_not_returned')

    def test_single_day_scalars_validate_type_and_date(self):
        self.archive.save_daily('heart_rate', '2026-01-01', {'calendarDate': '2026-01-01', 'restingHeartRate': True})
        self.archive.save_daily('heart_rate', '2026-01-02', {'calendarDate': '2026-01-03', 'restingHeartRate': 55})
        self.archive.save_daily('heart_rate', '2026-01-03', {'calendarDate': '2026-01-03', 'restingHeartRate': 0})
        result = metric_trend(self.db, 'resting_heart_rate', '2026-01-01', '2026-01-03')
        self.assertEqual([p['value'] for p in result['points']], [None, None, 0])
        self.assertEqual([p['status'] for p in result['points']],
                         ['metric_not_returned', 'metric_not_returned', 'ok'])

    def test_validation_rejects_reversed_and_oversized_ranges(self):
        for start, end in [('2026-01-02', '2026-01-01'), ('2026-01-01', '2026-04-01'), ('20260101', '2026-01-01')]:
            with self.assertRaises(ValueError):
                metric_trend(self.db, 'steps', start, end)
        with self.assertRaises(ValueError):
            metric_trend(self.db, 'unknown', '2026-01-01', '2026-01-01')

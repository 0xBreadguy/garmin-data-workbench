"""Read-only composed recovery queries and real MCP Apps resource transport."""
import json
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from garmin_archive.archive import Archive
from garmin_archive.comparisons import compare_periods
from garmin_archive.mcp_apps import APP_META, APP_MIME, RECOVERY_URI, recovery_app_html
from garmin_archive.mcp_server import create_server
from garmin_archive.queries import get_trend, open_archive
from garmin_archive.recovery import RECOVERY_METRICS, compare_sleep_recovery, get_sleep_recovery
from garmin_archive.sleep import get_sleep


def seed(root):
    archive = Archive(root)
    archive.mark_synthetic('recovery-test', 42, '2026-02-01T00:00:00+00:00')
    for day, duration in [('2026-01-01', 27000), ('2026-01-02', 0), ('2026-01-03', 28800)]:
        archive.save_daily('sleep', day, {'calendarDate': day, 'sleepTimeSeconds': duration,
            'deepSleepSeconds': 0, 'lightSleepSeconds': duration, 'remSleepSeconds': 0,
            'unmeasurableSleepSeconds': 0, 'awakeSleepSeconds': 1200,
            'sleepScores': {'overall': {'value': 0}}, 'sleepNeed': {'actual': 480},
            'nextSleepNeed': {'calendarDate': '2026-01-04', 'actual': 500, 'baseline': 480},
            'sleepStartTimestampLocal': '2026-01-01T22:30:00',
            'userNote': 'PRIVATE SENTINEL NOT FOR UI', 'samples': ['SAMPLE SENTINEL']})
        archive.save_daily('hrv', day, {'hrvSummary': {'calendarDate': day, 'lastNightAvg': 55}})
        archive.save_daily('heart_rate', day, {'restingHeartRate': 50})
    archive.mark_error('hrv', '2026-01-02', 'synthetic failure')
    archive.mark_error('sleep', '2026-01-03', 'synthetic failure')
    archive.close()


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        seed(self.root)

    def test_shared_results_units_independent_coverage_and_zero(self):
        before = (self.root / 'archive.sqlite3').read_bytes()
        with open_archive(self.root) as db:
            result = get_sleep_recovery(db, '2026-01-01', '2026-01-04')
            self.assertEqual(result['sleep'], get_sleep(db, '2026-01-01', '2026-01-04'))
            self.assertEqual(result['trends']['overnight_hrv'], get_trend(db, 'overnight_hrv', '2026-01-01', '2026-01-04'))
            self.assertFalse(db.in_transaction)
        self.assertTrue(result['archive_provenance']['synthetic'])
        nights = result['sleep']['nights']
        self.assertEqual(nights[1]['values']['sleep_duration'], 0)
        self.assertEqual(nights[1]['values']['sleep_score'], 0)
        self.assertIsNone(nights[2]['values']['sleep_duration'])
        self.assertIsNone(result['trends']['overnight_hrv']['points'][1]['value'])
        self.assertEqual(result['trends']['overnight_hrv']['points'][1]['status'], 'error')
        self.assertEqual(result['sleep']['fields']['sleep_need']['unit'], 'min')
        self.assertEqual(nights[0]['next_sleep_need']['day'], '2026-01-04')
        self.assertEqual(nights[0]['timing']['start_local'], '2026-01-01T22:30:00')
        self.assertNotIn('SENTINEL', json.dumps(result))
        self.assertEqual(before, (self.root / 'archive.sqlite3').read_bytes())

    def test_one_snapshot_and_existing_transaction_preserved(self):
        with open_archive(self.root) as db:
            original = get_trend
            def checked(*args, **kwargs):
                self.assertTrue(db.in_transaction)
                return original(*args, **kwargs)
            db.execute('BEGIN')
            with patch('garmin_archive.recovery.get_trend', side_effect=checked):
                get_sleep_recovery(db, '2026-01-01', '2026-01-04')
            self.assertTrue(db.in_transaction)
            db.rollback()
            with self.assertRaises(ValueError):
                get_sleep_recovery(db, '2026-02-02', '2026-01-01')
            self.assertFalse(db.in_transaction)

    def test_bounds_defaults_and_empty_period(self):
        with open_archive(self.root) as db:
            result = get_sleep_recovery(db, end='2026-01-14')
            self.assertEqual((result['from'], result['to']), ('2026-01-01', '2026-01-14'))
            result = get_sleep_recovery(db, '2025-01-01', '2025-03-31')
            self.assertEqual(len(result['sleep']['nights']), 90)
            self.assertEqual(result['sleep']['coverage']['fields']['sleep_duration']['days_with_value'], 0)
            self.assertLess(len(json.dumps(result)), 700_000)
            with self.assertRaises(ValueError):
                get_sleep_recovery(db, '2025-01-01', '2025-04-01')

    def test_comparison_parity_and_unavailable_metrics(self):
        with open_archive(self.root) as db:
            result = compare_sleep_recovery(db, '2026-01-02', '2026-01-04', '2026-01-01', '2026-01-01')
            for metric in RECOVERY_METRICS:
                expected = compare_periods(db, metric, '2026-01-02', '2026-01-04', '2026-01-01', '2026-01-01')
                actual = result['metrics'][metric]
                self.assertEqual(actual['change'], expected['change'])
                self.assertEqual(actual['warnings'], expected['warnings'])
                for period in ('baseline', 'period'):
                    self.assertEqual(actual[period]['coverage'], expected[period]['coverage'])
                    self.assertEqual(actual[period]['mean_of_available_days'], expected[period]['mean_of_available_days'])
                    self.assertNotIn('points', actual[period])
            self.assertIsNone(result['metrics']['body_battery_charged']['change']['mean_difference'])
            self.assertEqual(result['metrics']['sleep_duration']['change']['mean_difference'], -27000)
            self.assertIn('unequal_period_lengths', result['metrics']['sleep_duration']['warnings'])
            for arguments in [('2026-01-01','2026-01-04','2026-01-01','2026-01-02'),
                              ('2026-01-01','2026-04-01','2025-12-01','2025-12-01')]:
                with self.assertRaises(ValueError):
                    compare_sleep_recovery(db, *arguments)

    def test_resource_is_static_self_contained_and_packaged(self):
        html = recovery_app_html()
        self.assertTrue(html.lower().startswith('<!doctype html>'))
        self.assertIn('ui/initialize', html)
        self.assertIn('ui/notifications/tool-result', html)
        self.assertIn('compare_sleep_recovery', html)
        self.assertNotIn('/*__', html)
        self.assertNotIn('<script src=', html)
        self.assertNotIn('SENTINEL', html)
        self.assertLess(len(html.encode()), 500_000)
        self.assertEqual(APP_META['ui']['csp']['connectDomains'], [])
        self.assertEqual(APP_META['ui']['csp']['resourceDomains'], [])


class RecoveryTransportTest(unittest.IsolatedAsyncioTestCase):
    async def test_stdio_tools_resource_metadata_and_query_without_writes(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root); seed(path)
            before = (path / 'archive.sqlite3').read_bytes()
            files = sorted(p.name for p in path.iterdir())
            params = StdioServerParameters(command=sys.executable,
                args=['-m','garmin_archive.mcp_server','--data-dir',root])
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30)) as client:
                    await client.initialize()
                    tools = {t.name: t for t in (await client.list_tools()).tools}
                    self.assertEqual(tools['explore_sleep_recovery'].meta['ui']['resourceUri'], RECOVERY_URI)
                    self.assertTrue(tools['explore_sleep_recovery'].annotations.readOnlyHint)
                    self.assertEqual(tools['compare_sleep_recovery'].meta['ui']['visibility'], ['app'])
                    resource = (await client.read_resource(RECOVERY_URI)).contents[0]
                    self.assertEqual(resource.mimeType, APP_MIME)
                    self.assertEqual(resource.meta, APP_META)
                    self.assertEqual(resource.text, recovery_app_html())
                    result = await client.call_tool('explore_sleep_recovery', {'start':'2026-01-01','end':'2026-01-04'})
                    self.assertFalse(result.isError)
                    self.assertEqual(result.structuredContent['schema_version'], 1)
                    self.assertTrue(result.content)  # Non-UI clients retain meaningful JSON.
                    comparison = await client.call_tool('compare_sleep_recovery', {'start':'2026-01-02','end':'2026-01-04','baseline_start':'2026-01-01','baseline_end':'2026-01-01'})
                    self.assertFalse(comparison.isError)
                    self.assertEqual(comparison.structuredContent['metrics']['sleep_duration']['change']['mean_difference'], -27000)
                    invalid = await client.call_tool('explore_sleep_recovery', {'start':'2026-01-01','end':'2026-04-01'})
                    self.assertTrue(invalid.isError)
            self.assertEqual((path / 'archive.sqlite3').read_bytes(), before)
            self.assertEqual(sorted(p.name for p in path.iterdir()), files)

    async def test_ui_resource_needs_no_archive(self):
        with tempfile.TemporaryDirectory() as root:
            missing = Path(root) / 'does-not-exist'
            result = list(await create_server(missing).read_resource(RECOVERY_URI))
            self.assertEqual(result[0].mime_type, APP_MIME)
            self.assertFalse(missing.exists())

"""Offline CLI PNG delivery and shared metadata contracts."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from garmin_archive import cli
from garmin_archive.archive import Archive
from garmin_archive.chart_delivery import chart_metadata
from garmin_archive.queries import get_trend, open_archive
from garmin_archive.sleep import get_sleep


class CLIChartMetadataTest(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.data_dir = self.root / 'archive'
        with contextlib.closing(Archive(self.data_dir)) as archive:
            archive.mark_synthetic('test', 42, '2026-01-04T00:00:00Z')
            archive.save_daily('sleep', '2026-01-01', {
                'sleepTimeSeconds': 27000, 'sleepScores': {'overall': {'value': 80}}})
            archive.save_daily('sleep', '2026-01-02', {'sleepTimeSeconds': 28000})
            archive.mark_error('sleep', '2026-01-02', 'PRIVATE synthetic failure')
            archive.save_daily('body_battery', '2026-01-01', [{
                'date': '2026-01-01',
                'bodyBatteryValueDescriptorDTOList': [
                    {'bodyBatteryValueDescriptorIndex': 0, 'bodyBatteryValueDescriptorKey': 'bodyBatteryLevel'},
                    {'bodyBatteryValueDescriptorIndex': 1, 'bodyBatteryValueDescriptorKey': 'timestamp'}],
                'bodyBatteryValuesArray': [[25, '2026-01-01T00:00:00Z'], [85, '2026-01-01T07:00:00Z']]}])
            archive.connection.execute("UPDATE daily_data SET fetched_at='2026-01-04T12:00:00Z'")
            archive.connection.commit()
        self.before = {p.name: p.read_bytes() for p in self.data_dir.iterdir() if p.is_file()}
        for name in ('Archive', 'PersonalApiAuthenticator', 'GarminPersonalApiClient', 'resolve_api_key', '_sync'):
            mock = self.stack.enter_context(patch(f'garmin_archive.cli.{name}', side_effect=AssertionError('sync/auth attempted')))
            self.addCleanup(mock.assert_not_called)

    def run_chart(self, metric='sleep', *options, target=None):
        target = target or self.root / 'chart.png'
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                code = cli.main(['--data-dir', str(self.data_dir), 'chart', metric,
                    '--from', '2026-01-01', '--to', '2026-01-03', '--output', str(target), *options])
            except SystemExit as error:
                code = error.code
        self.assertEqual({p.name: p.read_bytes() for p in self.data_dir.iterdir() if p.is_file()}, self.before)
        self.assertNotIn('PRIVATE', stdout.getvalue() + stderr.getvalue())
        return code, stdout.getvalue(), stderr.getvalue()

    def assert_failure(self, result, code, error):
        actual_code, stdout, stderr = result
        self.assertEqual((actual_code, stdout), (code, ''))
        self.assertEqual(json.loads(stderr)['error']['code'], error)

    @unittest.skipUnless(importlib.util.find_spec('matplotlib'), 'charts extra not installed')
    def test_default_confirmation_and_json_sleep_metadata_match_delivered_png(self):
        from PIL import Image
        target = self.root / 'default.png'
        self.assertEqual(self.run_chart(target=target), (0, f'Chart saved to {target}\n', ''))
        target = self.root / 'structured.png'
        code, stdout, stderr = self.run_chart('sleep', '--json', '--layout', 'wide', target=target)
        self.assertEqual((code, stderr), (0, ''))
        metadata = json.loads(stdout)
        with open_archive(self.data_dir) as db:
            expected = chart_metadata(get_sleep(db, '2026-01-01', '2026-01-03'), layout='wide')
        expected.update(output_path=str(target), delivery='PNG file saved; host attachment and display must be verified separately.')
        self.assertEqual(metadata, expected)
        self.assertEqual(metadata['coverage']['sleep_duration'], {
            'requested_days': 3, 'days_with_value': 1, 'statuses': {'ok': 1, 'error': 1, 'not_checked': 1}})
        self.assertEqual(metadata['units']['sleep_duration'], 'hours')
        self.assertTrue(metadata['synthetic'])
        self.assertIn('simulated', metadata['freshness']['meaning'])
        self.assertEqual(metadata['freshness']['latest_available_fetch'], '2026-01-04T12:00:00Z')
        with Image.open(target) as image:
            self.assertEqual(image.info['Description'], metadata['caption'])
            image.verify()
        if os.name != 'nt':
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    @unittest.skipUnless(importlib.util.find_spec('matplotlib'), 'charts extra not installed')
    def test_body_battery_sampling_caveats_and_empty_freshness(self):
        for metric in ('body_battery_max', 'body_battery_last'):
            with self.subTest(metric=metric):
                code, stdout, stderr = self.run_chart(metric, '--json', target=self.root / f'{metric}.png')
                self.assertEqual((code, stderr), (0, ''))
                metadata = json.loads(stdout)
                self.assertIn('Observed samples only', metadata['caption'])
                self.assertIn('not proven full-day extrema or current levels', metadata['alt_text'])
                self.assertIn('continuous full-day coverage', ' '.join(metadata['explanations']))
                self.assertEqual(metadata['units'], {metric: 'Body Battery'})
                self.assertEqual(metadata['coverage'][metric]['days_with_value'], 1)
        code, stdout, stderr = self.run_chart('steps', '--json', target=self.root / 'empty.png')
        self.assertEqual((code, stderr), (0, ''))
        metadata = json.loads(stdout)
        self.assertEqual(metadata['coverage']['steps']['days_with_value'], 0)
        self.assertIsNone(metadata['freshness']['earliest_available_fetch'])
        self.assertIsNone(metadata['freshness']['latest_available_fetch'])
        self.assertIn('Gaps are not zero', ' '.join(metadata['explanations']))

    def test_failures_keep_codes_redaction_and_empty_stdout_in_both_modes(self):
        for options in ((), ('--json',)):
            with self.subTest(options=options):
                for exception, code, error in (
                    (ImportError('PRIVATE dependency path'), 2, 'dependency_unavailable'),
                    (OSError('PRIVATE output path'), 1, 'output_error')):
                    with patch('garmin_archive.charts.render_png', side_effect=exception):
                        self.assert_failure(self.run_chart('sleep', *options), code, error)
                    self.assertFalse((self.root / 'chart.png').exists())
                self.assert_failure(self.run_chart('sleep', *options, target=self.root / 'bad.jpg'), 2, 'invalid_argument')

    @unittest.skipUnless(importlib.util.find_spec('matplotlib'), 'charts extra not installed')
    def test_existing_file_and_archive_are_never_overwritten(self):
        target = self.root / 'existing.png'
        target.write_bytes(b'preserve this output')
        for options in ((), ('--json',)):
            self.assert_failure(self.run_chart('sleep', *options, target=target), 1, 'output_error')
            self.assertEqual(target.read_bytes(), b'preserve this output')
            with patch('garmin_archive.charts.render_png', side_effect=AssertionError('must validate suffix first')):
                self.assert_failure(self.run_chart('sleep', *options, target=self.data_dir / 'archive.sqlite3'), 2, 'invalid_argument')

    def test_explicit_synthetic_label_without_archive_marker(self):
        # Exercise the CLI flag independently of automatic provenance labeling.
        with open_archive(self.data_dir) as db:
            trend = get_trend(db, 'body_battery_max', '2026-01-01', '2026-01-03')
        trend['archive_provenance'] = {'synthetic': False}
        with patch('garmin_archive.cli.get_trend', return_value=trend), patch('garmin_archive.charts.render_trend') as render:
            code, stdout, stderr = self.run_chart('body_battery_max', '--json', '--synthetic')
        self.assertEqual((code, stderr), (0, ''))
        self.assertTrue(json.loads(stdout)['synthetic'])
        self.assertTrue(render.call_args.kwargs['synthetic'])

"""Synthetic chart semantics, brand assets and demo isolation."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import math
import os
import runpy
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from garmin_archive import cli
from garmin_archive.archive import Archive
from garmin_archive.brand import get_brand
from garmin_archive.queries import METRICS, get_trend, open_archive

CREATE_DEMO = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts' / 'create_demo_archive.py'))['create_demo_archive']


class BrandDemoTest(unittest.TestCase):
    def test_brand_matches_authored_logo_and_needs_no_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / 'missing'
            output = io.StringIO()
            with patch('garmin_archive.cli.Archive', side_effect=AssertionError('Opened archive')):
                with contextlib.redirect_stdout(output):
                    self.assertEqual(cli.main(['--data-dir', str(missing), 'brand']), 0)
            self.assertFalse(missing.exists())
            brand = json.loads(output.getvalue())
        paths = brand['assets']
        self.assertTrue(all(Path(p).is_file() for p in paths.values()))
        fills = {e.get('fill', '').lower() for e in ET.parse(paths['logo_svg']).getroot()}
        self.assertIn(brand['colors']['primary'].lower(), fills)
        self.assertIn(brand['colors']['ink'].lower(), fills)

    def test_demo_has_all_metrics_and_refuses_existing_destinations(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp) / 'demo'
            CREATE_DEMO(destination)
            database = destination / 'archive.sqlite3'
            before = database.read_bytes()
            with open_archive(destination) as db:
                for metric in METRICS:
                    trend = get_trend(db, metric, '2026-01-01', '2026-01-30')
                    self.assertEqual(trend['coverage']['days_with_value'], 26)
                    self.assertEqual([trend['points'][i]['status'] for i in (3,7,11,16)],
                                     ['not_checked','empty','error','metric_not_returned'])
                    self.assertIsNone(trend['points'][11]['value'])
                    if metric in ('steps', 'distance'):
                        self.assertEqual(trend['points'][15]['value'], 0)
            with self.assertRaises(FileExistsError):
                CREATE_DEMO(destination)
            self.assertEqual(database.read_bytes(), before)
            empty = Path(temp) / 'empty'
            empty.mkdir()
            with self.assertRaises(FileExistsError):
                CREATE_DEMO(empty)
            self.assertEqual(list(empty.iterdir()), [])
            self.assertIn('not real health data', (destination / 'SYNTHETIC.txt').read_text())


@unittest.skipUnless(importlib.util.find_spec('matplotlib'), 'charts extra not installed')
class ChartsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data_dir = self.root / 'demo'
        CREATE_DEMO(self.data_dir)
        self.before = (self.data_dir / 'archive.sqlite3').read_bytes()

    def query(self, metric, start='2026-01-01', end='2026-01-30'):
        with open_archive(self.data_dir) as db:
            return get_trend(db, metric, start, end)

    def test_sleep_converts_units_masks_failed_values_and_dates_statuses(self):
        from garmin_archive.charts import build_trend_figure
        trend = self.query('sleep_duration')
        figure = build_trend_figure(trend, synthetic=True)
        plotted = figure.axes[0].lines[0].get_ydata()
        self.assertEqual(plotted[0], trend['points'][0]['value'] / 3600)
        for i in (3,7,11,16):
            self.assertTrue(math.isnan(plotted[i]))
        text = '\n'.join(t.get_text() for t in figure.texts)
        for expected in ('hours', 'SYNTHETIC DATA', 'synthetic demo archive', '26 of 30 nights',
                         'Failed refresh [×]: Jan 12', 'Empty response [□]: Jan 8', 'Not checked [|]: Jan 4',
                         'Metric not returned [◇]: Jan 17', 'Values fetched:'):
            self.assertIn(expected, text)
        self.assertNotIn('retained values must be masked', text)
        strip = figure.axes[1]
        failures = [line.get_xdata()[0] for line in strip.lines if line.get_marker() == 'x']
        self.assertEqual(failures, [11])
        self.assertEqual((self.data_dir / 'archive.sqlite3').read_bytes(), self.before)

    def test_bars_start_at_zero_preserve_zero_and_follow_profile_distance(self):
        from garmin_archive.charts import build_trend_figure
        from matplotlib.colors import to_hex
        for metric in ('steps', 'distance'):
            trend = self.query(metric)
            figure = build_trend_figure(trend)
            axis = figure.axes[0]
            self.assertEqual(axis.get_ylim()[0], 0)
            self.assertEqual(axis.patches[15].get_height(), 0)
            self.assertTrue(math.isnan(axis.patches[11].get_height()))
            self.assertEqual(to_hex(axis.patches[0].get_facecolor()).upper(), get_brand()['colors']['primary'])
            if metric == 'distance':
                self.assertEqual(axis.patches[0].get_height(), trend['display']['points'][0]['value'])
                self.assertIn('mi', [t.get_text() for t in figure.texts])

    def test_png_metadata_private_creation_and_no_overwrite(self):
        from garmin_archive.charts import render_trend
        from PIL import Image
        output = self.root / 'sleep.png'
        render_trend(self.query('sleep_duration'), output, synthetic=True)
        with Image.open(output) as image:
            image.verify()
            self.assertIn('Synthetic data', image.info['Description'])
            self.assertEqual(image.info['Software'], 'Garmin Data Workbench')
        if os.name != 'nt':
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        before = output.read_bytes()
        with self.assertRaises(FileExistsError):
            render_trend(self.query('steps'), output)
        self.assertEqual(output.read_bytes(), before)

    def test_empty_single_day_and_dense_coverage_render_without_invented_values(self):
        from garmin_archive.charts import build_trend_figure, render_trend
        empty = self.root / 'empty'
        Archive(empty).close()
        with open_archive(empty) as db:
            trend = get_trend(db, 'sleep_duration', '2025-12-01', '2026-02-28')
        figure = build_trend_figure(trend)
        self.assertIn('No values', [t.get_text() for t in figure.texts])
        self.assertFalse(figure.axes[0].lines)
        figure.savefig(self.root / 'empty.png')
        for metric in METRICS:
            render_trend(self.query(metric, '2026-01-01', '2026-01-01'), self.root / f'{metric}.png', layout='wide')
        # Alternate coverage over 90 days exercises long, wrapped date lists.
        for i, point in enumerate(trend['points']):
            point['status'] = ('error', 'empty', 'not_checked')[i % 3]
        render_trend(trend, self.root / 'dense.png')

    def test_cli_options_preserve_json_errors_and_help_explains_data_dir(self):
        output, errors = io.StringIO(), io.StringIO()
        target = self.root / 'cli.png'
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            code = cli.main(['--data-dir', str(self.data_dir), 'chart', 'sleep_duration',
                             '--from','2026-01-01','--to','2026-01-30','--synthetic','--layout','wide',
                             '--output', str(target)])
        self.assertEqual((code, errors.getvalue()), (0, ''))
        self.assertTrue(target.is_file())
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(errors):
            code = cli.main(['--data-dir', str(self.data_dir), 'chart', 'steps', '--output', str(target)])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(errors.getvalue())['error']['code'], 'output_error')
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit):
            cli.parser().parse_args(['chart', '--help'])
        self.assertIn('--data-dir', output.getvalue())
        self.assertEqual((self.data_dir / 'archive.sqlite3').read_bytes(), self.before)

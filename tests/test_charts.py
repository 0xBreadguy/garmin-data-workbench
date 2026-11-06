"""Synthetic chart semantics, brand assets and demo isolation."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import math
import os
import runpy
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from garmin_archive import cli
from garmin_archive.archive import Archive
from garmin_archive.brand import get_brand
from garmin_archive.queries import METRICS, get_trend, open_archive
from garmin_archive.sleep import get_sleep

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
                    self.assertEqual([trend['points'][i]['status'] for i in tuple(v + {'sleep': 0, 'daily_summary': 1, 'heart_rate': 2, 'body_battery': 3, 'hrv': 4, 'daily_summary_legacy': 5}[trend['dataset']] for v in (3,7,11,16))],
                                     ['not_checked','empty','error','metric_not_returned'])
                    self.assertTrue(all(p['value'] is None for p in trend['points'] if p['status'] != 'ok'))
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
    @classmethod
    def setUpClass(cls):
        temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temp.cleanup)
        cls.demo_template = Path(temp.name) / 'demo'
        # Chart tests consume the same data; demo generation is tested above.
        CREATE_DEMO(cls.demo_template)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data_dir = self.root / 'demo'
        # Copy a closed archive so each test can mutate only its own files.
        shutil.copytree(self.demo_template, self.data_dir)
        self.before = (self.data_dir / 'archive.sqlite3').read_bytes()

    def query(self, metric, start='2026-01-01', end='2026-01-30'):
        with open_archive(self.data_dir) as db:
            return get_trend(db, metric, start, end)

    def assert_readable_dates(self, figure, strip, count):
        figure.canvas.draw()
        ticks = list(strip.get_xticks())
        self.assertEqual(ticks, sorted(set(ticks)))
        self.assertEqual((ticks[0], ticks[-1]), (0, count - 1))
        self.assertLessEqual(len(ticks), min(5, count))
        self.assertEqual(len(strip.lines), count)  # Keep every dated coverage mark.
        bounds = [label.get_window_extent() for label in strip.get_xticklabels()]
        # A visible 10-point gutter, including at the PNG export resolution.
        for left, right in zip(bounds, bounds[1:]):
            self.assertGreaterEqual((right.x0 - left.x1) * 72 / figure.dpi, 10)

    def test_sleep_week_date_labels_have_space_in_chat_and_wide(self):
        from garmin_archive.charts import build_sleep_figure
        with open_archive(self.data_dir) as db:
            result = get_sleep(db, '2026-04-24', '2026-04-30')
        for layout in ('chat', 'wide'):
            for dpi in (100, 160):
                with self.subTest(layout=layout, dpi=dpi):
                    figure = build_sleep_figure(result, layout=layout)
                    figure.set_dpi(dpi)
                    strip = figure.axes[2]
                    self.assert_readable_dates(figure, strip, 7)
                    labels = strip.get_xticklabels()
                    self.assertEqual((labels[0].get_text(), labels[-1].get_text()), ('Apr 24', 'Apr 30'))
                    self.assertGreaterEqual(len(labels), 3)
                    self.assertEqual(figure.axes[1].get_ylim(), (0, 100))
                    self.assertEqual(strip.get_xlim(), figure.axes[1].get_xlim())

    def test_date_spacing_handles_short_long_and_calendar_boundary_ranges(self):
        from garmin_archive.charts import build_trend_figure
        cases = [('2026-01-01', days) for days in (1, 2, 3, 4, 5, 6, 8, 9, 14, 30, 90)]
        cases += [('2026-09-24', 7), ('2026-09-27', 7), ('2025-12-29', 7)]
        for first, count in cases:
            last = (date.fromisoformat(first) + timedelta(days=count - 1)).isoformat()
            trend = self.query('sleep_duration', first, last)
            for layout in ('chat', 'wide'):
                with self.subTest(first=first, count=count, layout=layout):
                    figure = build_trend_figure(trend, layout=layout)
                    figure.set_dpi(160)
                    self.assert_readable_dates(figure, figure.axes[1], count)

    def test_sparse_sleep_week_keeps_dates_and_missingness(self):
        from garmin_archive.charts import build_sleep_figure
        # Leave only Jan 5 available, retaining the unchecked/empty source gaps.
        with open_archive(self.data_dir) as db:
            result = get_sleep(db, '2026-01-04', '2026-01-10')
        for night in result['nights'][2:]:
            night['values'] = dict.fromkeys(night['values'])
            if night['status'] == 'ok':
                night['status'] = 'not_checked'
            night['stages_complete'] = False
        for layout in ('chat', 'wide'):
            with self.subTest(layout=layout):
                figure = build_sleep_figure(result, layout=layout)
                strip = figure.axes[2]
                self.assert_readable_dates(figure, strip, 7)
                self.assertEqual([line.get_marker() for line in strip.lines], ['|', 'o', '|', '|', 's', '|', '|'])
                duration = figure.axes[0].lines[0].get_ydata()
                self.assertEqual(sum(not math.isnan(value) for value in duration), 1)
                self.assertIn('1/7', [t.get_text() for t in figure.texts])

    def test_sleep_converts_units_masks_failed_values_and_dates_statuses(self):
        from garmin_archive.charts import build_trend_figure
        trend = self.query('sleep_duration')
        figure = build_trend_figure(trend, synthetic=True)
        plotted = figure.axes[0].lines[0].get_ydata()
        self.assertEqual(plotted[0], trend['points'][0]['value'] / 3600)
        for i in (3,7,11,16):
            self.assertTrue(math.isnan(plotted[i]))
        text = '\n'.join(t.get_text() for t in figure.texts)
        for expected in ('hours', 'SYNTHETIC DATA', '26/30',
                         'Failed refresh [×]: Jan 12', 'Empty response [□]: Jan 8', 'Not checked [|]: Jan 4',
                         'Metric not returned [◇]: Jan 17'):
            self.assertIn(expected, text)
        self.assertNotIn('Values fetched:', text)
        self.assertNotIn('Gaps are not zero', text)
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
            self.assertTrue(math.isnan(axis.patches[12].get_height()))
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

    def test_sleep_report_uses_separate_score_axis_and_only_complete_stage_bars(self):
        from garmin_archive.charts import build_sleep_figure, render_trend
        with open_archive(self.data_dir) as db:
            result = get_sleep(db, '2026-01-01', '2026-01-30')
        # Incomplete/contradictory stages must keep the total but omit the stack.
        result['nights'][0]['values']['sleep_deep'] = None
        result['nights'][0]['stages_complete'] = False
        result['nights'][1]['values']['sleep_score'] = 0
        for layout in ('chat', 'wide'):
            figure = build_sleep_figure(result, synthetic=True, layout=layout)
            self.assertEqual(figure.axes[1].get_ylim(), (0, 100))
            self.assertEqual(figure.axes[1].lines[0].get_ydata()[1], 0)
            self.assertTrue(math.isnan(figure.axes[1].lines[0].get_ydata()[11]))
            self.assertEqual(len(figure.axes[0].patches), 25 * 4)
            text = '\n'.join(t.get_text() for t in figure.texts)
            self.assertIn('Sleep overview', text)
            self.assertIn('Sleep score · 26/30 nights', text)
            self.assertIn('Stages incomplete', text)
            render_trend(result, self.root / f'sleep-{layout}.png', synthetic=True, layout=layout)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(cli.main(['--data-dir', str(self.data_dir), 'chart', 'sleep', '--from', '2026-01-01',
                                      '--to', '2026-01-30', '--synthetic', '--output', str(self.root / 'report.png')]), 0)
        self.assertEqual((self.data_dir / 'archive.sqlite3').read_bytes(), self.before)

    def test_sleep_report_empty_single_and_scalar_stress_layouts(self):
        from garmin_archive.charts import build_sleep_figure, build_trend_figure
        with open_archive(self.data_dir) as db:
            for first, last in (('2025-10-01','2025-12-29'), ('2026-01-01','2026-01-01')):
                figure = build_sleep_figure(get_sleep(db, first, last), synthetic=True)
                figure.canvas.draw()
                if first.startswith('2025'):
                    self.assertFalse(figure.axes[0].patches)
                    self.assertIsNone(figure.axes[0].get_legend())
        figure = build_trend_figure(self.query('sleep_stress'))
        figure.canvas.draw()
        summary = next(t for t in figure.texts if t.get_fontsize() == 30)
        coverage = next(t for t in figure.texts if t.get_text() == '26/30')
        self.assertFalse(summary.get_window_extent().overlaps(coverage.get_window_extent()))
        self.assertEqual(figure.axes[0].get_ylim(), (0, 100))

    def test_sleep_need_minutes_convert_to_hours_and_body_battery_levels_keep_scale(self):
        from garmin_archive.charts import build_trend_figure, build_sleep_figure
        need = self.query('sleep_need')
        figure = build_trend_figure(need)
        self.assertEqual(figure.axes[0].lines[0].get_ydata()[0], need['points'][0]['value'] / 60)
        self.assertIn('hours', [t.get_text() for t in figure.texts])
        with open_archive(self.data_dir) as db:
            report = build_sleep_figure(get_sleep(db, '2026-01-01', '2026-01-30'))
        from matplotlib.colors import to_hex
        self.assertEqual({to_hex(bar.get_facecolor()).upper() for bar in report.axes[0].patches},
                         set(get_brand()['colors']['sleep_stages'].values()))
        line = next(line for line in report.axes[0].lines if line.get_label() == 'Garmin need')
        self.assertEqual(line.get_ydata()[0], need['points'][0]['value'] / 60)
        self.assertTrue(math.isnan(line.get_ydata()[11]))
        for metric in ('body_battery_min', 'body_battery_max', 'body_battery_first', 'body_battery_last'):
            figure = build_trend_figure(self.query(metric))
            figure.canvas.draw()
            self.assertEqual(figure.axes[0].get_ylim(), (0, 100))
            self.assertTrue(math.isnan(figure.axes[0].lines[0].get_ydata()[14]))
            summary = next(t for t in figure.texts if t.get_fontsize() == 30)
            coverage = next(t for t in figure.texts if t.get_text() == '26/30')
            self.assertFalse(summary.get_window_extent().overlaps(coverage.get_window_extent()))

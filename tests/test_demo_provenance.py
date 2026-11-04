"""Scenario answers and provenance across read-only adapters, with no account data."""
import contextlib
import importlib.util
import io
import json
import hashlib
import os
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from garmin_archive.archive import Archive
from garmin_archive.api_data import source_data, source_series
from garmin_archive.body_battery import get_body_battery
from garmin_archive.provenance import archive_provenance
from garmin_archive.queries import get_day, get_trend, open_archive
from garmin_archive.sleep import get_sleep

DEMO = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/create_demo_archive.py'))
CREATE = DEMO['create_demo_archive']


class DemoHandoffTest(unittest.TestCase):
    def create(self, destination, *options):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(DEMO['main']([str(destination), *options]), 0)
        return output.getvalue()

    def examples(self, output):
        # Execute the displayed native-shell commands, including quoting and absolute paths.
        return [line for line in output.splitlines()
                if line.startswith(('garmin-archive ', "& 'garmin-archive' "))]

    def run_example(self, command, cwd):
        shell = shutil.which('powershell.exe' if sys.platform == 'win32' else 'sh')
        if not shell:
            self.skipTest('Native shell is unavailable')
        options = ['-NoProfile', '-NonInteractive', '-Command'] if sys.platform == 'win32' else ['-c']
        env = {**os.environ, 'PATH': str(Path(sys.executable).parent) + os.pathsep + os.environ.get('PATH', '')}
        result = subprocess.run([shell, *options, command], cwd=cwd, env=env, capture_output=True,
                                text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def test_default_handoff_examples_query_and_render_the_latest_demo_week(self):
        with tempfile.TemporaryDirectory() as root:
            destination = Path(root) / "demo with spaces"
            output = self.create(destination)
            for detail in ('v2, seed 42', 'Manual/offline', '2026-01-01 through 2026-04-30',
                           '2026-04-24 through 2026-04-30', 'First question:',
                           '2026-05-01T12:00:00+00:00', 'not live freshness',
                           'no observations', 'independent formulas', 'Body Battery values are intentionally fixed'):
                self.assertIn(detail, output)
            commands = self.examples(output)
            self.assertEqual(len(commands), 2)
            before = (destination / 'archive.sqlite3').read_bytes()
            summary = json.loads(self.run_example(commands[0], root))
            self.assertEqual((summary['from'], summary['to']), ('2026-04-24', '2026-04-30'))
            self.assertEqual(summary['coverage']['requested_days'], 7)
            self.assertTrue(summary['archive_provenance']['synthetic'])
            for name in ('sleep_duration', 'sleep_deep', 'sleep_rem', 'sleep_score', 'sleep_need'):
                self.assertEqual(summary['coverage']['fields'][name]['days_with_value'], 7)
            if importlib.util.find_spec('matplotlib'):
                self.run_example(commands[1], root)
                self.assertTrue((destination / 'synthetic-sleep-overview.png').read_bytes().startswith(b'\x89PNG\r\n\x1a\n'))
            self.assertEqual((destination / 'archive.sqlite3').read_bytes(), before)

    def test_custom_windows_stay_in_the_corpus_and_longer_demo_preserves_the_first(self):
        with tempfile.TemporaryDirectory() as root:
            shorter = Path(root) / 'shorter'
            for days, start, end in ((3, '2026-01-01', '2026-01-03'),
                                     (30, '2026-01-24', '2026-01-30'),
                                     (320, '2026-11-10', '2026-11-16')):
                with self.subTest(days=days):
                    destination = shorter if days == 3 else Path(root) / str(days)
                    output = self.create(destination, '--days', str(days))
                    if days == 3:
                        original = (shorter / 'archive.sqlite3').read_bytes()
                        answers = (shorter / 'known-answers.json').read_bytes()
                    self.assertIn(f'2026-01-01 through {end} ({days} dates;', output)
                    self.assertIn(f'{start} through {end}', output)
                    summary = json.loads(self.run_example(self.examples(output)[0], root))
                    self.assertEqual((summary['from'], summary['to']), (start, end))
                    self.assertEqual(summary['coverage']['requested_days'], min(days, 7))
                    self.assertEqual(summary['nights'][-1]['fetched_at'], '2026-05-01T12:00:00+00:00')
            self.assertEqual((shorter / 'archive.sqlite3').read_bytes(), original)
            self.assertEqual((shorter / 'known-answers.json').read_bytes(), answers)

    def test_empty_handoff_does_not_offer_a_week_of_observations(self):
        with tempfile.TemporaryDirectory() as root:
            output = self.create(Path(root) / 'empty', '--empty')
            self.assertIn('Available dates: none', output)
            self.assertIn('no observations', output)
            self.assertNotIn('First question:', output)
            self.assertEqual(self.examples(output), [])


class DemoProvenanceTest(unittest.TestCase):
    def test_versioned_scenarios_match_independent_answers_and_preserve_database(self):
        with tempfile.TemporaryDirectory() as root:
            for profile in ('statute', 'metric-dst'):
                path = Path(root) / profile
                CREATE(path, profile=profile)
                before = (path / 'archive.sqlite3').read_bytes()
                answers = json.loads((path / 'known-answers.json').read_text())
                if profile == 'statute':
                    # v2 default corpus fingerprint: changing expected answers requires deliberate version review.
                    self.assertEqual(hashlib.sha256((path / 'known-answers.json').read_bytes()).hexdigest(),
                                     '2ad39e50b1fbb6eb4cc13cf0600c3680bbe082fce253795a61fb489dde6cac7a')
                self.assertEqual((answers['corpus_version'], answers['seed'], answers['days']), ('2', 42, 120))
                with open_archive(path) as db:
                    for case in answers['cases']:
                        for metric, expected in case['metrics'].items():
                            with self.subTest(profile=profile, first=case['from'], metric=metric):
                                actual = get_trend(db, metric, case['from'], case['to'])
                                self.assertEqual(actual['coverage']['days_with_value'], expected['days_with_value'])
                                self.assertEqual(actual['coverage']['statuses'], expected['statuses'])
                                self.assertEqual(actual['mean_of_available_days'], expected['mean_of_available_days'])
                                self.assertEqual([{k: p[k] for k in ('day', 'status', 'value')} for p in actual['points']], expected['points'])
                    with self.assertRaises(ValueError):
                        get_trend(db, 'steps', '2026-01-01', '2026-04-01')
                    sleep = get_sleep(db, '2026-02-05', '2026-02-08')['nights']
                    self.assertEqual([n['stages_complete'] for n in sleep], [False, True, True, False])
                    self.assertIsNone(sleep[1]['values']['sleep_score'])
                    self.assertIsNone(sleep[2]['values']['sleep_need'])
                    self.assertFalse(get_body_battery(db, '2026-02-10', '2026-02-10')['days'][0]['values']['body_battery_last'])
                    self.assertEqual(get_body_battery(db, '2026-02-11', '2026-02-11')['days'][0]['conflicting_timestamps'], 1)
                    nap = get_sleep(db, '2026-01-26', '2026-01-26')['nights'][0]
                    self.assertEqual(nap['values']['nap_duration'], nap['naps']['episodes'][0]['duration'])
                    no_detail = get_sleep(db, '2026-01-21', '2026-01-21')['nights'][0]
                    self.assertIn('episode detail was not returned', no_detail['naps']['detail_note'])
                    if profile == 'metric-dst':
                        dst = get_sleep(db, '2026-03-28', '2026-03-30')['nights']
                        self.assertTrue(dst[0]['timing']['end_local'].endswith('+01:00'))
                        self.assertTrue(dst[-1]['timing']['end_local'].endswith('+02:00'))
                        self.assertEqual(get_trend(db, 'distance', '2026-03-28', '2026-03-30')['display']['unit'], 'km')
                self.assertEqual((path / 'archive.sqlite3').read_bytes(), before)

    def test_provenance_survives_copy_and_old_readers_do_not_migrate(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / 'demo'; CREATE(path, days=30)
            copied = Path(root) / 'copied'; copied.mkdir()
            shutil.copyfile(path / 'archive.sqlite3', copied / 'archive.sqlite3')
            with open_archive(copied) as db:
                for result in (get_day(db, '2026-01-01'), get_trend(db, 'steps', '2026-01-01', '2026-01-01'),
                               get_sleep(db, '2026-01-01', '2026-01-01'), get_body_battery(db, '2026-01-01', '2026-01-01'),
                               source_data(db, 'sleep', '2026-01-01'), source_series(db, 'sleep', '/sleepTimeSeconds', '2026-01-01', '2026-01-01')):
                    self.assertTrue(result['archive_provenance']['synthetic'])
                    self.assertFalse(result['archive_provenance']['marker_present'])
            legacy = Path(root) / 'legacy'; archive = Archive(legacy)
            archive.connection.execute('DROP TABLE archive_provenance'); archive.connection.commit(); archive.close()
            before = (legacy / 'archive.sqlite3').read_bytes()
            with open_archive(legacy) as db:
                self.assertIsNone(archive_provenance(db)['synthetic'])
                (legacy / 'SYNTHETIC.txt').write_text('legacy marker')
                p = archive_provenance(db)
                self.assertTrue(p['synthetic'])
                self.assertIsNone(p['created_at'])
            self.assertEqual((legacy / 'archive.sqlite3').read_bytes(), before)

    def test_empty_archive_and_generated_values_are_repeatable(self):
        with tempfile.TemporaryDirectory() as root:
            paths = [Path(root) / name for name in ('one', 'two', 'empty')]
            for path in paths:
                CREATE(path, empty=path.name == 'empty')
            self.assertEqual((paths[0] / 'known-answers.json').read_bytes(), (paths[1] / 'known-answers.json').read_bytes())
            with open_archive(paths[2]) as db:
                self.assertEqual(get_trend(db, 'steps', '2026-01-01', '2026-03-31')['coverage']['days_with_value'], 0)
                self.assertTrue(archive_provenance(db)['synthetic'])
            with open_archive(paths[0]) as db:
                nights = get_sleep(db, '2026-01-24', '2026-01-30')['nights']
                self.assertGreater(len({n['values']['sleep_awake'] for n in nights}), 3)
                self.assertGreater(len({n['timing']['end_utc'][11:] for n in nights}), 3)

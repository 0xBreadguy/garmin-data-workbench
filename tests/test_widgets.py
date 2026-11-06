"""Native snapshot parity, bounded safe export and read-only CLI behavior."""
import contextlib
import io
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from garmin_archive.brand import brand_tokens_css, get_brand
from garmin_archive.cli import main
from garmin_archive.mcp_apps import recovery_app_html
from garmin_archive.queries import open_archive
from garmin_archive.recovery import compare_sleep_recovery, get_sleep_recovery
from garmin_archive.sleep import STAGES
from garmin_archive.widgets import recovery_widget_html, recovery_widget_snapshot
from test_recovery import seed


class WidgetTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / 'archive'
        seed(self.archive)

    def test_snapshot_parity_and_one_read_transaction(self):
        with open_archive(self.archive) as db:
            def checked(*args):
                self.assertTrue(db.in_transaction)
                return compare_sleep_recovery(*args)
            with patch('garmin_archive.widgets.compare_sleep_recovery', side_effect=checked):
                value = recovery_widget_snapshot(db, '2026-01-01', '2026-01-04')
            self.assertFalse(db.in_transaction)
            self.assertEqual(value['report'], get_sleep_recovery(db, '2026-01-01', '2026-01-04'))
            self.assertEqual(value['comparison'], compare_sleep_recovery(db, '2026-01-03', '2026-01-04', '2026-01-01', '2026-01-02'))
            self.assertIsNone(recovery_widget_snapshot(db, '2026-01-01', '2026-01-01')['comparison'])
            with self.assertRaises(ValueError):
                recovery_widget_snapshot(db, '2026-01-01', '2026-04-01')

    def test_fragment_escaping_size_and_defaults(self):
        with open_archive(self.archive) as db:
            value = recovery_widget_snapshot(db, end='2026-01-14')
            self.assertEqual(value['report']['from'], '2026-01-01')
            largest = recovery_widget_snapshot(db, '2026-01-01', '2026-03-31')
        value['report']['archive_provenance']['freshness_meaning'] = '</script><script>alert("&")</script>'
        html = recovery_widget_html(value)
        self.assertNotRegex(html.lower(), r'<(?:!doctype|html\b|head\b|body\b|form\b|iframe\b)')
        self.assertNotIn('/*__', html)
        self.assertNotIn('<script src=', html)
        self.assertNotIn('SENTINEL', html)
        self.assertNotIn('</script><script>alert', html)
        payload = re.search(r'id="recovery-snapshot">(.*?)</script>', html, re.S).group(1)
        self.assertEqual(json.loads(payload), value)
        self.assertLess(len(recovery_widget_html(largest).encode()), 1_000_000)
        with patch('garmin_archive.widgets.MAX_WIDGET_BYTES', 10):
            with self.assertRaisesRegex(ValueError, '1 MB'):
                recovery_widget_html(value)

    def test_both_routes_share_brand_tokens_stage_order_and_signature(self):
        brand = get_brand()
        stages = [stage.removeprefix('sleep_') for stage in STAGES]
        self.assertEqual(list(brand['colors']['sleep_stages']), stages)
        self.assertEqual(list(brand['dark_colors']['sleep_stages']), stages)
        logo = re.findall(r'<path\b[^>]*/>', Path(brand['assets']['logo_svg']).read_text(encoding='utf-8'))
        self.assertEqual(len(logo), 3)
        with open_archive(self.archive) as db:
            widget = recovery_widget_html(recovery_widget_snapshot(db, '2026-01-01', '2026-01-04'))
        for html in (recovery_app_html(), widget):
            self.assertIn(brand_tokens_css(), html)
            for path in logo:
                self.assertIn(path, html)
            self.assertIn(repr(stages), html.replace('"', "'"))
            self.assertIn("['Deep', 'REM', 'Light', 'Unclassified']", html)

    def test_interactive_ui_colors_come_from_brand_tokens(self):
        ui = Path(__file__).parents[1] / 'src' / 'garmin_archive' / 'ui'
        hex_color = r'#[0-9a-fA-F]{3,8}\b'
        css = (ui / 'recovery.css').read_text(encoding='utf-8')
        # White text on brand fills and the logo plate, plus the shared focus ring, are the only literals.
        self.assertLessEqual(set(re.findall(hex_color, css)), {'#fff', '#438dff'})
        self.assertEqual(re.findall(hex_color, (ui / 'recovery.js').read_text(encoding='utf-8')), [])

    def test_cli_private_export_no_overwrite_no_sync(self):
        before = {p.name: p.read_bytes() for p in self.archive.iterdir() if p.is_file()}
        target = self.root / 'recovery.html'
        args = ['--data-dir', str(self.archive), 'widget', 'sleep-recovery',
                '--from', '2026-01-01', '--to', '2026-01-04', '--output', str(target)]
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch('garmin_archive.cli.Archive', side_effect=AssertionError('writer opened')):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(main(args), 0)
        metadata = json.loads(stdout.getvalue())
        self.assertEqual(stderr.getvalue(), '')
        self.assertEqual(metadata['output_path'], str(target))
        self.assertTrue(metadata['archive_provenance']['synthetic'])
        self.assertEqual(metadata['bytes'], target.stat().st_size)
        if os.name != 'nt':
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        contents = target.read_bytes()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            self.assertEqual(main(args), 1)
        self.assertEqual(json.loads(stderr.getvalue())['error']['code'], 'output_error')
        self.assertEqual(contents, target.read_bytes())
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.archive.iterdir() if p.is_file()})

    def test_missing_archive_and_invalid_destination_create_nothing(self):
        target = self.root / 'widget.html'
        missing = self.root / 'absent'
        for archive, output, code, error in [(missing, target, 1, 'archive_unavailable'),
                                           (self.archive, target.with_suffix('.png'), 2, 'invalid_argument')]:
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(main(['--data-dir', str(archive), 'widget', 'sleep-recovery',
                                      '--to', '2026-01-04', '--output', str(output)]), code)
            self.assertEqual(stdout.getvalue(), '')
            self.assertEqual(json.loads(stderr.getvalue())['error']['code'], error)
            self.assertFalse(output.exists())
        self.assertFalse(missing.exists())

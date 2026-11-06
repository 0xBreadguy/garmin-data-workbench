"""Native Grok source export: shared data, bounded bytes and private delivery."""
import contextlib
import io
import json
import math
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from garmin_archive import widgets
from garmin_archive.archive import Archive
from garmin_archive.cli import main
from garmin_archive.queries import open_archive
from garmin_archive.recovery import compare_sleep_recovery, get_sleep_recovery
from test_recovery import seed


def embedded_snapshot(source):
    template = (Path(widgets.__file__).with_name("ui") / "recovery.canvas.tsx").read_text(encoding="utf-8")
    before, after = template.split(widgets.GROK_SNAPSHOT_MARKER)
    assert source.startswith(before) and source.endswith(after)
    return json.loads(source[len(before):len(source) - len(after) if after else None])


class GrokWidgetTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "archive"
        seed(self.archive)

    def invoke(self, output, *, host="grok", start="2026-01-01", end="2026-01-04", archive=None):
        args = ["--data-dir", str(archive or self.archive), "widget", "sleep-recovery",
                "--from", start, "--to", end, "--output", str(output)]
        if host is not None:
            args += ["--host", host]
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_shared_snapshot_parity_coherent_transaction_and_bounds(self):
        with open_archive(self.archive) as db:
            shared_query = widgets.get_sleep_recovery
            shared_compare = widgets.compare_sleep_recovery

            def report(*args):
                self.assertTrue(db.in_transaction)
                return shared_query(*args)

            def comparison(*args):
                self.assertTrue(db.in_transaction)
                return shared_compare(*args)

            with patch.object(widgets, "get_sleep_recovery", side_effect=report), \
                    patch.object(widgets, "compare_sleep_recovery", side_effect=comparison):
                info = widgets.write_recovery_widget(db, self.root / "coherent.canvas.tsx",
                    "2026-01-01", "2026-01-04", host="grok")
            self.assertFalse(db.in_transaction)
            payload = embedded_snapshot(Path(info["output_path"]).read_text(encoding="utf-8"))
            self.assertEqual(payload, {"schema_version": 1,
                "report": get_sleep_recovery(db, "2026-01-01", "2026-01-04"),
                "comparison": compare_sleep_recovery(db, "2026-01-03", "2026-01-04", "2026-01-01", "2026-01-02")})
            self.assertEqual(payload["report"]["sleep"]["nights"][1]["values"]["sleep_duration"], 0)
            self.assertIsNone(payload["report"]["sleep"]["nights"][2]["values"]["sleep_duration"])
            self.assertIsNone(payload["report"]["trends"]["overnight_hrv"]["points"][1]["value"])
            self.assertNotIn("SENTINEL", Path(info["output_path"]).read_text(encoding="utf-8"))
            single = widgets.recovery_widget_snapshot(db, "2026-01-01", "2026-01-01")
            self.assertIsNone(embedded_snapshot(widgets.recovery_grok_canvas(single))["comparison"])
            longest = widgets.recovery_widget_snapshot(db, "2026-01-01", "2026-03-31")
            self.assertEqual(len(embedded_snapshot(widgets.recovery_grok_canvas(longest))["report"]["sleep"]["nights"]), 90)
            for start, end in [("2026-01-01", "2026-04-01"), ("2026-01-02", "2026-01-01")]:
                with self.assertRaises(ValueError):
                    widgets.recovery_widget_snapshot(db, start, end)

    def test_payload_escaping_determinism_and_nonfinite_rejection(self):
        with open_archive(self.archive) as db:
            payload = widgets.recovery_widget_snapshot(db, "2026-01-01", "2026-01-04")
        dangerous = '</script><script>alert("&")</script>\u2028\u2029` ${globalThis.bad = true} \\ "\n🍞'
        payload["report"]["archive_provenance"]["freshness_meaning"] = dangerous
        source = widgets.recovery_grok_canvas(payload)
        self.assertEqual(source, widgets.recovery_grok_canvas(payload))
        self.assertEqual(embedded_snapshot(source), payload)
        self.assertNotIn('</script><script>alert', source)
        self.assertNotIn("\u2028", source)
        self.assertNotIn("\u2029", source)
        self.assertIn("\\u003c", source)
        self.assertIn("\\u0026", source)
        payload["report"]["archive_provenance"]["invalid"] = math.nan
        with self.assertRaises(ValueError):
            widgets.recovery_grok_canvas(payload)

    def test_template_marker_and_project_size_guard(self):
        with patch.object(Path, "read_text", return_value="no marker"):
            with self.assertRaisesRegex(ValueError, "exactly one"):
                widgets.recovery_grok_canvas({})
        with patch.object(Path, "read_text", return_value=widgets.GROK_SNAPSHOT_MARKER * 2):
            with self.assertRaisesRegex(ValueError, "exactly one"):
                widgets.recovery_grok_canvas({})
        output = self.root / "oversized.canvas.tsx"
        with patch.object(widgets, "MAX_GROK_CANVAS_BYTES", 10):
            code, stdout, stderr = self.invoke(output)
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertEqual(json.loads(stderr)["error"]["code"], "invalid_argument")
        self.assertIn("workbench's 1 MiB", stderr)
        self.assertIn("not a documented Grok host limit", stderr)
        self.assertFalse(output.exists())

    def test_cli_private_exclusive_export_leaves_archive_unchanged(self):
        before = {p.name: p.read_bytes() for p in self.archive.iterdir() if p.is_file()}
        target = self.root / "recovery.canvas.tsx"
        with patch("garmin_archive.cli.Archive", side_effect=AssertionError("writer opened")):
            code, stdout, stderr = self.invoke(target)
        self.assertEqual((code, stderr), (0, ""))
        metadata = json.loads(stdout)
        contents = target.read_bytes()
        self.assertEqual(metadata["output_path"], str(target))
        self.assertEqual(metadata["bytes"], len(contents))
        self.assertTrue(metadata["archive_provenance"]["synthetic"])
        self.assertIn("WriteCanvas", metadata["delivery"])
        self.assertIn("unchanged", metadata["delivery"])
        self.assertIn("private Page", metadata["delivery"])
        self.assertNotIn(b"\r\n", contents)
        if os.name != "nt":
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        code, stdout, stderr = self.invoke(target)
        self.assertEqual((code, stdout), (1, ""))
        self.assertEqual(json.loads(stderr)["error"]["code"], "output_error")
        self.assertEqual(contents, target.read_bytes())
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.archive.iterdir() if p.is_file()})

    def test_invalid_suffix_missing_archive_and_unwritable_destination(self):
        for filename in ("recovery.html", "recovery.tsx", "recovery.canvas.TSX", "recovery.canvas.tsx.txt"):
            target = self.root / filename
            code, stdout, stderr = self.invoke(target)
            self.assertEqual((code, stdout), (2, ""))
            self.assertEqual(json.loads(stderr)["error"]["code"], "invalid_argument")
            self.assertFalse(target.exists())
        missing = self.root / "missing-archive"
        target = self.root / "missing.canvas.tsx"
        code, stdout, stderr = self.invoke(target, archive=missing)
        self.assertEqual((code, stdout), (1, ""))
        self.assertEqual(json.loads(stderr)["error"]["code"], "archive_unavailable")
        self.assertFalse(target.exists())
        self.assertFalse(missing.exists())
        code, stdout, stderr = self.invoke(self.root / "missing-parent" / "page.canvas.tsx")
        self.assertEqual((code, stdout), (1, ""))
        self.assertEqual(json.loads(stderr)["error"]["code"], "output_error")
        with open_archive(self.archive) as db:
            with self.assertRaisesRegex(ValueError, "host must be"):
                widgets.write_recovery_widget(db, target, host="unknown")

    def test_default_and_explicit_muse_exports_match(self):
        default = self.root / "default.html"
        explicit = self.root / "explicit.html"
        for output, host in ((default, None), (explicit, "muse")):
            code, stdout, stderr = self.invoke(output, host=host)
            self.assertEqual((code, stderr), (0, ""))
            self.assertIn("widget.create_html_file_widget", json.loads(stdout)["delivery"])
        self.assertEqual(default.read_bytes(), explicit.read_bytes())
        self.assertIn('id="recovery-snapshot"', default.read_text(encoding="utf-8"))

    def test_unmarked_invented_archive_keeps_null_provenance_read_only(self):
        # Deliberately unmarked invented data exercises unknown provenance without
        # accessing a personal archive or claiming this fixture is live data.
        root = self.root / "unmarked-invented"
        archive = Archive(root)
        try:
            archive.save_daily("sleep", "2026-01-01", {
                "calendarDate": "2026-01-01", "sleepTimeSeconds": 25200})
        finally:
            archive.close()
        before = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
        output = self.root / "unmarked.canvas.tsx"
        code, stdout, stderr = self.invoke(output, archive=root, end="2026-01-01")
        self.assertEqual((code, stderr), (0, ""))
        metadata = json.loads(stdout)
        self.assertIsNone(metadata["archive_provenance"]["synthetic"])
        payload = embedded_snapshot(output.read_text(encoding="utf-8"))
        self.assertEqual(payload["report"]["archive_provenance"]["kind"], "unmarked")
        self.assertIsNone(payload["report"]["archive_provenance"]["synthetic"])
        self.assertEqual(payload["report"]["sleep"]["nights"][0]["values"]["sleep_duration"], 25200)
        self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()})

    def test_current_day_comparison_warning_survives_export(self):
        output = self.root / "current-day.canvas.tsx"
        with patch("garmin_archive.comparisons.local_today", return_value=(date(2026, 1, 4), "test")):
            code, stdout, stderr = self.invoke(output)
        self.assertEqual((code, stderr), (0, ""))
        payload = embedded_snapshot(output.read_text(encoding="utf-8"))
        for comparison in payload["comparison"]["metrics"].values():
            self.assertIn("period_includes_today_or_future", comparison["warnings"])
            self.assertNotIn("baseline_includes_today_or_future", comparison["warnings"])

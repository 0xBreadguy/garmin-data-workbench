"""CLI integration for private, explicitly requested Grok delivery artifacts."""
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from garmin_archive.cli import main
from test_recovery import seed


class GrokHandoffCliTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "archive"
        seed(self.archive)

    def invoke(self, output, handoff, host="grok"):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["--data-dir", str(self.archive), "widget", "sleep-recovery",
                         "--host", host, "--from", "2026-01-01", "--to", "2026-01-04",
                         "--output", str(output), "--handoff-dir", str(handoff)])
        return code, out.getvalue(), err.getvalue()

    def test_bounded_handoff_matches_export_and_archive_stays_read_only(self):
        before = {p.name: p.read_bytes() for p in self.archive.iterdir() if p.is_file()}
        output, handoff = self.root / "recovery.canvas.tsx", self.root / "handoff"
        code, out, err = self.invoke(output, handoff)
        self.assertEqual((code, err), (0, ""))
        result = json.loads(out)
        receipt = result["handoff"]
        self.assertEqual(Path(receipt["source_path"]).read_bytes(), output.read_bytes())
        self.assertEqual(receipt["expected_source"]["sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
        plan = json.loads(Path(receipt["plan_path"]).read_text())
        self.assertGreater(len(plan["steps"]), 2)
        self.assertGreater(len(plan["verification_steps"]), 2)
        self.assertEqual(plan["steps"][0]["tool"], "WriteCanvas")
        self.assertTrue(all(step["tool"] == "EditCanvas" for step in plan["steps"][1:]))
        self.assertIn("Stop on any failure", result["delivery"])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.archive.iterdir() if p.is_file()})

    def test_invalid_host_and_existing_directory_create_no_source(self):
        output, handoff = self.root / "wrong.html", self.root / "handoff"
        code, out, err = self.invoke(output, handoff, "muse")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("requires --host grok", err)
        self.assertFalse(output.exists())
        self.assertFalse(handoff.exists())
        handoff.mkdir()
        sentinel = handoff / "user-work.txt"
        sentinel.write_text("preserve")
        output = self.root / "recovery.canvas.tsx"
        code, out, err = self.invoke(output, handoff)
        self.assertEqual((code, out), (1, ""))
        self.assertEqual(json.loads(err)["error"]["code"], "output_error")
        self.assertFalse(output.exists())
        self.assertEqual(sentinel.read_text(), "preserve")

    def test_handoff_failure_reports_preserved_source_instead_of_claiming_success(self):
        output = self.root / "recovery.canvas.tsx"
        with patch("garmin_archive.grok_handoff.write_handoff", side_effect=OSError("injected write failure")):
            code, out, err = self.invoke(output, self.root / "handoff")
        self.assertEqual((code, out), (1, ""))
        self.assertEqual(json.loads(err)["error"]["code"], "handoff_error")
        self.assertIn(str(output), err)
        self.assertTrue(output.exists())

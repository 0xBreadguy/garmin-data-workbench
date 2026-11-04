"""Setup evidence never reads secrets, syncs, creates archives or proves recurrence."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from garmin_archive import cli
from garmin_archive.archive import Archive
from garmin_archive.install import assistant_guide
from garmin_archive.onboarding import routine_template, setup_receipt


class OnboardingTest(unittest.TestCase):
    def test_missing_archive_receipt_and_installed_guide_have_no_setup_side_effects(self):
        with tempfile.TemporaryDirectory() as temp:
            missing = Path(temp) / "missing"
            with patch("garmin_archive.onboarding.schedule_status", return_value={"status": "unsupported"}), \
                    patch("garmin_archive.cli.Archive", side_effect=AssertionError("Created archive")):
                for command in ("agent-guide", "setup-receipt", "routine-template"):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        self.assertEqual(cli.main(["--data-dir", str(missing), command]), 0)
                    if command == "setup-receipt":
                        result = json.loads(output.getvalue())
                        self.assertEqual(result["archive"]["status"], "unavailable")
                        self.assertEqual(result["verification"]["external_routine"], "not_inspected")
                        self.assertIsNotNone(result["installation"]["source"]["revision"])
                    if command == "agent-guide":
                        self.assertIn("chart sleep", output.getvalue())
                        self.assertIn("hypotheses", output.getvalue())
                self.assertFalse(missing.exists())

    def test_loaded_schedule_and_successful_catchup_do_not_prove_recurring_execution(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "archive"
            archive = Archive(path)
            archive.save_daily("sleep", "2026-01-01", {"sleepTimeSeconds": 0})
            archive.save_daily("sleep", "2026-01-02", {})
            archive.mark_error("sleep", "2026-01-03", "PRIVATE RESPONSE MUST NOT BE IN RECEIPT")
            with archive.connection:
                archive.connection.execute("INSERT INTO catchup_state VALUES (1, '2026-01-01', '2026-01-03', '2026-01-03T00:00:00Z', 'ok')")
            archive.close()
            before = (path / "archive.sqlite3").read_bytes()
            with patch("garmin_archive.onboarding.schedule_status", return_value={"status": "scheduled", "every_hours": 6}):
                result = setup_receipt(path)
            self.assertEqual(result["verification"]["recurring_execution"], "not_verified")
            self.assertEqual(result["native_schedule"]["status"], "scheduled")
            self.assertEqual(len(result["archive"]["coverage"]), 3)
            self.assertEqual(result["archive"]["coverage"][0]["first_day"], "2026-01-02")
            self.assertNotIn("PRIVATE RESPONSE", json.dumps(result))
            self.assertEqual((path / "archive.sqlite3").read_bytes(), before)

    def test_generic_handoff_supports_shell_without_asserting_mcp_connection(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "missing"
            result = assistant_guide("other", data_dir=path)
            self.assertIn("same host", result)
            self.assertIn("no key or MCP client", result)
            self.assertIn("chart sleep", result)
            self.assertIn("raw", result)
            self.assertFalse(path.exists())

    def test_routine_template_preserves_paths_and_does_not_schedule(self):
        with tempfile.TemporaryDirectory(prefix="Garmin Zoë's ") as temp:
            path = Path(temp) / "not yet created"
            result = routine_template(path, 2)
            self.assertFalse(result["created"])
            self.assertEqual(result["argv"][1:], ["--data-dir", str(path.resolve()), "sync", "--catch-up", "--lookback-days", "2"])
            self.assertIn("nonzero", " ".join(result["instructions"]))
            self.assertFalse(path.exists())
            with self.assertRaises(ValueError):
                routine_template(path, 32)

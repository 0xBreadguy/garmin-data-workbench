"""Installer behavior without personal data, network access, or user configuration."""
from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from garmin_personal_api.errors import GarminPersonalApiError

from garmin_archive import cli, install
from garmin_archive.archive import Archive


class InstallerFlowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.archive = Path(self.temp.name) / "archive"
        self.stdout = io.StringIO()
        self.stderr = io.StringIO()
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(contextlib.redirect_stdout(self.stdout))
        self.stack.enter_context(contextlib.redirect_stderr(self.stderr))
        self.key = self.stack.enter_context(patch("garmin_archive.install.ensure_key", return_value="existing"))
        self.sync = self.stack.enter_context(patch("garmin_archive.cli._sync", return_value=0))
        self.schedule = self.stack.enter_context(patch("garmin_archive.schedule.configure_schedule"))
        self.schedule_key = self.stack.enter_context(patch("garmin_archive.install.scheduled_key_available", return_value=True))
        self.probe = self.stack.enter_context(patch("garmin_archive.install.probe_server"))
        self.register = self.stack.enter_context(patch("garmin_archive.install.register_codex", return_value="added"))
        self.register_claude = self.stack.enter_context(patch("garmin_archive.install.register_claude", return_value="added"))
        self.discovery = self.stack.enter_context(patch("garmin_archive.install.verify_codex_discovery", return_value=[]))
        self.stack.enter_context(patch("garmin_archive.cli.sys.platform", "darwin"))

    def run_install(self, *args):
        return cli.main(["--data-dir", str(self.archive), "install", *args])

    def test_guided_install_asks_frequency_first_and_connects_codex(self):
        def answer(prompt):
            self.assertIn("How often", prompt)
            self.key.assert_not_called()
            return ""

        with patch("sys.stdin.isatty", return_value=True), patch("builtins.input", side_effect=answer):
            self.assertEqual(self.run_install(), 0)
        self.schedule.assert_called_once_with(self.archive, 6, 2)
        self.register.assert_called_once_with(self.archive)
        self.discovery.assert_called_once()
        self.assertIn("fresh Codex runtime discovered", self.stdout.getvalue())
        self.assertEqual(self.sync.call_args.args[1].lookback_days, 2)

    def test_env_only_key_does_not_install_a_broken_schedule(self):
        self.schedule_key.return_value = False
        self.assertEqual(self.run_install("--every-hours", "6"), 1)
        self.schedule.assert_not_called()
        self.discovery.assert_called_once()
        self.assertIn("shell-only key", self.stderr.getvalue())

    def test_failed_initial_sync_does_not_change_schedule_or_agent(self):
        self.sync.return_value = 1
        self.assertEqual(self.run_install("--every-hours", "6"), 1)
        self.schedule.assert_not_called()
        self.register.assert_not_called()

    def test_chatgpt_remains_pending_and_manual_preserves_schedule(self):
        self.assertEqual(self.run_install("--manual", "--client", "chatgpt"), 2)
        self.schedule.assert_not_called()
        self.register.assert_not_called()
        self.assertIn("has not configured or verified a ChatGPT connection", self.stdout.getvalue())
        self.assertIn("Any existing schedule was left unchanged", self.stdout.getvalue())

    def test_claude_registration_does_not_claim_a_successful_chat(self):
        self.assertEqual(self.run_install("--manual", "--client", "claude"), 0)
        self.register_claude.assert_called_once_with(self.archive)
        self.register.assert_not_called()
        self.assertIn("has not been checked in a Claude conversation", self.stdout.getvalue())

    def test_existing_codex_configuration_is_not_claimed_as_verified_archive(self):
        self.register.return_value = "existing"
        self.assertEqual(self.run_install("--manual"), 0)
        self.assertIn("Existing Codex registration was preserved", self.stdout.getvalue())
        self.assertIn("confirm it points to this archive", self.stdout.getvalue())

    def test_invalid_frequency_stops_before_key_and_sync(self):
        self.assertEqual(self.run_install("--every-hours", "169"), 2)
        self.key.assert_not_called()
        self.sync.assert_not_called()

    def test_connect_reuses_archive_without_sync_or_schedule(self):
        Archive(self.archive).close()
        self.assertEqual(cli.main(["--data-dir", str(self.archive), "connect", "--client", "claude"]), 0)
        self.sync.assert_not_called()
        self.schedule.assert_not_called()
        self.key.assert_not_called()
        self.register_claude.assert_called_once_with(self.archive)

    def test_connect_reports_a_pending_chatgpt_connection(self):
        Archive(self.archive).close()
        self.assertEqual(cli.main(["--data-dir", str(self.archive), "connect", "--client", "chatgpt"]), 2)
        self.assertIn("has not configured or verified a ChatGPT connection", self.stdout.getvalue())
        self.sync.assert_not_called()
        self.schedule.assert_not_called()

    def test_connect_does_not_create_missing_archive(self):
        self.assertEqual(cli.main(["--data-dir", str(self.archive), "connect"]), 1)
        self.assertFalse(self.archive.exists())
        self.probe.assert_not_called()


class KeyAndCodexTest(unittest.TestCase):
    def test_private_key_saved_only_after_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config" / "key"
            auth = MagicMock()
            auth.__enter__.return_value.obtain_token.return_value.access_token = "fake-token"
            client = MagicMock()
            with patch.dict(os.environ, {}, clear=True), \
                    patch("garmin_archive.install.DEFAULT_API_KEY_FILE", path), \
                    patch("garmin_archive.install.resolve_api_key", side_effect=GarminPersonalApiError("missing")), \
                    patch("garmin_archive.install.sys.stdin.isatty", return_value=True), \
                    patch("garmin_archive.install.getpass.getpass", return_value="test-private-key"), \
                    patch("garmin_archive.install.PersonalApiAuthenticator", return_value=auth), \
                    patch("garmin_archive.install.GarminPersonalApiClient", return_value=client):
                self.assertEqual(install.ensure_key(), "created")
            self.assertEqual(path.read_text(), "test-private-key\n")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            client.__enter__.return_value.get_user_profile_settings.assert_called_once()

    def test_bad_key_is_not_saved_or_printed(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "key"
            auth = MagicMock()
            auth.__enter__.return_value.obtain_token.side_effect = ValueError("secret response")
            with patch.dict(os.environ, {}, clear=True), \
                    patch("garmin_archive.install.DEFAULT_API_KEY_FILE", path), \
                    patch("garmin_archive.install.resolve_api_key", side_effect=GarminPersonalApiError("missing")), \
                    patch("garmin_archive.install.sys.stdin.isatty", return_value=True), \
                    patch("garmin_archive.install.getpass.getpass", return_value="test-private-key"), \
                    patch("garmin_archive.install.PersonalApiAuthenticator", return_value=auth):
                with self.assertRaises(RuntimeError) as error:
                    install.ensure_key()
            self.assertNotIn("secret response", str(error.exception))
            self.assertNotIn("test-private-key", str(error.exception))
            self.assertFalse(path.exists())

    def test_scheduled_key_must_exist_and_match_active_key(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "key"
            with patch("garmin_archive.install.DEFAULT_API_KEY_FILE", path), patch.dict(os.environ, {"GARMIN_PERSONAL_API_KEY": "key-one"}):
                self.assertFalse(install.scheduled_key_available())
                path.write_text("key-two")
                path.chmod(0o600)
                self.assertFalse(install.scheduled_key_available())
                path.write_text("key-one")
                self.assertTrue(install.scheduled_key_available())

    def test_register_does_not_overwrite_existing_codex_server(self):
        with tempfile.TemporaryDirectory() as temp:
            executable = Path(temp) / "mcp"
            executable.touch()
            with patch("garmin_archive.install.shutil.which", return_value="/fake/codex"), \
                    patch("garmin_archive.install.subprocess.run", return_value=subprocess.CompletedProcess([], 0)) as run:
                self.assertEqual(install.register_codex(Path(temp), executable=executable), "existing")
            self.assertEqual(run.call_count, 1)
            self.assertEqual(run.call_args.args[0][1:3], ["mcp", "get"])

    def test_claude_registration_uses_user_scope_only_when_absent(self):
        with tempfile.TemporaryDirectory() as temp:
            executable = Path(temp) / "mcp"
            executable.touch()
            results = [subprocess.CompletedProcess([], 1, stderr='No MCP server named "garmin-workbench"'),
                       subprocess.CompletedProcess([], 0)]
            with patch("garmin_archive.install.shutil.which", return_value="/fake/claude"), \
                    patch("garmin_archive.install.subprocess.run", side_effect=results) as run:
                self.assertEqual(install.register_claude(Path(temp), executable=executable), "added")
            command = run.call_args_list[1].args[0]
            self.assertEqual(command[1:8], ["mcp", "add", "--scope", "user", "--transport", "stdio", "garmin-workbench"])
            self.assertEqual(command[-2:], ["--data-dir", str(Path(temp).resolve())])

    def test_dot_handoff_names_the_computer_without_accessing_archive(self):
        with tempfile.TemporaryDirectory() as temp, patch("garmin_archive.install.socket.gethostname", return_value="example-mac"):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(cli.main(["--data-dir", str(Path(temp) / "missing"), "assistant-guide", "--client", "dot"]), 0)
            self.assertIn("example-mac", output.getvalue())
            self.assertIn("local Codex task", output.getvalue())
            self.assertIn("never ask me for my Garmin key", output.getvalue())
            self.assertFalse((Path(temp) / "missing").exists())

    def test_discovery_checks_real_protocol_without_a_model_turn(self):
        with tempfile.TemporaryDirectory() as temp:
            executable = Path(temp) / "codex"
            executable.write_text(f'''#!{sys.executable}
import json, sys
for line in sys.stdin:
    message = json.loads(line)
    if message.get("method") == "initialize":
        print(json.dumps({{"id": message["id"], "result": {{}}}}), flush=True)
    elif message.get("method") == "mcpServerStatus/list":
        names = {sorted(install.REQUIRED_TOOLS)!r}
        print(json.dumps({{"id": message["id"], "result": {{"data": [{{"name": "garmin-workbench", "tools": {{n: {{}} for n in names}}}}]}}}}), flush=True)
''')
            executable.chmod(0o700)
            with patch("garmin_archive.install.shutil.which", return_value=str(executable)):
                self.assertEqual(set(install.verify_codex_discovery()), install.REQUIRED_TOOLS)


if __name__ == "__main__":
    unittest.main()

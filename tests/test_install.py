"""Installer behavior without personal data, network access, or user configuration."""
from __future__ import annotations

import contextlib
import io
import logging
import runpy
import os
import subprocess
import sys
import tempfile
import unittest
import warnings
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
        self.stack.enter_context(patch("garmin_archive.onboarding.schedule_status", return_value={"status": "not_configured"}))

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

    def test_shell_install_provides_guidance_and_receipt_without_mcp_registration(self):
        self.assertEqual(self.run_install("--manual", "--client", "shell"), 0)
        self.probe.assert_not_called()
        self.register.assert_not_called()
        self.assertIn("chart sleep", self.stdout.getvalue())
        self.assertIn('"recurring_execution": "not_verified"', self.stdout.getvalue())


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
            if os.name == "posix":
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
            executable = Path(temp) / "fake_codex.py"
            executable.write_text(f'''
import json, sys
for line in sys.stdin:
    message = json.loads(line)
    if message.get("method") == "initialize":
        print(json.dumps({{"id": message["id"], "result": {{}}}}), flush=True)
    elif message.get("method") == "mcpServerStatus/list":
        names = {sorted(install.REQUIRED_TOOLS)!r}
        print(json.dumps({{"id": message["id"], "result": {{"data": [{{"name": "garmin-workbench", "tools": {{n: {{}} for n in names}}}}]}}}}), flush=True)
''')
            # Exercise a real child process without requiring POSIX shebangs.
            popen = subprocess.Popen

            def launch(command, **kwargs):
                self.assertEqual(command, [str(executable), "app-server"])
                return popen([sys.executable, *command], **kwargs)

            with patch("garmin_archive.install.shutil.which", return_value=str(executable)), \
                    patch("garmin_archive.install.subprocess.Popen", side_effect=launch):
                self.assertEqual(set(install.verify_codex_discovery()), install.REQUIRED_TOOLS)


class SecretFileTest(unittest.TestCase):
    def setUp(self):
        self.stack = contextlib.ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.source = self.root / "provider-secret"
        self.source.write_text("synthetic-private-key\n")
        self.source.chmod(0o600)
        self.destination = self.root / "config" / "key"
        self.archive = self.root / "archive"
        self.stack.enter_context(patch("garmin_archive.install.DEFAULT_API_KEY_FILE", self.destination))
        # Windows needs USERPROFILE to resolve Path.home(); isolate both native
        # home conventions while still clearing credentials and other settings.
        self.stack.enter_context(patch.dict(os.environ, {
            "HOME": str(self.root), "USERPROFILE": str(self.root),
        }, clear=True))
        self.stack.enter_context(patch("sys.stdin.isatty", return_value=False))
        self.auth = self.stack.enter_context(patch("garmin_archive.install.PersonalApiAuthenticator"))
        self.auth.return_value.__enter__.return_value.obtain_token.return_value.access_token = "fake-token"
        self.client = self.stack.enter_context(patch("garmin_archive.install.GarminPersonalApiClient"))
        self.sync = self.stack.enter_context(patch("garmin_archive.cli._sync"))
        self.register = self.stack.enter_context(patch("garmin_archive.install.register_codex"))
        self.schedule = self.stack.enter_context(patch("garmin_archive.schedule.configure_schedule"))
        self.output = self.stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
        self.errors = self.stack.enter_context(contextlib.redirect_stderr(io.StringIO()))

    def run_save(self):
        return cli.main(["--data-dir", str(self.archive), "save-key", "--from-file", str(self.source)])

    def test_headless_import_validates_without_sync_archive_client_or_schedule(self):
        log_level = logging.root.manager.disable
        self.assertEqual(self.run_save(), 0)
        self.assertEqual(logging.root.manager.disable, log_level)
        self.auth.return_value.__enter__.return_value.obtain_token.assert_called_once_with("synthetic-private-key")
        self.client.return_value.__enter__.return_value.get_user_profile_settings.assert_called_once()
        self.assertEqual(self.destination.read_text(), "synthetic-private-key\n")
        if os.name == "posix":
            self.assertEqual(self.destination.stat().st_mode & 0o777, 0o600)
            self.assertEqual(self.destination.parent.stat().st_mode & 0o777, 0o700)
        self.assertTrue(self.source.exists())
        self.assertFalse(self.archive.exists())
        self.sync.assert_not_called()
        self.register.assert_not_called()
        self.schedule.assert_not_called()
        self.assertNotIn("synthetic-private-key", self.output.getvalue() + self.errors.getvalue())

    def test_rejected_key_does_not_leak_response_or_save_and_restores_logging(self):
        self.auth.return_value.__enter__.return_value.obtain_token.side_effect = ValueError("synthetic-private-key PRIVATE_BODY")
        log_level = logging.root.manager.disable
        self.assertEqual(self.run_save(), 1)
        self.assertEqual(logging.root.manager.disable, log_level)
        self.assertFalse(self.destination.exists())
        output = self.output.getvalue() + self.errors.getvalue()
        self.assertNotIn("synthetic-private-key", output)
        self.assertNotIn("PRIVATE_BODY", output)
        self.assertIn("not saved", output)

    def test_existing_file_is_preserved_without_authentication(self):
        self.destination.parent.mkdir()
        self.destination.write_text("existing-key")
        self.assertEqual(self.run_save(), 1)
        self.assertEqual(self.destination.read_text(), "existing-key")
        self.auth.assert_not_called()

    def test_malformed_and_missing_secret_sources_fail_before_authentication(self):
        for content in (b"", b"\xff", b"one\ntwo", b"x\x00y", b"x" * 16_385):
            with self.subTest(content_length=len(content)):
                self.source.write_bytes(content)
                self.assertEqual(self.run_save(), 1)
                self.assertFalse(self.destination.exists())
        self.source.unlink()
        self.assertEqual(self.run_save(), 1)
        self.auth.assert_not_called()

    @unittest.skipUnless(os.name == "posix", "POSIX file privacy checks")
    def test_shared_symlink_directory_and_fifo_sources_are_rejected(self):
        self.source.chmod(0o644)
        self.assertEqual(self.run_save(), 1)
        self.source.unlink()
        self.source.symlink_to(self.root / "missing")
        self.assertEqual(self.run_save(), 1)
        self.source.unlink()
        self.source.mkdir()
        self.assertEqual(self.run_save(), 1)
        self.source.rmdir()
        os.mkfifo(self.source, 0o600)
        self.assertEqual(self.run_save(), 1)
        self.auth.assert_not_called()

    def test_dry_run_checks_shape_without_network_or_any_writes(self):
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        self.assertEqual(cli.main(['save-key', '--from-file', str(self.source), '--dry-run']), 0)
        result = __import__('json').loads(self.output.getvalue())
        self.assertEqual(result['authentication'], 'not_attempted')
        self.assertFalse(result['saved'])
        self.assertEqual(before, sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*')))
        self.auth.assert_not_called()
        self.client.assert_not_called()
        self.assertNotIn('synthetic-private-key', self.output.getvalue())

    def test_timeouts_report_phase_and_never_save_secret(self):
        from requests.exceptions import ReadTimeout
        for phase in ('auth', 'profile'):
            with self.subTest(phase=phase):
                self.auth.return_value.__enter__.return_value.obtain_token.side_effect = ReadTimeout('PRIVATE_BODY') if phase == 'auth' else None
                self.client.return_value.__enter__.return_value.get_user_profile_settings.side_effect = ReadTimeout('PRIVATE_BODY')
                self.assertEqual(cli.main(['save-key', '--from-file', str(self.source), '--timeout', '2']), 1)
                self.assertFalse(self.destination.exists())
                self.assertIn('timed out', self.errors.getvalue())
                self.assertIn('Validating Garmin authentication', self.errors.getvalue())
                self.assertNotIn('PRIVATE_BODY', self.errors.getvalue())
                self.auth.assert_called_with(timeout=2)
        self.assertIn('Checking Garmin profile access', self.errors.getvalue())

    def test_agent_guide_client_option_includes_generic_policy_and_handoff(self):
        self.assertEqual(cli.main(['agent-guide', '--client', 'muse']), 0)
        self.assertIn('canonical presentation policy', self.output.getvalue())
        self.assertIn('This handoff does not establish a connection', self.output.getvalue())
        self.assertEqual(self.output.getvalue().count('# Using Garmin Data Workbench'), 1)
        self.auth.assert_not_called()

    def test_live_connection_script_reports_timeout_phase_without_secret_details(self):
        from requests.exceptions import ConnectTimeout
        main = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/check_connection.py'))['main']
        client = self.client.return_value.__enter__.return_value
        client.get_user_profile_settings.side_effect = ConnectTimeout('PRIVATE_BODY')
        previous = logging.root.manager.disable
        with patch.dict(main.__globals__, {'PersonalApiAuthenticator': self.auth,
                                          'GarminPersonalApiClient': self.client,
                                          'resolve_api_key': lambda: 'synthetic-private-key'}):
            self.assertEqual(main(['--timeout', '2']), 1)
        self.assertEqual(logging.root.manager.disable, previous)
        self.assertIn('Checking Garmin profile access', self.errors.getvalue())
        self.assertIn('Connection check timed out', self.errors.getvalue())
        self.assertNotIn('PRIVATE_BODY', self.errors.getvalue())
        self.assertNotIn('synthetic-private-key', self.errors.getvalue())

    def test_non_tty_installer_points_to_secret_facility_without_prompting(self):
        with patch("garmin_archive.install.resolve_api_key", side_effect=GarminPersonalApiError("missing")), \
                patch("garmin_archive.install.getpass.getpass") as prompt:
            with self.assertRaisesRegex(RuntimeError, "save-key --from-file"):
                install.ensure_key()
        prompt.assert_not_called()

    def test_hidden_prompt_never_falls_back_to_echoed_input(self):
        def unsafe_prompt(*args):
            warnings.warn("cannot hide input", install.getpass.GetPassWarning)
            self.fail("Prompt continued after losing hidden entry")
        with patch("garmin_archive.install.resolve_api_key", side_effect=GarminPersonalApiError("missing")), \
                patch("sys.stdin.isatty", return_value=True), \
                patch("garmin_archive.install.getpass.getpass", side_effect=unsafe_prompt):
            with self.assertRaisesRegex(RuntimeError, "Hidden key entry is unavailable"):
                install.ensure_key()
        self.auth.assert_not_called()

    def test_muse_handoff_uses_same_host_cli_and_selected_archive(self):
        self.assertEqual(cli.main(["--data-dir", str(self.archive), "assistant-guide", "--client", "muse"]), 0)
        output = self.output.getvalue()
        # Windows temp paths may use an 8.3 alias; handoffs use canonical paths.
        self.assertIn(str(self.archive.resolve()), output)
        self.assertIn("day YYYY-MM-DD", output)
        self.assertIn("trend sleep_duration", output)
        self.assertIn("no key or MCP client", output)
        self.assertIn("does not establish a connection", output)
        self.assertFalse(self.archive.exists())
        self.auth.assert_not_called()


if __name__ == "__main__":
    unittest.main()

"""Command examples preserve paths across the supported native shells."""
from __future__ import annotations

import contextlib
import io
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from garmin_archive.platforms import installed_executable, shell_command


class PlatformTest(unittest.TestCase):
    def test_entry_points_use_the_current_environment_and_native_suffix(self):
        for platform, suffix in (("darwin", ""), ("linux", ""), ("win32", ".exe")):
            with self.subTest(platform=platform):
                self.assertEqual(installed_executable("garmin-archive-mcp", platform=platform),
                                 Path(sys.executable).parent / f"garmin-archive-mcp{suffix}")

    def test_posix_examples_preserve_spaces_quotes_and_shell_metacharacters(self):
        arguments = ["/home/Zoë's tools/garmin-archive", "--data-dir", "/data/archive $HOME; & #"]
        self.assertEqual(shlex.split(shell_command(arguments, platform="linux")), arguments)

    def test_windows_examples_use_powershell_literals_and_call_operator(self):
        arguments = [r"C:\Users\Zoë's tools\garmin-archive.exe", "--data-dir", r"C:\data\$HOME; & #"]
        self.assertEqual(shell_command(arguments, platform="win32"),
                         "& 'C:\\Users\\Zoë''s tools\\garmin-archive.exe' '--data-dir' 'C:\\data\\$HOME; & #'")

    def test_example_runs_in_native_shell_without_changing_arguments(self):
        shell = shutil.which("powershell.exe" if sys.platform == "win32" else "sh")
        if not shell:
            self.skipTest("Native shell is unavailable")
        with tempfile.TemporaryDirectory(prefix="garmin shell ") as temp:
            script = Path(temp) / "echo arguments.py"
            script.write_text("import json, sys; print(json.dumps(sys.argv[1:]))", encoding="utf-8")
            arguments = ["Zoë's archive", "$HOME; & # literal"]
            command = shell_command([sys.executable, str(script), *arguments])
            options = ["-NoProfile", "-NonInteractive", "-Command"] if sys.platform == "win32" else ["-c"]
            result = subprocess.run([shell, *options, command], capture_output=True, text=True,
                                    encoding="utf-8", check=True, timeout=15)
            self.assertEqual(json.loads(result.stdout), arguments)

    def test_windows_handoffs_and_generic_connection_use_powershell(self):
        from garmin_archive import cli, install
        from garmin_archive.archive import Archive

        with tempfile.TemporaryDirectory() as temp:
            data_dir = Path(temp) / "Zoë's archive $HOME"
            with patch("garmin_archive.platforms.sys.platform", "win32"):
                guide = install.assistant_guide("muse", data_dir=data_dir)
                self.assertIn("PowerShell", guide)
                self.assertIn("`& '", guide)
                self.assertIn("Zoë''s archive $HOME", guide)
                self.assertIn("garmin-archive.exe", guide)
                self.assertFalse(data_dir.exists())

                output = io.StringIO()
                with contextlib.closing(Archive(data_dir)) as archive:
                    with patch("garmin_archive.install.probe_server"), contextlib.redirect_stdout(output):
                        self.assertEqual(cli._connect(archive, "other"), 2)
                self.assertIn("PowerShell syntax", output.getvalue())
                self.assertIn("launch: & '", output.getvalue())

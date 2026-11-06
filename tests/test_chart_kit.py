"""Offline export contract and hard complexity budgets for editable chart starters."""
import contextlib
import io
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from garmin_archive import cli
from garmin_archive.chart_kit import write_chart_kit

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "src/garmin_archive/ui"


class ChartKitTests(unittest.TestCase):
    def test_receipt_brand_private_and_no_archive(self):
        with tempfile.TemporaryDirectory() as parent:
            for host, starter, reference in (("grok", "starter.canvas.tsx", "reference.canvas.tsx"), ("muse", "starter.html", "reference.js")):
                output = Path(parent) / host
                stream = io.StringIO()
                with patch.object(cli, "Archive", side_effect=AssertionError("archive opened")), contextlib.redirect_stdout(stream):
                    self.assertEqual(cli.main(["--data-dir", str(Path(parent) / "missing"), "chart-kit",
                                               "--host", host, "--output", str(output)]), 0)
                receipt = json.loads(stream.getvalue())
                self.assertEqual(receipt["host"], host)
                self.assertEqual(receipt["output_dir"], str(output))
                self.assertEqual(set(receipt["paths"]), {"RULES.md", starter, reference, "brand.json", "logo.svg"})
                self.assertEqual(len(receipt["next_steps"]), 2)
                self.assertFalse((Path(parent) / "missing").exists())
                brand = json.loads((output / "brand.json").read_text())
                self.assertEqual(brand["assets"], {"logo_svg": "logo.svg"})
                self.assertIn("<svg", (output / "logo.svg").read_text())
                source = (output / starter).read_text()
                self.assertIn("SAMPLE DATA, REPLACE", source)
                self.assertIn("Invented observations", source)
                self.assertIn("Example volume", source)
                self.assertNotIn("__BRAND", source)
                self.assertNotIn("__LOGO", source)
                self.assertIn(brand["colors"]["primary"], source)
                self.assertIn(brand["dark_colors"]["primary"], source)
                for color in brand["colors"]["series"] + brand["dark_colors"]["series"]:
                    self.assertIn(color, source)
                # The 14.6 KB budget is on the template; a kit adds brand tokens and the logo.
                self.assertLessEqual(len(source.encode()), 16_000)
                self.assertLessEqual(len(source.splitlines()), 250)
                if os.name != "nt":
                    self.assertEqual(output.stat().st_mode & 0o777, 0o700)
                    for name in receipt["paths"]:
                        self.assertEqual((output / name).stat().st_mode & 0o777, 0o600)
                before = {p.name: p.read_bytes() for p in output.iterdir()}
                with self.assertRaises(FileExistsError):
                    write_chart_kit(output, host)
                self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_existing_file_symlink_and_cli_error(self):
        with tempfile.TemporaryDirectory() as parent:
            output = Path(parent) / "file"
            output.write_text("preserve")
            with self.assertRaises(FileExistsError):
                write_chart_kit(output, "muse")
            self.assertEqual(output.read_text(), "preserve")
            if os.name != "nt":
                link = Path(parent) / "link"
                link.symlink_to(output)
                with self.assertRaises(FileExistsError):
                    write_chart_kit(link, "grok")
            error = io.StringIO()
            with contextlib.redirect_stderr(error):
                self.assertEqual(cli.main(["chart-kit", "--host", "muse", "--output", str(output)]), 1)
            self.assertEqual(json.loads(error.getvalue())["error"]["code"], "output_error")
            with self.assertRaises(ValueError):
                write_chart_kit(Path(parent) / "bad", "unknown")

    def test_source_contract_and_size_budgets(self):
        source = (UI / "starter.canvas.tsx").read_text()
        self.assertEqual(re.findall(r'^import \{ (.*?) \} from "grok/canvas";', source, re.M),
                         ["Page, Section, useState, useGrokTheme"])
        self.assertNotRegex(source, r'<(?:p|h[1-6]|table|ul|pre|rect)\b')
        self.assertNotRegex(source, r'outerHTML|innerHTML|prefers-color-scheme')
        self.assertIn("background: theme.bg.base", source)
        self.assertIn("fontFamily: theme.font.family", source)
        self.assertIn("theme.motion", source)
        muse = (UI / "starter.html").read_text()
        self.assertNotRegex(muse, r'<(?:form|iframe)\b|(?:src|href)=[\"\']https?://|\bfetch\(')
        for name in ("starter.canvas.tsx", "starter.html"):
            # Match the exporter's UTF-8/universal-newline read, independent of Git's CRLF checkout setting.
            content = (UI / name).read_text(encoding="utf-8").encode("utf-8")
            self.assertLessEqual(len(content), 14_600, name)
            self.assertLessEqual(len(content.splitlines()), 250, name)
        for name, limit in (("src/garmin_archive/ui/chart_rules.md", 100), ("tests/test_chart_kit.py", 120),
                            ("scripts/test_chart_starters.mjs", 220)):
            self.assertLessEqual(len((ROOT / name).read_bytes().splitlines()), limit, name)


if __name__ == "__main__":
    unittest.main()

"""Offline exact-source staging, size bounds and private handoff artifacts."""
import hashlib
import json
import os
import re
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from garmin_archive import grok_handoff as handoff
from garmin_archive.archive import Archive
from garmin_archive.queries import open_archive
from garmin_archive.widgets import recovery_grok_canvas, recovery_widget_snapshot


def sha(source):
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def apply_exact(current, step):
    """Independent small model of exact-once native edits and atomic batches."""
    args = step["arguments"]
    if step["tool"] == "WriteCanvas":
        return args["contents"]
    following = current
    for edit in args.get("edits", [args]):
        old = edit["old_string"]
        at = following.find(old)
        if at < 0 or following.find(old, at + 1) >= 0:
            raise ValueError("Exact-once source match failed")
        following = following[:at] + edit["new_string"] + following[at + len(old):]
    return following


class GrokHandoffTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name).resolve()
        archive = Archive(cls.root / "invented-archive")
        try:
            archive.mark_synthetic("grok-handoff-test", 42, "2026-04-01T00:00:00+00:00")
            for i in range(90):
                day = (date(2026, 1, 1) + timedelta(days=i)).isoformat()
                total = 0 if i == 1 else 25200 + i * 17
                archive.save_daily("sleep", day, {"calendarDate": day, "sleepTimeSeconds": total,
                    "deepSleepSeconds": total // 4, "lightSleepSeconds": total - total // 4,
                    "remSleepSeconds": 0, "unmeasurableSleepSeconds": 0, "awakeSleepSeconds": i * 10,
                    "sleepScores": {"overall": {"value": 60 + i % 35}}, "sleepNeed": {"actual": 480},
                    "sleepStartTimestampLocal": day + "T22:30:00"})
                archive.save_daily("hrv", day, {"hrvSummary": {"lastNightAvg": 45 + i % 15}})
                archive.save_daily("heart_rate", day, {"restingHeartRate": 50 + i % 8})
                archive.save_daily("body_battery", day, [{"date": day, "charged": i % 70}])
            archive.mark_error("hrv", "2026-01-03", "Invented refresh failure")
        finally:
            archive.close()
        cls.sources = {}
        with open_archive(cls.root / "invented-archive") as db:
            for days in (2, 14, 90):
                end = (date(2026, 1, 1) + timedelta(days=days - 1)).isoformat()
                cls.sources[days] = recovery_grok_canvas(recovery_widget_snapshot(db, "2026-01-01", end))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_two_fourteen_ninety_day_delivery_reconstructs_exact_bytes(self):
        for days, source in self.sources.items():
            with self.subTest(days=days):
                plan = handoff.build_handoff_plan(source, "Saved recovery")
                self.assertEqual(plan, handoff.build_handoff_plan(source, "Saved recovery"))
                self.assertEqual(plan["expected_source"], {"sha256": sha(source),
                    "bytes": len(source.encode("utf-8")), "lines": len(source.splitlines()), "encoding": "utf-8"})
                current = None
                for i, step in enumerate(plan["steps"]):
                    self.assertEqual(step["number"], i + 1)
                    self.assertEqual(step["before_sha256"], None if current is None else sha(current))
                    if i:
                        self.assertEqual(current.count(handoff.ANCHOR), 1)
                        self.assertEqual(current.count("export default function App()"), 1)
                        self.assertIn(handoff.PLACEHOLDER, current)
                        self.assertFalse(step["arguments"]["replace_all"])
                    current = apply_exact(current, step)
                    self.assertEqual(step["after_sha256"], sha(current))
                self.assertEqual(current.encode("utf-8"), source.encode("utf-8"))
                self.assertNotIn(handoff.ANCHOR, current)
                self.assertEqual(current.count("export default function App()"), 1)

    def test_every_argument_is_bounded_with_worst_reserved_canvas_id(self):
        canvas_id = "x" * (handoff.MAX_CANVAS_ID_JSON_BYTES - 2)
        for source in self.sources.values():
            plan = handoff.build_handoff_plan(source, "Recovery 🍞")
            for step in [*plan["steps"], *plan["verification_steps"], plan["readback"]]:
                args = handoff.bind_canvas_id(step, canvas_id)
                actual = len(json.dumps(args, ensure_ascii=True, separators=(",", ":")).encode("ascii"))
                self.assertLessEqual(actual, 12000)
                if "reserved_arguments_json_bytes" in step:
                    self.assertEqual(actual, step["reserved_arguments_json_bytes"])
                if "canvas_id" in step["arguments"]:
                    self.assertEqual(step["arguments"]["canvas_id"], handoff.CANVAS_ID)
            for invalid in ("", handoff.CANVAS_ID, "x" * 511, "🍞" * 100, None):
                with self.assertRaises(ValueError):
                    handoff.bind_canvas_id(plan["steps"][1], invalid)

    def test_atomic_verification_covers_every_byte_and_restores_exact_source(self):
        for source in self.sources.values():
            plan = handoff.build_handoff_plan(source, "Recovery")
            current, prior_end, fragments = source, 0, []
            for i, step in enumerate(plan["verification_steps"]):
                self.assertEqual(step["number"], len(plan["steps"]) + i + 1)
                self.assertEqual(step["before_sha256"], sha(current))
                if step["label"] == "verify-source-fragment":
                    start, end = step["start_character"], step["end_character"]
                    fragment = source[start:end]
                    fragments.append((start, end))
                    self.assertEqual(start, 0 if prior_end == 0 else prior_end - 256)
                    self.assertGreater(end, prior_end)
                    self.assertEqual(step["start_byte"], len(source[:start].encode("utf-8")))
                    self.assertEqual(step["end_byte"], len(source[:end].encode("utf-8")))
                    self.assertEqual(source.find(fragment), start)
                    self.assertEqual(source.find(fragment, start + 1), -1)
                    edits = step["arguments"]["edits"]
                    self.assertEqual(len(edits), 3)
                    self.assertEqual(edits[0]["old_string"], fragment)
                    self.assertEqual(edits[0]["new_string"], handoff.VERIFY_SLOT)
                    self.assertNotIn(handoff.VERIFY_SLOT, current)
                    self.assertEqual(edits[0]["new_string"], edits[1]["old_string"])
                    self.assertEqual(edits[1]["new_string"], fragment)
                    for edit in edits:
                        self.assertNotEqual(edit["old_string"], edit["new_string"])
                        self.assertFalse(edit["replace_all"])
                    prior_end = end
                following = apply_exact(current, step)
                self.assertNotEqual(following, current)  # Native no_change never needed.
                current = following
                self.assertEqual(step["after_sha256"], sha(current))
                self.assertTrue(current.startswith(source))  # Temporary marker is only a suffix.
            self.assertEqual(fragments[-1][1], len(source))
            self.assertEqual(current.encode("utf-8"), source.encode("utf-8"))
            self.assertNotIn(handoff.VERIFY_MARKER_PREFIX, current)

    def test_verification_rejects_changed_fragments_but_requires_readback_for_extra_source(self):
        source = self.sources[14]
        plan = handoff.build_handoff_plan(source, "Recovery")
        current = source
        for step in plan["verification_steps"]:
            if step["label"] == "verify-source-fragment":
                at = step["start_character"]
                changed = current[:at] + "\x00" + current[at + 1:]
                with self.assertRaisesRegex(ValueError, "Exact-once"):
                    apply_exact(changed, step)
            current = apply_exact(current, step)
        # Fragments are evidence of expected content, not a remote file digest.
        current = "// foreign extra content\n" + source
        for step in plan["verification_steps"]:
            current = apply_exact(current, step)
        self.assertNotEqual(current, source)
        self.assertIn("exact full ReadCanvas", plan["verification_meaning"])

    def test_atomic_batch_failure_does_not_advance_the_checkpoint(self):
        source = self.sources[2]
        verification = handoff.build_handoff_plan(source, "Recovery")["verification_steps"]
        current = apply_exact(source, verification[0])
        step = json.loads(json.dumps(verification[1]))
        step["arguments"]["edits"][2]["old_string"] = "absent marker"
        before = current
        with self.assertRaisesRegex(ValueError, "Exact-once"):
            apply_exact(current, step)
        self.assertEqual(current, before)

    def test_invalid_source_and_unexpected_anchors_fail_closed(self):
        source = self.sources[14]
        invalid = ["", "export default function App() {}", source + "// added\n",
                   source.replace("function Lane(", "function OtherLane("),
                   source.replace("const transportPart0 = ", "const transportPart1 = ", 1),
                   source.replace("const transportPart0 = ", "const transportPart00 = ", 1),
                   source.replace('].join("")));', '].join(" ")));', 1),
                   source.replace("\n", "\r\n"), handoff.ANCHOR + source]
        for value in invalid:
            with self.subTest(kind=value[:50]):
                with self.assertRaises(ValueError):
                    handoff.build_handoff_plan(value, "Recovery")
        for title in ("", " ", "a" * 1024, None):
            with self.assertRaises(ValueError):
                handoff.build_handoff_plan(source, title)
        with patch.object(handoff, "MAX_ARGUMENT_BYTES", 800):
            with self.assertRaisesRegex(ValueError, "argument bound"):
                handoff.build_handoff_plan(source, "Recovery")
        with patch.object(handoff, "MAX_SOURCE_BYTES", 100):
            with self.assertRaisesRegex(ValueError, "project bound"):
                handoff.build_handoff_plan(source, "Recovery")

    def test_transport_and_future_code_sections_fail_closed_when_oversized(self):
        source = self.sources[14]
        declaration = re.search(r'const transportPart0 = (".*");\n', source)
        oversized = source[:declaration.start(1)] + json.dumps("x" * 2049) + source[declaration.end(1):]
        with self.assertRaisesRegex(ValueError, "2048 ASCII"):
            handoff.build_handoff_plan(oversized, "Recovery")
        template = (Path(handoff.__file__).with_name("ui") / "recovery.canvas.tsx").read_text()
        expansion = "function Explorer() {\n  // " + "x" * 12000 + "\n"
        future_source = source.replace("function Explorer() {", expansion)
        future_template = template.replace("function Explorer() {", expansion)
        with patch.object(Path, "read_text", return_value=future_template):
            with self.assertRaisesRegex(ValueError, "explorer.*argument bound"):
                handoff.build_handoff_plan(future_source, "Recovery")

    def test_private_exclusive_files_and_complete_manifest(self):
        with tempfile.TemporaryDirectory(dir=self.root) as folder:
            target = Path(folder) / "handoff"
            result = handoff.write_handoff(target, self.sources[14], "Recovery")
            self.assertEqual(result["output_dir"], str(target))
            self.assertEqual((target / "source.canvas.tsx").read_bytes(), self.sources[14].encode("utf-8"))
            plan = json.loads((target / "plan.json").read_text())
            self.assertFalse((target / "plan.pending.json").exists())
            for step in [*plan["steps"], *plan["verification_steps"], plan["readback"]]:
                self.assertEqual(json.loads((target / step["arguments_file"]).read_text()), step["arguments"])
            before = {p.name: p.read_bytes() for p in target.iterdir()}
            with self.assertRaises(FileExistsError):
                handoff.write_handoff(target, self.sources[2], "Other")
            self.assertEqual(before, {p.name: p.read_bytes() for p in target.iterdir()})
            if os.name == "posix":
                self.assertEqual(target.stat().st_mode & 0o777, 0o700)
                for path in target.iterdir():
                    self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_no_directory_is_created_for_invalid_source_or_missing_parent(self):
        with tempfile.TemporaryDirectory(dir=self.root) as folder:
            target = Path(folder) / "handoff"
            with self.assertRaises(ValueError):
                handoff.write_handoff(target, "not source", "Recovery")
            self.assertFalse(target.exists())
            with self.assertRaises(NotADirectoryError):
                handoff.write_handoff(target / "child", self.sources[2], "Recovery")
            self.assertFalse(target.exists())

    def test_write_failure_never_publishes_partial_manifest(self):
        with tempfile.TemporaryDirectory(dir=self.root) as folder:
            target = Path(folder) / "handoff"
            with patch.object(handoff.os, "link", side_effect=OSError("Invented publish failure")):
                with self.assertRaisesRegex(OSError, "Invented"):
                    handoff.write_handoff(target, self.sources[2], "Recovery")
            self.assertFalse((target / "plan.json").exists())
            self.assertTrue((target / "source.canvas.tsx").exists())

    def test_symlink_destination_and_ancestor_are_not_followed(self):
        with tempfile.TemporaryDirectory(dir=self.root) as folder:
            parent = Path(folder)
            other = parent / "other"
            other.mkdir()
            link = parent / "link"
            try:
                link.symlink_to(other, target_is_directory=True)
            except (OSError, NotImplementedError):
                self.skipTest("Creating symlinks is unavailable on this host")
            with self.assertRaises(FileExistsError):
                handoff.write_handoff(link, self.sources[2], "Recovery")
            with self.assertRaisesRegex(ValueError, "symbolic links"):
                handoff.write_handoff(link / "handoff", self.sources[2], "Recovery")
            self.assertEqual(list(other.iterdir()), [])


if __name__ == "__main__":
    unittest.main()

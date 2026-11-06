"""Native Grok source export: shared data, bounded bytes and private delivery."""
import contextlib
import copy
import io
import json
import math
import os
import re
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from garmin_archive import widgets
from garmin_archive.archive import Archive
from garmin_archive.cli import main
from garmin_archive.grok_transport import pack_grok_snapshot, project_grok_snapshot
from garmin_archive.queries import open_archive
from garmin_archive.recovery import compare_sleep_recovery, get_sleep_recovery
from test_recovery import seed


def embedded_transport_parts(source):
    template = (Path(widgets.__file__).with_name("ui") / "recovery.canvas.tsx").read_text(encoding="utf-8")
    before, after = template.split('const snapshot = decodeTransport(/*__RECOVERY_SNAPSHOT__*/);')
    assert source.startswith(before) and source.endswith(after)
    block = source[len(before):len(source) - len(after) if after else None]
    lines = block.splitlines()
    parts, names = [], []
    for i, line in enumerate(lines[:-1]):
        match = re.fullmatch(r'const (transportPart\d+) = (".*");', line)
        assert match and match[1] == f'transportPart{i}'
        part = json.loads(match[2])
        assert isinstance(part, str) and 0 < len(part) <= 2048 and part.isascii()
        names.append(match[1])
        parts.append(part)
    assert parts
    assert lines[-1] == 'const snapshot = decodeTransport(JSON.parse([' + ','.join(names) + '].join("")));'
    return parts


def embedded_snapshot(source):
    packet = json.loads(''.join(embedded_transport_parts(source)))
    assert packet["codec_version"] == 1 and packet["schema_version"] == 1
    # Independent test decoder. Assertions below compare each decoded field to
    # canonical query output, not just pack/unpack agreement.
    def text(index):
        return None if index is None else packet["strings"][index]

    def period(values):
        first, last, mean, count, requested, oldest, newest = values
        return {"from": text(first), "to": text(last), "mean_of_available_days": mean,
                "coverage": {"days_with_value": count, "requested_days": requested},
                "freshness": {"oldest_available_fetch": text(oldest), "newest_available_fetch": text(newest)}}

    nights = []
    for day, status, complete, fetched, timing, values in packet["nights"]:
        nights.append({"day": text(day), "status": text(status), "stages_complete": complete, "fetched_at": text(fetched),
            "timing": dict(zip(("start_utc", "end_utc", "start_local", "end_local"), map(text, timing))),
            "values": dict(zip(("sleep_duration", "sleep_need", "sleep_awake", "sleep_score", "sleep_deep",
                                "sleep_light", "sleep_rem", "sleep_unmeasurable"), values))})
    trends = {metric: {"points": [{"day": text(day), "value": value, "status": text(status), "fetched_at": text(fetched)}
                                   for day, value, status, fetched in points]}
              for metric, points in zip(("overnight_hrv", "resting_heart_rate", "body_battery_charged"), packet["trends"])}
    comparisons = None
    if packet["comparison"] is not None:
        comparisons = {"metrics": {}}
        for metric, (baseline, current, status, difference, warnings) in zip(
                ("sleep_duration", "overnight_hrv", "resting_heart_rate", "sleep_score", "body_battery_charged"), packet["comparison"]):
            comparisons["metrics"][metric] = {"baseline": period(baseline), "period": period(current),
                "change": {"status": text(status), "mean_difference": difference}, "warnings": list(map(text, warnings))}
    return {"schema_version": packet["schema_version"], "report": {"from": text(packet["range"][0]),
        "to": text(packet["range"][1]), "archive_provenance": packet["provenance"],
        "sleep": {"nights": nights}, "trends": trends}, "comparison": comparisons}


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

    def assert_canonical_fields(self, decoded, canonical):
        self.assertEqual(decoded["schema_version"], canonical["schema_version"])
        report, original = decoded["report"], canonical["report"]
        for key in ("from", "to", "archive_provenance"):
            self.assertEqual(report[key], original[key])
        self.assertEqual(len(report["sleep"]["nights"]), len(original["sleep"]["nights"]))
        for night, source in zip(report["sleep"]["nights"], original["sleep"]["nights"]):
            for key in ("day", "status", "stages_complete", "fetched_at", "timing"):
                self.assertEqual(night[key], source[key])
            self.assertEqual(set(night["values"]), {"sleep_duration", "sleep_need", "sleep_awake", "sleep_score",
                "sleep_deep", "sleep_light", "sleep_rem", "sleep_unmeasurable"})
            for metric, value in night["values"].items():
                self.assertEqual(value, source["values"][metric])
                self.assertIs(type(value), type(source["values"][metric]))
        self.assertEqual(set(report["trends"]), {"overnight_hrv", "resting_heart_rate", "body_battery_charged"})
        for metric, trend in report["trends"].items():
            self.assertEqual(len(trend["points"]), len(original["trends"][metric]["points"]))
            for point, source in zip(trend["points"], original["trends"][metric]["points"]):
                self.assertEqual(point, {key: source[key] for key in ("day", "value", "status", "fetched_at")})
        if canonical["comparison"] is None:
            self.assertIsNone(decoded["comparison"])
        else:
            self.assertEqual(set(decoded["comparison"]["metrics"]), set(canonical["comparison"]["metrics"]))
            for metric, comparison in decoded["comparison"]["metrics"].items():
                source = canonical["comparison"]["metrics"][metric]
                self.assertEqual(comparison["warnings"], source["warnings"])
                self.assertEqual(comparison["change"], {key: source["change"][key] for key in ("status", "mean_difference")})
                for name in ("baseline", "period"):
                    for key in ("from", "to", "mean_of_available_days", "freshness"):
                        self.assertEqual(comparison[name][key], source[name][key])
                    self.assertEqual(comparison[name]["coverage"], {key: source[name]["coverage"][key]
                        for key in ("days_with_value", "requested_days")})

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
            self.assert_canonical_fields(payload, {"schema_version": 1,
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
        self.assert_canonical_fields(embedded_snapshot(source), payload)
        self.assertNotIn('</script><script>alert', source)
        self.assertNotIn("\u2028", source)
        self.assertNotIn("\u2029", source)
        self.assertIn("\\u003c", source)
        self.assertIn("\\u0026", source)
        payload["report"]["archive_provenance"]["invalid"] = math.nan
        with self.assertRaises(ValueError):
            widgets.recovery_grok_canvas(payload)

    def test_escaped_data_survives_a_split_inside_unicode_escape(self):
        with open_archive(self.archive) as db:
            canonical = widgets.recovery_widget_snapshot(db, "2026-01-01", "2026-01-04")
        dangerous = '\u2028\u2029🍞</script><script>bad()</script> " \\ \n ` ${bad()}'
        provenance = canonical["report"]["archive_provenance"]
        provenance["freshness_meaning"] = dangerous
        initial = ''.join(embedded_transport_parts(widgets.recovery_grok_canvas(canonical)))
        # Position the first six-character JSON escape three characters before a
        # real 2048-character boundary, rather than relying on a lucky fixture.
        padding = (2048 - 3 - initial.index('\\u2028') % 2048) % 2048
        provenance["freshness_meaning"] = 'A' * padding + dangerous
        source = widgets.recovery_grok_canvas(canonical)
        parts = embedded_transport_parts(source)
        self.assertTrue(any(left.endswith('\\u2') and right.startswith('028')
                            for left, right in zip(parts, parts[1:])))
        self.assertEqual(''.join(parts).count('\\u2028'), 1)
        self.assertNotIn('</script>', source)
        decoded = embedded_snapshot(source)
        self.assertEqual(decoded["report"]["archive_provenance"]["freshness_meaning"], 'A' * padding + dangerous)
        self.assert_canonical_fields(decoded, canonical)

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

    def test_packing_is_versioned_deterministic_and_preserves_independent_fields(self):
        with open_archive(self.archive) as db:
            canonical = widgets.recovery_widget_snapshot(db, "2026-01-01", "2026-01-04")
        # Deliberately distinct values/times catch accidental cross-field reuse.
        first = canonical["report"]["sleep"]["nights"][0]
        first["values"].update(sleep_deep=0, sleep_light=23000, sleep_rem=None, sleep_unmeasurable=4000)
        first["stages_complete"] = False
        first["timing"] = {"start_utc": None, "end_utc": "2026-01-02T06:00:00+00:00",
                           "start_local": "2026-01-01T22:00:00-08:00", "end_local": "2026-01-02T06:00:00"}
        canonical["report"]["trends"]["overnight_hrv"]["points"][0]["fetched_at"] = "2026-01-05T06:07:08+00:00"
        canonical["comparison"]["metrics"]["sleep_score"]["warnings"].append("future_unknown_warning")
        before = copy.deepcopy(canonical)
        packet = pack_grok_snapshot(canonical)
        self.assertEqual(packet["codec_version"], 1)
        self.assertEqual(packet["range"][0], 0)
        self.assertEqual(packet["strings"][0], "2026-01-01")
        self.assertEqual(packet, pack_grok_snapshot(canonical))
        self.assertEqual(canonical, before)
        self.assert_canonical_fields(project_grok_snapshot(canonical), canonical)
        self.assert_canonical_fields(embedded_snapshot(widgets.recovery_grok_canvas(canonical)), canonical)
        self.assertLess(len(json.dumps(packet)), len(json.dumps(canonical)))
        canonical["schema_version"] = 2
        with self.assertRaisesRegex(ValueError, "Unsupported recovery snapshot version"):
            pack_grok_snapshot(canonical)

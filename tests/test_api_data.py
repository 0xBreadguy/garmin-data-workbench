"""Full Personal API coverage with synthetic payloads and an offline HTTP session."""
from __future__ import annotations

import contextlib
import io
import json
import re
import tempfile
import unittest
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import requests
from garmin_personal_api import GarminPersonalApiClient

from garmin_archive.api_data import (api_catalog, contract, field_schema, response_schema,
                                     source_data, source_series, snapshot_coverage)
from garmin_archive.archive import Archive
from garmin_archive.cli import main
from garmin_archive.queries import get_day, get_trend, open_archive
from garmin_archive.sleep import get_sleep
from garmin_archive.sources import DAILY_SOURCES, SOURCES
from garmin_archive.sync import sync
from test_archive import activity_zip

DAY = "2026-01-01"


class OfflineSession:
    def __init__(self, source_payloads=None):
        self.calls = []
        self.payloads = {}
        self.fail = None
        self.source_payloads = source_payloads or {}

    def get(self, url, *, params=None, headers=None, timeout=None):
        path = urlparse(url).path
        # Match the documented contract, rather than accepting any URL that
        # the implementation happens to request.
        template = next((key for key in contract()["responses"]
            if re.fullmatch(re.sub(r"\{[^}]+\}", "[^/]+", key), path)), None)
        if template is None:
            raise AssertionError(f"Undocumented endpoint: {path}")
        self.calls.append((template, params))
        response = requests.Response()
        response.status_code = 404 if template == self.fail else 200
        if template == SOURCES["original"].path:
            response._content = activity_zip()
            return response
        if template == SOURCES["activities"].path:
            payload = ([{"activityId": 42}, {"activityId": 43, "parentId": 42}]
                       if params["start"] == 0 else [])
        elif template == SOURCES["profile"].path:
            payload = {"measurementSystem": "metric", "timeZone": "UTC", "availableTrainingDays": ["MONDAY"]}
        else:
            payload = {"calendarDate": DAY, "newField": {"zero": 0, "false": False, "null": None},
                       "endpointMarker": template}
            schema = contract()["responses"][template].get("application/json", {}).get("schema", {})
            if schema.get("type") == "array":
                payload = [payload]
        if template in self.source_payloads:
            payload = self.source_payloads[template]
            if template == SOURCES["activities"].path and params["start"]:
                payload = []
        self.payloads[path] = payload
        response._content = json.dumps(payload).encode()
        return response


class ApiDataTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.archive = Archive(self.path)
        self.addCleanup(self.archive.close)
        self.db = self.archive.connection

    def test_every_documented_endpoint_is_collected_through_the_official_sdk(self):
        session = OfflineSession()
        client = GarminPersonalApiClient("synthetic", session=session)
        report = sync(self.archive, client, date.fromisoformat(DAY), date.fromisoformat(DAY),
                      today=date(2026, 1, 10), pause=0)
        self.assertFalse(report.errors)
        self.assertEqual(len(contract()["responses"]), 26)
        self.assertEqual({path for path, params in session.calls}, set(contract()["responses"]))
        self.assertEqual(set(DAILY_SOURCES), {r[0] for r in self.db.execute("SELECT dataset FROM daily_data")})
        self.assertEqual(report.activities, 2)
        self.assertEqual(report.decoded, 2)
        self.assertIn("availableTrainingDays", json.loads(self.db.execute(
            "SELECT data_json FROM source_snapshots WHERE dataset='profile'").fetchone()[0]))
        for name in DAILY_SOURCES:
            result = source_data(self.db, name, DAY)
            self.assertEqual(result["status"], "ok", name)
            stored = json.loads(self.db.execute("SELECT data_json FROM daily_data WHERE dataset=?", (name,)).fetchone()[0])
            self.assertEqual(stored, session.payloads[next(path for path in session.payloads
                if re.fullmatch(re.sub(r"\{[^}]+\}", "[^/]+", SOURCES[name].path), path))])
        for name in ("profile", "heart_rate_zones", "activity", "activity_workouts", "activities", "original"):
            result = source_data(self.db, name, activity_id=0 if SOURCES[name].scope == "current" else 43)
            self.assertEqual(result["status"], "ok", name)
        for path, params in session.calls:
            if path == SOURCES["activities"].path:
                self.assertEqual(params["excludeChildren"], "false")
            if path == SOURCES["menstrual_day"].path:
                self.assertEqual(params, {"todayDate": "2026-01-10", "includeAnalysis": "true", "skipbm": "false", "reducedResponse": "false"})
            if path == SOURCES["weight"].path:
                self.assertEqual(params["includeAll"], "true")

    def test_contract_definitions_are_navigable_without_losing_native_metadata(self):
        self.assertEqual(sum(len(s.get("properties", {})) for s in contract()["schemas"].values()), 1587)
        self.assertEqual({s.path for s in SOURCES.values()}, set(contract()["responses"]))
        seen = set()
        def check(dataset, pointer, schema):
            ref = schema.get("$ref")
            if ref:
                if ref in seen:
                    return
                seen.add(ref)
                schema = contract()["schemas"][ref.rsplit("/", 1)[-1]]
            if "allOf" in schema:
                for part in schema["allOf"]:
                    check(dataset, pointer, part)
                return
            result = api_catalog(dataset, pointer)
            fields = result["fields"]
            while result["next_offset"] is not None:
                result = api_catalog(dataset, pointer, offset=result["next_offset"])
                fields += result["fields"]
            self.assertEqual(len(fields), len(schema.get("properties", {})) + int("items" in schema), pointer)
            if "enum" in schema:
                self.assertEqual(result["schema"]["enum"], schema["enum"])
            for key, value in schema.get("properties", {}).items():
                child = pointer + "/" + key.replace("~", "~0").replace("/", "~1")
                self.assertIn(child, {field["pointer"] for field in fields})
                check(dataset, child, value)
            if "items" in schema:
                check(dataset, pointer + "/*", schema["items"])
        for name in SOURCES:
            check(name, "", response_schema(name))
        # Native unit caveats must survive; normalized dashboard labels can be
        # misleading (e.g. poolLength says cm even with another display unit).
        self.assertIn("centimeters", field_schema("activities", "/poolLength")["description"])
        self.assertEqual(api_catalog("activities")["schema"]["type"], "object")
        self.assertIn("minutes", field_schema("sleep", "/dailyNapDTOS/0/napStartTimeOffset")["description"])

    def test_paging_large_arrays_objects_strings_and_unknown_fields(self):
        payload = {"samples": [[i, 60 + i % 10] for i in range(5000)],
                   "a/b~c": {"new": False}, "note": "🍞" * 1200, "empty": [], "null": None, "zero": 0}
        self.archive.save_daily("heart_rate", DAY, payload)
        offset, values = 0, []
        while offset is not None:
            result = source_data(self.db, "heart_rate", DAY, pointer="/samples", limit=77, offset=offset)
            values += [entry["value"] for entry in result["entries"]]
            self.assertLess(len(json.dumps(result).encode()), 50_000)
            offset = result["next_offset"]
        self.assertEqual(values, payload["samples"])
        self.assertIs(source_data(self.db, "heart_rate", DAY, pointer="/a~1b~0c/new")["value"], False)
        self.assertEqual(source_data(self.db, "heart_rate", DAY, pointer="/zero")["value"], 0)
        offset, chunks = 0, []
        while offset is not None:
            result = source_data(self.db, "heart_rate", DAY, pointer="/note", offset=offset)
            chunks.append(result["value"])
            offset = result["next_offset"]
        self.assertEqual("".join(chunks), payload["note"])
        self.assertEqual(source_data(self.db, "heart_rate", DAY, pointer="/null")["field_status"], "null")
        self.assertEqual(source_data(self.db, "heart_rate", DAY, pointer="/absent")["field_status"], "missing")
        self.assertEqual(source_data(self.db, "heart_rate", DAY, pointer="/empty")["total"], 0)
        self.assertTrue(next(e for e in source_data(self.db, "heart_rate", DAY)["entries"] if e.get("key") == "samples")["expand"])

    def test_coordinates_are_an_explicit_opt_in_at_any_depth(self):
        self.archive.save_daily("wellness_activity", DAY,
            [{"startLatitude": 12.5, "nested": {"position_long": 3.2, "distance": 100}}])
        result = source_data(self.db, "wellness_activity", DAY)
        self.assertNotIn("12.5", json.dumps(result))
        self.assertNotIn("position_long", json.dumps(result))
        result = source_data(self.db, "wellness_activity", DAY, include_location=True)
        self.assertEqual(result["entries"][0]["value"]["startLatitude"], 12.5)
        self.assertEqual(source_data(self.db, "wellness_activity", DAY, pointer="/0/startLatitude")["field_status"], "location_omitted")

    def test_failed_refreshes_mask_retained_daily_and_activity_data(self):
        self.archive.save_daily("nutrition", DAY, {"energy": 0})
        self.archive.mark_error("nutrition", DAY, "HTTP 404")
        result = source_data(self.db, "nutrition", DAY)
        self.assertEqual(result["status"], "error")
        self.assertTrue(result["retained_data_available"])
        self.assertNotIn("entries", result)
        self.archive.save_activities(DAY, [{"activityId": 42}])
        self.archive.save_snapshot("activity", "42", {"activityId": 42, "power": 123})
        self.archive.mark_snapshot_error("activity", "42", "HTTP 400")
        self.assertEqual(source_data(self.db, "activity", activity_id=42)["status"], "error")
        self.archive.save_snapshot("activity", "42", {"power": 123})
        self.archive.mark_error("activities", DAY, "HTTP 404")
        self.assertEqual(source_data(self.db, "activity", activity_id=42)["status"], "error")
        self.assertEqual(source_data(self.db, "activities", activity_id=42)["status"], "error")

    def test_native_series_preserve_signed_values_flags_null_and_failure_states(self):
        for day, payload in (("01", {"v": -12}), ("02", {"v": False}), ("03", {"v": None}), ("04", {}), ("05", {"v": 2})):
            self.archive.save_daily("daily_summary_legacy", "2026-01-" + day, payload)
        self.archive.mark_error("daily_summary_legacy", "2026-01-05", "HTTP 404")
        result = source_series(self.db, "daily_summary_legacy", "/v", DAY, "2026-01-06")
        self.assertEqual([p["value"] for p in result["points"]], [-12, False, None, None, None, None])
        self.assertEqual([p["field_status"] for p in result["points"]], ["available", "available", "null", "missing", "unavailable", "unavailable"])
        self.assertNotIn("mean_of_available_days", result)

    def test_old_archive_reads_do_not_migrate_and_next_writer_preserves_data(self):
        self.archive.save_daily("sleep", DAY, {"sleepTimeSeconds": 123})
        self.db.execute("DROP TABLE source_snapshots")
        self.db.commit()
        before = (self.path / "archive.sqlite3").read_bytes()
        with open_archive(self.path) as db:
            self.assertEqual(source_data(db, "profile")["status"], "not_checked")
            self.assertEqual(snapshot_coverage(db), [])
        self.assertEqual(before, (self.path / "archive.sqlite3").read_bytes())
        writer = Archive(self.path)
        writer.close()
        self.assertEqual(source_data(self.db, "sleep", DAY, pointer="/sleepTimeSeconds")["value"], 123)
        self.assertEqual(self.db.execute("PRAGMA user_version").fetchone()[0], 1)

    def test_new_source_errors_are_isolated_resumable_and_never_leak_response_bodies(self):
        session = OfflineSession()
        session.fail = SOURCES["nutrition"].path
        client = GarminPersonalApiClient("synthetic", session=session)
        result = sync(self.archive, client, date.fromisoformat(DAY), date.fromisoformat(DAY), today=date(2026, 1, 10), pause=0)
        self.assertFalse(result.stopped)
        self.assertTrue(result.errors)
        self.assertEqual(source_data(self.db, "nutrition", DAY)["status"], "error")
        self.assertEqual(source_data(self.db, "spo2", DAY)["status"], "ok")
        session.fail = None
        session.calls.clear()
        result = sync(self.archive, client, date.fromisoformat(DAY), date.fromisoformat(DAY), today=date(2026, 1, 10), pause=0)
        self.assertFalse(result.errors)
        self.assertEqual(result.checked, 1)
        self.assertEqual(source_data(self.db, "nutrition", DAY)["status"], "ok")

    def test_cli_catalog_needs_no_archive_and_source_queries_remain_read_only(self):
        missing = self.path / "absent"
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["--data-dir", str(missing), "api-catalog"]), 0)
        self.assertEqual(len(json.loads(out.getvalue())["sources"]), 26)
        self.assertFalse(missing.exists())
        self.archive.save_daily("hydration", DAY, [{"valueInML": 0}])
        before = (self.path / "archive.sqlite3").read_bytes()
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["--data-dir", str(self.path), "source-data", "hydration", "--day", DAY, "--pointer", "/0/valueInML"]), 0)
        self.assertEqual(json.loads(out.getvalue())["value"], 0)
        self.assertEqual(before, (self.path / "archive.sqlite3").read_bytes())
        for pointer in ("not/a/pointer", "/bad~2escape"):
            with self.assertRaises(ValueError):
                source_data(self.db, "sleep", DAY, pointer=pointer)
        for kwargs in ({"limit": 101}, {"offset": -1}):
            with self.assertRaises(ValueError):
                source_data(self.db, "sleep", DAY, **kwargs)

    def test_interpreted_daily_metrics_validate_dates_types_and_sentinels(self):
        self.archive.save_daily("daily_summary_legacy", DAY, {"calendarDate": DAY,
            "hydrationValueInML": 0, "activeKilocalories": 456, "averageStressLevel": -1, "averageSpo2": 101,
            "moderateIntensityMinutes": True})
        result = get_day(self.db, DAY)
        self.assertEqual(result["metrics"]["hydration"]["value"], 0)
        self.assertEqual(result["metrics"]["calories_active"]["value"], 456)
        for metric in ("stress_average", "spo2_average", "intensity_moderate"):
            self.assertIsNone(result["metrics"][metric]["value"])
        self.archive.save_daily("daily_summary_legacy", DAY, {"calendarDate": "2026-01-02", "hydrationValueInML": 100})
        self.assertIsNone(get_trend(self.db, "hydration", DAY, DAY)["points"][0]["value"])

    def test_nap_episodes_use_source_offsets_and_paginate_without_rebuilding_totals(self):
        item = {"calendarDate": DAY, "napTimeSec": 1200, "napStartTimestampGMT": "2026-01-01T22:00:00Z",
                "napEndTimestampGMT": "2026-01-01T22:20:00Z", "napStartTimeOffset": -480,
                "napEndTimeOffset": -480, "napSource": 0, "napFeedback": "RESTORATIVE"}
        self.archive.save_daily("sleep", DAY, {"calendarDate": DAY, "dailyNapDTOS": [item] * 21})
        result = get_sleep(self.db, DAY, DAY)["nights"][0]
        self.assertIsNone(result["values"]["nap_duration"])
        self.assertEqual(result["naps"]["total"], 21)
        self.assertEqual(result["naps"]["next_offset"], 20)
        self.assertEqual(result["naps"]["episodes"][0]["start_local"], "2026-01-01T14:00:00-08:00")
        self.assertEqual(len(source_data(self.db, "sleep", DAY, pointer="/dailyNapDTOS", offset=20)["entries"]), 1)
        self.archive.mark_error("sleep", DAY, "HTTP 404")
        self.assertEqual(get_sleep(self.db, DAY, DAY)["nights"][0]["naps"]["episodes"], [])

    def test_nap_summary_budget_and_invalid_episode_fields_remain_explicit(self):
        for i in range(1, 8):
            day = f"2026-01-{i:02d}"
            self.archive.save_daily("sleep", day, {"calendarDate": day, "dailyNapDTOS": [
                {"calendarDate": day, "napTimeSec": True},
                {"calendarDate": "1999-01-01"}, None,
                {"napStartTimestampGMT": "2026-01-01T14:00:00Z", "napEndTimestampGMT": "2026-01-01T13:00:00Z"},
                *[{}] * 20]})
        result = get_sleep(self.db, DAY, "2026-01-07")
        self.assertEqual(sum(len(n["naps"]["episodes"]) for n in result["nights"]), 100)
        self.assertEqual(result["nights"][-1]["naps"]["next_offset"], 0)
        episodes = result["nights"][0]["naps"]["episodes"]
        self.assertIsNone(episodes[0]["duration"])
        self.assertEqual([e["status"] for e in episodes[1:4]], ["date_mismatch", "invalid", "invalid_window"])

    def test_native_profile_fields_survive_unusable_presentation_defaults(self):
        session = OfflineSession()
        original_get = session.get
        def get(url, **kwargs):
            response = original_get(url, **kwargs)
            if urlparse(url).path == SOURCES["profile"].path:
                response._content = b'{"displayName":"Synthetic example","measurementSystem":null}'
            return response
        session.get = get
        report = sync(self.archive, GarminPersonalApiClient("synthetic", session=session),
                      date.fromisoformat(DAY), date.fromisoformat(DAY), today=date(2026, 1, 10), pause=0)
        self.assertFalse(report.errors)
        self.assertEqual(source_data(self.db, "profile", pointer="/displayName")["value"], "Synthetic example")


if __name__ == "__main__":
    unittest.main()

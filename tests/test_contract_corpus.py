"""Exercise every JSON source through SDK collection and bounded native queries."""
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from garmin_personal_api import GarminPersonalApiClient

from garmin_archive.api_data import source_data
from garmin_archive.archive import Archive
from garmin_archive.queries import open_archive
from garmin_archive.sources import SOURCES
from garmin_archive.sync import sync
from corpus import DAY, contract_payloads
from test_api_data import OfflineSession


def query_arguments(source):
    if source.scope == "daily":
        return {"day": DAY}
    if source.scope == "current":
        return {}
    if source.scope in {"activity", "activity_list"}:
        return {"activity_id": 42}
    raise ValueError(f"Not a JSON source: {source.scope}")


class ContractCorpusTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.archive = Archive(self.path)
        self.addCleanup(self.archive.close)

    def read_node(self, db, name, pointer=""):
        """Reassemble pages like a client, expanding large children by pointer."""
        offset = 0
        pages = []
        while True:
            page = source_data(db, name, pointer=pointer, limit=7, offset=offset,
                               include_location=True, **query_arguments(SOURCES[name]))
            self.assertLess(len(json.dumps(page).encode()), 50_000)
            self.assertEqual(page["status"], "ok")
            self.assertIn(page["field_status"], ("available", "null"))
            pages.append(page)
            if page["next_offset"] is None:
                break
            self.assertGreater(page["next_offset"], offset)
            offset = page["next_offset"]
        kind = pages[0]["type"]
        if kind == "string":
            return "".join(page["value"] for page in pages)
        if kind not in {"object", "array"}:
            return pages[0]["value"]
        entries = [entry for page in pages for entry in page["entries"]]
        self.assertEqual(len(entries), pages[0]["total"])
        values = [self.read_node(db, name, entry["pointer"]) if entry.get("expand")
                  else entry["value"] for entry in entries]
        if kind == "array":
            self.assertEqual([entry["index"] for entry in entries], list(range(len(entries))))
            return values
        self.assertEqual(len({entry["key"] for entry in entries}), len(entries))
        return {entry["key"]: value for entry, value in zip(entries, values)}

    def test_every_json_source_round_trips_through_sdk_archive_and_paged_queries(self):
        payloads = contract_payloads()
        session = OfflineSession(source_payloads=payloads)
        report = sync(self.archive, GarminPersonalApiClient("synthetic", session=session),
                      date.fromisoformat(DAY), date.fromisoformat(DAY),
                      today=date(2026, 1, 10), pause=0)
        self.assertFalse(report.errors)
        self.assertEqual(report.decoded, 1)
        self.assertEqual({path for path, _ in session.calls}, {s.path for s in SOURCES.values()})
        before = self.archive.path.read_bytes()
        with open_archive(self.path) as db:
            for name, source in SOURCES.items():
                if source.scope == "file":
                    continue
                with self.subTest(source=name):
                    expected = payloads[source.path]
                    if source.scope == "activity_list":
                        expected = expected[0]
                    actual = self.read_node(db, name)
                    # JSON text equality also distinguishes false from 0 and
                    # integral floats from integers (Python equality does not).
                    self.assertEqual(json.dumps(actual, sort_keys=True),
                                     json.dumps(expected, sort_keys=True))
                    extension = "/0/synthetic_extension" if isinstance(expected, list) else "/synthetic_extension"
                    escaped = source_data(db, name, pointer=extension + "/a~1b~0c//0",
                                          **query_arguments(source))
                    self.assertEqual(escaped["value"], 0)
        self.assertEqual(self.archive.path.read_bytes(), before)

    def test_unchecked_empty_and_failed_refresh_states_for_every_daily_and_snapshot_source(self):
        payloads = contract_payloads()
        db = self.archive.connection
        for name, source in SOURCES.items():
            if source.scope not in {"daily", "current", "activity"}:
                continue  # Activity-search and FIT state have separate recovery tests.
            with self.subTest(source=name):
                args = query_arguments(source)
                self.assertEqual(source_data(db, name, **args)["status"], "not_checked")
                if source.scope == "daily":
                    save = lambda payload: self.archive.save_daily(name, DAY, payload)
                    fail = lambda: self.archive.mark_error(name, DAY, "Synthetic failed refresh")
                else:
                    key = "current" if source.scope == "current" else "42"
                    save = lambda payload: self.archive.save_snapshot(name, key, payload)
                    fail = lambda: self.archive.mark_snapshot_error(name, key, "Synthetic failed refresh")
                save(payloads[source.path])
                fail()
                failed = source_data(db, name, **args)
                self.assertEqual(failed["status"], "error")
                self.assertTrue(failed["retained_data_available"])
                self.assertNotIn("entries", failed)
                self.assertNotIn("value", failed)
                for empty in (None, {}, []):
                    save(empty)
                    result = source_data(db, name, **args)
                    self.assertEqual(result["status"], "empty")
                    self.assertIsNone(result["error"])
                save(payloads[source.path])
                self.assertEqual(source_data(db, name, **args)["status"], "ok")

"""Synthetic contract-shaped responses; no real account data or network access."""
import json
import tempfile
import unittest
from pathlib import Path

from garmin_archive.api_data import contract, response_schema, source_data
from garmin_archive.archive import Archive
from garmin_archive.sources import SOURCES

DAY = "2026-01-01"


def specimen(schema, ancestors=()):
    """Populate every declared property; stop recursive references at cycles.

    Values test transport and storage, not physiological validity or live API behavior.
    """
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        if name in ancestors:
            return {}
        return specimen(contract()["schemas"][name], (*ancestors, name))
    if "allOf" in schema:
        merged = {}
        for part in schema["allOf"]:
            value = specimen(part, ancestors)
            if isinstance(value, dict):
                merged.update(value)
        return merged
    if "enum" in schema and schema["enum"]:
        return schema["enum"][0]
    kind = schema.get("type")
    if kind == "object" or "properties" in schema:
        return {key: specimen(value, ancestors) for key, value in schema.get("properties", {}).items()}
    if kind == "array":
        return [specimen(schema.get("items", {}), ancestors)]
    return {"string": "synthetic 🍞", "integer": 42, "number": 1.25,
            "boolean": False}.get(kind)


class ContractCorpusTest(unittest.TestCase):
    def test_contract_shaped_responses_survive_archive_and_native_access(self):
        with tempfile.TemporaryDirectory() as temp:
            archive = Archive(Path(temp))
            self.addCleanup(archive.close)
            db = archive.connection
            tested = set()
            for name, source in SOURCES.items():
                if source.scope not in {"daily", "current", "activity"}:
                    continue  # Activity list and original FIT have dedicated tests.
                with self.subTest(source=name):
                    payload = specimen(response_schema(name))
                    if source.scope == "daily":
                        archive.save_daily(name, DAY, payload)
                        row = db.execute("SELECT data_json FROM daily_data WHERE dataset=? AND day=?", (name, DAY)).fetchone()
                        result = source_data(db, name, DAY, include_location=True)
                    else:
                        resource_id = "current" if source.scope == "current" else "42"
                        archive.save_snapshot(name, resource_id, payload)
                        row = db.execute("SELECT data_json FROM source_snapshots WHERE dataset=? AND resource_id=?", (name, resource_id)).fetchone()
                        result = source_data(db, name, activity_id=42 if source.scope == "activity" else 0, include_location=True)
                    self.assertEqual(json.loads(row[0]), payload)
                    self.assertIn(result["status"], ("ok", "empty"))
                    self.assertEqual(result["field_status"], "available")
                    if isinstance(payload, (dict, list)):
                        self.assertEqual(result["total"], len(payload))
                    tested.add(name)
            self.assertEqual(tested, {n for n, s in SOURCES.items() if s.scope in {"daily", "current", "activity"}})

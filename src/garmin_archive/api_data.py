"""Discover and page every Personal API response field in the local archive.

Native fields retain their names, values, units and timestamp representations.
The contract describes fields; it never filters out newly returned fields.
"""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import timedelta
from functools import lru_cache
from importlib.resources import files

from .provenance import archive_provenance
from .queries import parse_day, query_range
from .sources import SOURCES

MAX_PAGE_BYTES = 48_000
INLINE_BYTES = 1_000
MAX_ITEMS = 100


@lru_cache(maxsize=1)
def contract() -> dict:
    return json.loads(files("garmin_archive").joinpath("personal_api_contract.json").read_text())


def _source(dataset):
    if dataset not in SOURCES:
        raise ValueError("Unknown Personal API source; use api-catalog")
    return SOURCES[dataset]


def _bounds(limit, offset):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_ITEMS:
        raise ValueError(f"limit must be between 1 and {MAX_ITEMS}")
    if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
        raise ValueError("offset must be a nonnegative integer")


def _tokens(pointer):
    if not isinstance(pointer, str) or len(pointer) > 4096 or (pointer and not pointer.startswith("/")):
        raise ValueError("pointer must be an RFC 6901 JSON Pointer, empty for the root")
    tokens = pointer.split("/")[1:] if pointer else []
    if any(re.search(r"~(?![01])", token) for token in tokens):
        raise ValueError("Invalid JSON Pointer escape")
    return [token.replace("~1", "/").replace("~0", "~") for token in tokens]


def _child(pointer, key):
    return pointer + "/" + str(key).replace("~", "~0").replace("/", "~1")


def _resolve(schema):
    result = dict(schema)
    if "$ref" in result:
        target = contract()["schemas"][result.pop("$ref").rsplit("/", 1)[-1]]
        result = {**_resolve(target), **result}
    for part in result.pop("allOf", []):
        result = {**_resolve(part), **result}
    return result


def response_schema(dataset):
    content = contract()["responses"][_source(dataset).path]
    schema = content.get("application/json", {}).get("schema", {"type": "string", "format": "binary"})
    # Search results are stored individually and selected by activity ID. The
    # catalog must describe that same object view, not an artificial array index.
    return schema["items"] if _source(dataset).scope == "activity_list" else schema


def field_schema(dataset, pointer=""):
    schema = response_schema(dataset)
    for token in _tokens(pointer):
        schema = _resolve(schema)
        if schema.get("type") == "array":
            if token != "*" and not token.isdecimal():
                return {}
            schema = schema.get("items", {})
        else:
            schema = schema.get("properties", {}).get(token, schema.get("additionalProperties", {}))
            if not isinstance(schema, dict):
                return {}
    return _resolve(schema)


def _description(schema):
    schema = _resolve(schema)
    return {key: value for key, value in schema.items()
            if key not in {"properties", "items", "additionalProperties"}}


def api_catalog(dataset="", pointer="", *, limit=100, offset=0):
    """List sources, then a page of schema children at a native field pointer.

    Use * as the array item token in schema pointers. In data pointers use a
    concrete index. Descriptions include vendor units where documented; absent
    unit documentation is never replaced with a guess.
    """
    _bounds(limit, offset)
    base = {key: contract()[key] for key in ("source", "reviewed", "api_version", "schema_sha256")}
    if not dataset:
        if pointer:
            raise ValueError("A pointer requires a source")
        sources = [{"dataset": name, "endpoint": source.path, "scope": source.scope}
                   for name, source in SOURCES.items()]
        return {**base, "sources": sources[offset:offset + limit], "total": len(sources),
                "next_offset": offset + limit if offset + limit < len(sources) else None}
    schema = field_schema(dataset, pointer)
    children = [(name, value) for name, value in schema.get("properties", {}).items()]
    if "items" in schema:
        children.append(("*", schema["items"]))
    entries = [{"pointer": _child(pointer, name), **_description(value)} for name, value in children]
    return {**base, "dataset": dataset, "endpoint": _source(dataset).path, "pointer": pointer,
            "scope": _source(dataset).scope,
            "schema": _description(schema), "fields": entries[offset:offset + limit], "total": len(entries),
            "next_offset": offset + limit if offset + limit < len(entries) else None,
            "note": "Native source fields; use source-data for values. Arrays use concrete indices in data pointers. "
                    "Open-ended objects may contain fields not enumerated by Garmin's schema."}


def _activity_id(value):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("This source requires a positive activity_id")


def _stored(db, dataset, day, activity_id):
    source = _source(dataset)
    metadata = {"source": "Garmin Personal API via local archive", "dataset": dataset,
                "endpoint": source.path, "scope": source.scope}
    if source.scope == "daily":
        parse_day(day)
        if activity_id:
            raise ValueError("Daily sources use day, not activity_id")
        metadata["requested_day"] = day
        row = db.execute(
            "SELECT d.data_json, d.fetched_at, s.status, s.error, s.updated_at AS last_attempt "
            "FROM (SELECT 1) LEFT JOIN daily_data d ON d.dataset=? AND d.day=? "
            "LEFT JOIN sync_state s ON s.dataset=? AND s.day=?", (dataset, day, dataset, day)).fetchone()
    else:
        if day:
            raise ValueError("This source is a current snapshot or activity; omit day")
        if source.scope == "current":
            if activity_id:
                raise ValueError("Current settings do not use activity_id")
            resource_id = "current"
        else:
            _activity_id(activity_id)
            resource_id = str(activity_id)
            metadata["activity_id"] = activity_id
        if source.scope in {"activity_list", "file"}:
            column = "summary_json" if source.scope == "activity_list" else "NULL"
            row = db.execute(
                f"SELECT {('a.' + column) if column != 'NULL' else column} AS data_json, a.updated_at AS fetched_at, "
                "s.status, s.error, s.updated_at AS last_attempt, a.day, a.fit_status, length(a.original_zip) AS original_bytes "
                "FROM activities a LEFT JOIN sync_state s ON s.dataset='activities' AND s.day=a.day "
                "WHERE activity_id=?", (activity_id,)).fetchone()
            if row:
                metadata["activity_day"] = row["day"]
                if source.scope == "file":
                    return {**metadata, "status": "ok" if row["original_bytes"] is not None else "not_checked",
                            "fetched_at": None, "last_attempt": None, "fit_status": row["fit_status"],
                            "original_bytes": row["original_bytes"], "data": None,
                            "note": "Original bytes are retained. Export with export-original; decoded samples use records/activity_records. "
                                    "The archive does not record a separate original-file fetch time."}
        else:
            exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_snapshots'").fetchone()
            row = db.execute("SELECT * FROM source_snapshots WHERE dataset=? AND resource_id=?",
                             (dataset, resource_id)).fetchone() if exists else None
    result = {**metadata, "status": row["status"] if row and row["status"] else "not_checked",
              "error": row["error"] if row else None, "fetched_at": row["fetched_at"] if row else None,
              "last_attempt": row["last_attempt"] if row else None,
              "retained_data_available": bool(row and row["data_json"] is not None)}
    # A failed search refresh also masks dependent activity detail snapshots.
    if source.scope == "activity":
        parent = db.execute("SELECT s.status, s.error, s.updated_at, a.day FROM activities a "
            "LEFT JOIN sync_state s ON s.dataset='activities' AND s.day=a.day WHERE a.activity_id=?", (activity_id,)).fetchone()
        if parent:
            result["activity_day"] = parent["day"]
            if parent["status"] == "error":
                result.update(status="error", error=parent["error"], last_attempt=parent["updated_at"])
    raw = row["data_json"] if row else None
    if result["status"] in {"ok", "empty"} and raw is not None:
        result["data"] = json.loads(raw)
    else:
        result["data"] = None
        if result["status"] == "ok":
            result["status"] = "response_missing"
    return result


def _location(key):
    key = str(key).lower().replace("_", "")
    return "latitude" in key or "longitude" in key or key in {"lat", "lon", "lng", "positionlat", "positionlong"}


def without_coordinates(value):
    if isinstance(value, dict):
        return {key: without_coordinates(item) for key, item in value.items() if not _location(key)}
    if isinstance(value, list):
        return [without_coordinates(item) for item in value]
    return value


def snapshot_coverage(db):
    exists = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_snapshots'").fetchone()
    return [dict(row) for row in db.execute(
        "SELECT dataset, status, COUNT(*) AS resources, MAX(fetched_at) AS fetched_at, "
        "MAX(last_attempt) AS last_attempt, MAX(error) AS error_example "
        "FROM source_snapshots GROUP BY dataset, status ORDER BY dataset, status"
    )] if exists else []


def _select(data, tokens):
    for token in tokens:
        if isinstance(data, dict) and token in data:
            data = data[token]
        elif isinstance(data, list) and re.fullmatch(r"0|[1-9][0-9]*", token) and int(token) < len(data):
            data = data[int(token)]
        else:
            return False, None
    return True, data


def _kind(value):
    if value is None: return "null"
    if isinstance(value, bool): return "boolean"
    if isinstance(value, dict): return "object"
    if isinstance(value, list): return "array"
    if isinstance(value, str): return "string"
    return "number"


def source_data(db, dataset, day="", activity_id=0, pointer="", *, limit=100, offset=0, include_location=False):
    """Page a native response node, retaining every field, including unknown ones.

    Large child nodes return navigable pointers instead of truncated values.
    A string node pages by characters; objects page by keys and arrays by items.
    """
    _bounds(limit, offset)
    tokens = _tokens(pointer)
    result = _stored(db, dataset, day, activity_id)
    result["archive_provenance"] = archive_provenance(db)
    data = result.pop("data")
    result.update(pointer=pointer, field_status="unavailable", next_offset=None,
                  location_policy="included" if include_location else "coordinate fields omitted; opt in with include_location")
    if result["status"] not in {"ok", "empty"} or _source(dataset).scope == "file":
        return result
    if not include_location and any(_location(token) for token in tokens):
        result["field_status"] = "location_omitted"
        return result
    found, value = _select(data, tokens)
    result["field_status"] = "available" if found else "missing"
    if not found:
        return result
    result["type"] = _kind(value)
    if value is None:
        result.update(field_status="null", value=None)
    elif isinstance(value, str):
        # Explicit character pagination preserves even very long notes.
        result.update(value=value[offset:offset + limit], total=len(value), offset=offset,
                      next_offset=offset + limit if offset + limit < len(value) else None)
    elif isinstance(value, (dict, list)):
        entries = []
        keys = list(value) if isinstance(value, dict) else range(len(value))
        index = offset
        while index < min(len(keys), offset + limit):
            key = keys[index]
            item = value[key]
            entry = {"pointer": _child(pointer, key), "type": _kind(item)}
            if isinstance(value, dict):
                entry["key"] = key
            else:
                entry["index"] = key
            if not include_location and isinstance(value, dict) and _location(key):
                entry["field_status"] = "location_omitted"
            else:
                item = item if include_location else without_coordinates(item)
                if len(json.dumps(item, ensure_ascii=False).encode()) <= INLINE_BYTES:
                    entry["value"] = item
                else:
                    entry["total"] = len(item)
                    entry["expand"] = True
            if len(json.dumps([*entries, entry], ensure_ascii=False).encode()) > MAX_PAGE_BYTES:
                if not entries:
                    raise ValueError("Field name exceeds the page size; inspect the native response locally with health")
                break
            entries.append(entry)
            index += 1
        result.update(entries=entries, total=len(keys), offset=offset,
                      next_offset=index if index < len(keys) else None)
    else:
        result["value"] = value
    return result


def source_series(db, dataset, pointer, start="", end=""):
    """Read a native scalar field across 1–90 request dates, without aggregation.

    Values are source scalars, not derived daily statistics. An indexed array
    refers to source order, never an inferred stable entity or daily average.
    """
    if _source(dataset).scope != "daily":
        raise ValueError("Series require a daily source")
    tokens = _tokens(pointer)
    if any(_location(token) for token in tokens):
        raise ValueError("Use source-data with include_location for coordinate fields")
    first, last, prefs, today_source = query_range(db, start, end)
    points = []
    for i in range((last - first).days + 1):
        day = (first + timedelta(days=i)).isoformat()
        result = _stored(db, dataset, day, 0)
        data = result.pop("data")
        found, value = _select(data, tokens) if result["status"] in {"ok", "empty"} else (False, None)
        state = "unavailable" if result["status"] not in {"ok", "empty"} else "missing" if not found else "null" if value is None else "available"
        if found and isinstance(value, (dict, list)):
            state, value = "not_scalar", None
        if isinstance(value, str) and len(value.encode()) > INLINE_BYTES:
            state, value = "use_source_data", None
        points.append({"requested_day": day, "status": result["status"], "field_status": state,
                       "value": value, "fetched_at": result["fetched_at"], "last_attempt": result["last_attempt"],
                       "error": result.get("error")})
    return {"archive_provenance": archive_provenance(db), "source": "Garmin Personal API via local archive", "dataset": dataset, "pointer": pointer,
            "field": _description(field_schema(dataset, pointer)), "from": first.isoformat(), "to": last.isoformat(),
            "preferences": prefs, "today_source": today_source,
            "coverage": {"requested_days": len(points), "values_returned": sum(p["field_status"] == "available" for p in points)},
            "points": points, "note": "Native scalars, including source sentinels. Dates identify collection requests; "
            "consult payload dates/timestamps. No unit conversion, validation of measurement meaning, or daily aggregation is inferred."}

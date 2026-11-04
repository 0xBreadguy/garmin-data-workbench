"""Reusable, deterministic synthetic Personal API transport fixtures.

The contract supplies breadth, not an oracle for metric interpretation. These
values are shape examples; dedicated sleep, battery and query fixtures supply
coherent measurements and domain edge cases. Nothing is copied from an account.
"""
from copy import deepcopy
from datetime import UTC, datetime
import struct

from garmin_fit_sdk import CrcCalculator

from garmin_archive.api_data import contract, response_schema
from garmin_archive.sources import SOURCES

DAY = "2026-01-01"


def native_values():
    """Unspecified/forward-compatible fields, including JSON Pointer escapes."""
    return {"zero": 0, "negative": -12.5, "false": False, "true": True,
            "null": None, "empty_object": {}, "empty_array": [], "empty_string": "",
            "large_id": 9_007_199_254_740_993, "unicode": "Synthetic 🍞 日本語",
            "a/b~c": {"": [0, False, None, "", {"nested": 1.25}]}}


def specimen(schema, ancestors=()):
    """Populate declared fields and open maps, failing on unsupported shapes.

    Formats get parseable example strings. Vendor patterns, cross-field
    relationships and physiological constraints are not validated here.
    """
    if "$ref" in schema:
        name = schema["$ref"].rsplit("/", 1)[-1]
        if name in ancestors:
            return {}  # Bound recursive object definitions, preserving other branches.
        return specimen(contract()["schemas"][name], (*ancestors, name))
    if "allOf" in schema:
        merged = {}
        for part in schema["allOf"]:
            value = specimen(part, ancestors)
            if not isinstance(value, dict):
                raise ValueError("Corpus only supports object allOf definitions")
            merged.update(value)
        # Include sibling properties if a future contract adds them.
        merged.update({key: specimen(value, ancestors)
                       for key, value in schema.get("properties", {}).items()})
        return merged
    if any(key in schema for key in ("oneOf", "anyOf")):
        raise ValueError("Add explicit corpus variants for union schemas")
    if schema.get("enum"):
        return schema["enum"][0]
    kind = schema.get("type")
    if kind == "object":
        value = {key: specimen(child, ancestors)
                 for key, child in schema.get("properties", {}).items()}
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            value["synthetic_key"] = specimen(additional, ancestors)
        elif not value and additional is not False:
            value = native_values()
        return value
    if kind == "array":
        return [specimen(schema["items"], ancestors)]
    if kind == "string":
        return {"date": DAY, "date-time": DAY + "T07:30:00.000Z", "time": "07:30:00",
                "uuid": "00000000-0000-4000-8000-000000000042"}.get(
                    schema.get("format"), "synthetic 🍞")
    if kind == "integer":
        return 42
    if kind == "number":
        return 1.25
    if kind == "boolean":
        return False
    raise ValueError(f"Unsupported corpus schema: {schema}")


def contract_payloads():
    """One full response per JSON source; search responses are lists on the wire."""
    payloads = {}
    for name, source in SOURCES.items():
        if source.scope == "file":
            continue
        payload = specimen(response_schema(name))
        item = payload[0] if isinstance(payload, list) else payload
        item["synthetic_extension"] = deepcopy(native_values())
        if source.scope == "activity_list":
            item["activityId"] = 42
            payload = [item]
        payloads[source.path] = payload
    return payloads


def activity_fit(sport=2, *, gps=True):
    """A FIT recording with scaled sensors, zeroes, invalids and summary messages.

    Positions are invented at the pole/equator, never a person's route. Wire
    definitions are explicit so expected decoded values are independent of the
    SDK's profile metadata. The SDK supplies only CRC calculation here.
    """
    def definition(local, message, fields):
        return (bytes([0x40 | local, 0, 0]) + struct.pack("<H", message)
                + bytes([len(fields)]) + b"".join(bytes(field) for field in fields))

    stamp = int((datetime(2026, 1, 1, tzinfo=UTC)
                 - datetime(1989, 12, 31, tzinfo=UTC)).total_seconds())
    body = definition(0, 0, [(0, 1, 0), (1, 2, 0x84), (2, 2, 0x84)])
    body += b"\x00" + struct.pack("<BHH", 4, 1, 1)
    fields = [(253, 4, 0x86), (0, 4, 0x85), (1, 4, 0x85),
        (3, 1, 2), (4, 1, 2), (5, 4, 0x86), (7, 2, 0x84), (13, 1, 1),
        (73, 4, 0x86), (78, 4, 0x86)]
    body += definition(1, 20, fields if gps else [fields[0], *fields[3:]])
    for values in (
        (stamp, 1_073_741_824, -1_073_741_824, 123, 95, 12345, 250, -5, 4500, 3117),
        (stamp + 60, 0, 0, 0, 0, 0, 0, 0, 0, 2500),
        (stamp + 120, 0x7fffffff, 0x7fffffff, 255, 255, 0xffffffff, 65535, 127,
         0xffffffff, 0xffffffff),
    ):
        body += b"\x01" + struct.pack("<IiiBBIHbII" if gps else "<IBBIHbII", *(values if gps else (values[0], *values[3:])))
    body += definition(2, 18, [(253, 4, 0x86), (2, 4, 0x86), (5, 1, 0),
                             (7, 4, 0x86), (8, 4, 0x86), (9, 4, 0x86)])
    body += b"\x02" + struct.pack("<IIBIII", stamp + 120, stamp, sport, 120000, 60000, 12345)
    body += definition(3, 19, [(253, 4, 0x86), (2, 4, 0x86), (9, 4, 0x86)])
    body += b"\x03" + struct.pack("<III", stamp + 120, stamp, 12345)
    body += definition(4, 21, [(253, 4, 0x86), (0, 1, 0), (1, 1, 0)])
    body += b"\x04" + struct.pack("<IBB", stamp, 0, 0)  # Timer start.
    header = struct.pack("<BBHI4s", 14, 0x20, 2200, len(body), b".FIT")
    header += struct.pack("<H", CrcCalculator.calculate_crc(header, 0, len(header)))
    content = header + body
    return content + struct.pack("<H", CrcCalculator.calculate_crc(content, 0, len(content)))

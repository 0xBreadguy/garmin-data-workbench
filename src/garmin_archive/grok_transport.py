"""Versioned, lossless packing of the fields used by the native Grok view.

This is a presentation transport, not a query or metric definition. Field order
is part of codec version 1 and must match decodeTransport in recovery.canvas.tsx.
Nulls, zeroes, status strings and timestamps are retained without interpretation.
"""
from __future__ import annotations

CODEC_VERSION = 1
SLEEP_FIELDS = ("sleep_duration", "sleep_need", "sleep_awake", "sleep_score",
                "sleep_deep", "sleep_light", "sleep_rem", "sleep_unmeasurable")
TIME_FIELDS = ("start_utc", "end_utc", "start_local", "end_local")
TREND_METRICS = ("overnight_hrv", "resting_heart_rate", "body_battery_charged")
COMPARISON_METRICS = ("sleep_duration", "overnight_hrv", "resting_heart_rate",
                      "sleep_score", "body_battery_charged")


def project_grok_snapshot(snapshot: dict) -> dict:
    """Keep exact canonical values consumed by the view; do not aggregate them."""
    if snapshot["schema_version"] != 1:
        raise ValueError("Unsupported recovery snapshot version.")
    report = snapshot["report"]
    result = {"schema_version": 1, "report": {
        "from": report["from"], "to": report["to"],
        "archive_provenance": report["archive_provenance"],
        "sleep": {"nights": [{
            **{key: night[key] for key in ("day", "status", "stages_complete", "fetched_at")},
            "timing": {key: night["timing"][key] for key in TIME_FIELDS},
            "values": {key: night["values"][key] for key in SLEEP_FIELDS},
        } for night in report["sleep"]["nights"]]},
        "trends": {metric: {"points": [{key: point[key] for key in
            ("day", "value", "status", "fetched_at")} for point in report["trends"][metric]["points"]]}
            for metric in TREND_METRICS},
    }, "comparison": None}
    if snapshot["comparison"] is not None:
        comparisons = {}
        for metric in COMPARISON_METRICS:
            source = snapshot["comparison"]["metrics"][metric]
            comparison = {"change": {key: source["change"][key] for key in ("status", "mean_difference")},
                          "warnings": list(source["warnings"])}
            for name in ("baseline", "period"):
                period = source[name]
                comparison[name] = {**{key: period[key] for key in ("from", "to", "mean_of_available_days")},
                    "coverage": {key: period["coverage"][key] for key in ("days_with_value", "requested_days")},
                    "freshness": {key: period["freshness"][key] for key in
                                  ("oldest_available_fetch", "newest_available_fetch")}}
            comparisons[metric] = comparison
        result["comparison"] = {"metrics": comparisons}
    return result


def pack_grok_snapshot(snapshot: dict) -> dict:
    """Replace repeated strings and field names with versioned dictionary/tuples."""
    projected = project_grok_snapshot(snapshot)
    report = projected["report"]
    strings, indices = [], {}

    def text(value):
        if value is None:
            return None
        if value not in indices:
            indices[value] = len(strings)
            strings.append(value)
        return indices[value]

    bounds = [text(report["from"]), text(report["to"])]
    nights = [[text(night["day"]), text(night["status"]), night["stages_complete"],
               text(night["fetched_at"]), [text(night["timing"][key]) for key in TIME_FIELDS],
               [night["values"][key] for key in SLEEP_FIELDS]]
              for night in report["sleep"]["nights"]]
    trends = [[[text(point["day"]), point["value"], text(point["status"]), text(point["fetched_at"])]
               for point in report["trends"][metric]["points"]] for metric in TREND_METRICS]
    comparisons = None
    if projected["comparison"] is not None:
        comparisons = []
        for metric in COMPARISON_METRICS:
            comparison = projected["comparison"]["metrics"][metric]
            periods = []
            for name in ("baseline", "period"):
                period = comparison[name]
                periods.append([text(period["from"]), text(period["to"]), period["mean_of_available_days"],
                    period["coverage"]["days_with_value"], period["coverage"]["requested_days"],
                    text(period["freshness"]["oldest_available_fetch"]),
                    text(period["freshness"]["newest_available_fetch"])])
            comparisons.append([*periods, text(comparison["change"]["status"]),
                comparison["change"]["mean_difference"], [text(warning) for warning in comparison["warnings"]]])
    return {"codec_version": CODEC_VERSION, "schema_version": projected["schema_version"],
            "strings": strings, "range": bounds, "provenance": report["archive_provenance"],
            "nights": nights, "trends": trends, "comparison": comparisons}

"""Independent synthetic expectations for comparisons and covered activity volume."""
from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from garmin_archive.archive import Archive
from garmin_archive.comparisons import compare_periods, validate_periods
from garmin_archive.workouts import get_workout_summary, list_activities


class AnalysisTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.archive = Archive(Path(temp.name))
        self.addCleanup(self.archive.close)
        self.db = self.archive.connection
        self.archive.save_preferences("statute_us", "America/Los_Angeles")

    def steps(self, day, value):
        self.archive.save_daily("daily_summary", day, {"data": [{"calendarDate": day,
            "movement": {"steps": {"value": value}}}]})

    def test_comparison_uses_independent_coverage_and_masks_failed_retained_values(self):
        for day, value in (("2026-01-01", 100), ("2026-01-02", 300), ("2026-01-03", 600), ("2026-01-04", 999)):
            self.steps(day, value)
        self.archive.mark_error("daily_summary", "2026-01-04", "HTTP 429")
        result = compare_periods(self.db, "steps", "2026-01-03", "2026-01-05", "2026-01-01", "2026-01-02")
        self.assertEqual(result["baseline"]["mean_of_available_days"], 200)
        self.assertEqual(result["period"]["mean_of_available_days"], 600)
        self.assertEqual(result["change"]["mean_difference"], 400)
        self.assertEqual(result["change"]["mean_percent_change"], 200)
        self.assertEqual(result["period"]["coverage"]["days_with_value"], 1)
        self.assertEqual(result["period"]["points"][1]["status"], "error")
        self.assertIsNone(result["period"]["points"][1]["value"])
        self.assertIsNotNone(result["period"]["points"][0]["fetched_at"])
        self.assertEqual(result["warnings"], ["period_incomplete_coverage", "unequal_period_lengths"])

    def test_zero_missing_and_score_percentages_have_distinct_reasons(self):
        self.steps("2026-01-01", 0)
        self.steps("2026-01-02", 10)
        zero = compare_periods(self.db, "steps", "2026-01-02", "2026-01-02", "2026-01-01", "2026-01-01")
        self.assertEqual(zero["change"]["mean_difference"], 10)
        self.assertIsNone(zero["change"]["mean_percent_change"])
        self.assertEqual(zero["change"]["percent_change_status"], "zero_baseline")
        for day, score in (("2026-01-01", 80), ("2026-01-02", 88)):
            self.archive.save_daily("sleep", day, {"sleepScores": {"overall": {"value": score}}})
        score = compare_periods(self.db, "sleep_score", "2026-01-02", "2026-01-02", "2026-01-01", "2026-01-01")
        self.assertEqual(score["change"]["mean_difference"], 8)
        self.assertEqual(score["change"]["percent_change_status"], "not_applicable_to_scale")
        missing = compare_periods(self.db, "steps", "2026-01-03", "2026-01-03", "2026-01-01", "2026-01-01")
        self.assertEqual(missing["change"]["status"], "unavailable")
        self.assertIsNone(missing["change"]["mean_difference"])

    def test_period_validation_covers_overlap_order_format_and_90_day_boundary(self):
        for bounds in (("2026-01-02", "2026-01-01", "2025-12-01", "2025-12-02"),
                       ("2026-01-01", "2026-04-01", "2025-12-01", "2025-12-02"),
                       ("2026-01-01", "2026-01-02", "2025-12-31", "2026-01-01"),
                       ("20260101", "2026-01-02", "2025-12-01", "2025-12-02"),
                       ("2026-01-01", "2026-01-02", "2025-01-01", "2025-12-31")):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                validate_periods(*bounds)
        validate_periods("2026-01-01", "2026-03-31", "2025-12-01", "2025-12-31")

    def test_changes_use_unrounded_means_and_today_is_flagged(self):
        for day, value in enumerate((1, 1, 2, 2, 2, 3), 1):
            self.steps(f"2026-01-{day:02}", value)
        with patch("garmin_archive.comparisons.local_today", return_value=(date(2026, 1, 6), "host")):
            result = compare_periods(self.db, "steps", "2026-01-04", "2026-01-06", "2026-01-01", "2026-01-03")
        self.assertEqual(result["change"]["mean_difference"], 1)
        self.assertEqual(result["change"]["mean_percent_change"], 75)
        self.assertEqual(result["warnings"], ["period_includes_today_or_future"])

    def activity(self, identity, distance=None, duration=None, kind="running", **extra):
        return {"activityId": identity, "activityName": "Synthetic", "activityType": {"typeKey": kind},
                "distance": distance, "duration": duration, "position_lat": "PRIVATE", **extra}

    def test_workouts_have_week_boundaries_field_counts_preferences_and_no_locations(self):
        self.archive.save_activities("2026-01-04", [self.activity(1, 1609.344, 600), self.activity(2, None, 300)])
        self.archive.save_activities("2026-01-05", [self.activity(3, 3218.688, 900), self.activity(4, 999, 999, "cycling")])
        self.archive.save_activities("2026-01-06", [])
        self.archive.save_activities("2026-01-07", [self.activity(5, 99999, 99999)])
        self.archive.mark_error("activities", "2026-01-07", "HTTP 429")
        result = get_workout_summary(self.db, "2026-01-04", "2026-01-08", "running")
        self.assertEqual(result["totals"]["activity_count"], 3)
        self.assertEqual(result["totals"]["distance_m"], 4828.032)
        self.assertEqual(result["totals"]["distance_m_activities"], 2)
        self.assertEqual(result["totals"]["duration_s"], 1800)
        self.assertEqual(result["totals"]["display_distance"], 3)
        self.assertEqual(result["totals"]["display_distance_unit"], "mi")
        self.assertEqual(result["coverage"]["days_available"], 3)
        self.assertEqual([w["week_start"] for w in result["weeks"]], ["2025-12-29", "2026-01-05"])
        self.assertEqual([w["duration_s"] for w in result["weeks"]], [900, 900])
        self.assertEqual(result["days"][2]["activity_count"], 0)
        self.assertIsNone(result["days"][3]["activity_count"])
        self.assertIsNone(result["days"][4]["distance_m"])
        self.assertNotIn("PRIVATE", str(result))

    def test_multisport_parents_are_excluded_before_type_filtering_and_recordings_remain_separate(self):
        self.archive.save_activities("2026-01-01", [self.activity(1, 9000, 900, "multisport"),
            self.activity(2, 1000, 100, parentId=1), self.activity(3, 8000, 800, "cycling", parentId=1),
            self.activity(4, 2000, 200)])
        result = get_workout_summary(self.db, "2026-01-01", "2026-01-01")
        self.assertEqual(result["totals"]["activity_count"], 3)
        self.assertEqual(result["totals"]["distance_m"], 11000)
        running = get_workout_summary(self.db, "2026-01-01", "2026-01-01", "running")
        self.assertEqual(running["totals"]["distance_m"], 3000)
        page = list_activities(self.db, "2026-01-01", "2026-01-01", "running", limit=1)
        self.assertEqual(page["activities"][0]["activity_id"], 4)
        self.assertEqual(page["next_offset"], 1)
        self.assertEqual(list_activities(self.db, activity_type="running", offset=1)["activities"][0]["activity_id"], 2)
        self.assertNotIn("PRIVATE", str(page))

    def test_missing_fields_zero_empty_and_unchecked_are_not_conflated(self):
        self.archive.save_activities("2026-01-01", [self.activity(1, True, -1), self.activity(2, "123", None)])
        self.archive.save_activities("2026-01-02", [])
        invalid = get_workout_summary(self.db, "2026-01-01", "2026-01-02")
        self.assertEqual(invalid["totals"]["activity_count"], 2)
        self.assertIsNone(invalid["totals"]["distance_m"])
        self.assertEqual(invalid["totals"]["distance_m_activities"], 0)
        empty = get_workout_summary(self.db, "2026-01-02", "2026-01-02")
        self.assertEqual(empty["totals"]["distance_m"], 0)
        missing = get_workout_summary(self.db, "2026-01-03", "2026-01-03")
        self.assertIsNone(missing["totals"]["activity_count"])
        self.assertIsNone(missing["totals"]["distance_m"])
        self.archive.save_activities("2026-01-04", [self.activity(3, 0, 0)])
        zero = get_workout_summary(self.db, "2026-01-04", "2026-01-04")
        self.assertEqual(zero["totals"]["distance_m"], 0)
        self.assertEqual(zero["totals"]["distance_m_activities"], 1)

    def test_list_masks_failed_measurements_and_rejects_unsafe_bounds(self):
        self.archive.save_activities("2026-01-01", [self.activity(1, 100, 10)])
        self.archive.mark_error("activities", "2026-01-01", "HTTP 429")
        row = list_activities(self.db)["activities"][0]
        self.assertEqual(row["status"], "error")
        self.assertIsNone(row["distance_m"])
        self.assertIsNotNone(row["last_attempt"])
        for kwargs in ({"limit": 0}, {"offset": 2**63}, {"start": "bad"},
                       {"start": "2026-01-02", "end": "2026-01-01"}, {"activity_type": "x" * 101}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                list_activities(self.db, **kwargs)
        with self.assertRaises(ValueError):
            get_workout_summary(self.db, "2026-01-01", "2026-04-01")

    def test_parent_exclusion_precedes_date_filter_and_large_totals_remain_valid_json(self):
        self.archive.save_activities("2026-01-01", [self.activity(1, 100, 10)])
        self.archive.save_activities("2026-01-02", [self.activity(2, 100, 10, parentId=1)])
        result = get_workout_summary(self.db, "2026-01-01", "2026-01-01")
        self.assertEqual(result["totals"]["activity_count"], 0)
        self.archive.save_activities("2026-01-03", [self.activity(3, 10**19, 1e308), self.activity(4, 10**19, 1e308)])
        result = get_workout_summary(self.db, "2026-01-03", "2026-01-03")
        self.assertEqual(result["totals"]["distance_m"], 2e19)
        self.assertIsNone(result["totals"]["duration_s"])
        import json
        json.dumps(result, allow_nan=False)

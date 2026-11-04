"""The documented Personal API sources and their collection scopes.

Only collection imports the authenticated client. Queries use these definitions
to describe archived responses, without making any network requests.
"""
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable


@dataclass(frozen=True)
class Source:
    path: str
    scope: str
    fetch: Callable[[Any, Any, date], Any] | None = None


SOURCES = {
    "daily_summary": Source("/usersummary-service/v2/dailysummaries", "daily",
        lambda c, d, t: c.get_daily_summaries(d, d)),
    "sleep": Source("/sleep-service/sleep/dailySleep", "daily", lambda c, d, t: c.get_daily_sleep(d)),
    "hrv": Source("/hrv-service/hrv/{calendarDate}", "daily", lambda c, d, t: c.get_daily_hrv(d)),
    "heart_rate": Source("/wellness-service/wellness/dailyHeartRate", "daily", lambda c, d, t: c.get_daily_heart_rate(d)),
    "body_battery": Source("/wellness-service/wellness/bodyBattery/reports/daily", "daily",
        lambda c, d, t: c.get_daily_body_battery(d, d)),
    "daily_summary_legacy": Source("/usersummary-service/usersummary/daily", "daily",
        lambda c, d, t: c.get("/usersummary-service/usersummary/daily", params={"calendarDate": d.isoformat()})),
    "steps": Source("/usersummary-service/stats/steps/daily/{startDate}/{endDate}", "daily",
        lambda c, d, t: c.get_daily_steps(d, d)),
    "stress": Source("/usersummary-service/stats/stress/daily/{startDate}/{endDate}", "daily",
        lambda c, d, t: c.get_daily_stress(d, d)),
    "hydration": Source("/usersummary-service/stats/hydration/daily/{startDate}/{endDate}", "daily",
        lambda c, d, t: c.get_daily_hydration(d, d)),
    "weight": Source("/weight-service/weight/range/{startDate}/{endDate}", "daily",
        lambda c, d, t: c.get_weight_measurements(d, d)),
    "weight_measurements": Source("/weight-service/weight/all/{startDate}/{endDate}", "daily",
        lambda c, d, t: c.get(f"/weight-service/weight/all/{d.isoformat()}/{d.isoformat()}")),
    "weight_goals": Source("/goal-service/goal/user/effective/weightgoal/{startDate}/{endDate}", "daily",
        lambda c, d, t: c.get_effective_weight_goals(d, d)),
    "nutrition": Source("/nutrition-service/food/logs/{date}", "daily", lambda c, d, t: c.get_daily_food_logs(d)),
    "fitness_age": Source("/fitnessage-service/fitnessage/v2/{calendarDate}", "daily", lambda c, d, t: c.get_fitness_age(d)),
    "spo2": Source("/wellness-service/wellness/daily/spo2acclimation/{calendarDate}", "daily", lambda c, d, t: c.get_daily_spo2(d)),
    "menstrual_summary": Source("/periodichealth-service/menstrualcycle/summary/{calendarDate}", "daily",
        lambda c, d, t: c.get_menstrual_cycle_summary(d)),
    "menstrual_day": Source("/periodichealth-service/menstrualcycle/dayview/{calendarDate}", "daily",
        lambda c, d, t: c.get(f"/periodichealth-service/menstrualcycle/dayview/{d.isoformat()}",
            params={"todayDate": t.isoformat(), "reducedResponse": "false", "skipbm": "false", "includeAnalysis": "true"})),
    "wellness_activity": Source("/wellnessactivity-service/activity/summary/range/{fromDate}/{untilDate}", "daily",
        lambda c, d, t: c.get_wellness_activity_summaries(d, d)),
    "sleep_summaries": Source("/sleep-service/sleep/dailySleepSummariesByDate", "daily",
        lambda c, d, t: c.get_daily_sleep_summaries(d, d)),
    "hrv_summaries": Source("/hrv-service/hrv/daily/{fromDate}/{toDate}", "daily",
        lambda c, d, t: c.get_daily_hrv_summaries(d, d)),
    "profile": Source("/userprofile-service/userprofile/settings", "current", lambda c, k, t: c.get_user_profile_settings()),
    "heart_rate_zones": Source("/biometric-service/heartRateZones/v2", "current", lambda c, k, t: c.get_heart_rate_zones()),
    "activity": Source("/activity-service/activity/{activityId}", "activity", lambda c, k, t: c.get_activity(k)),
    "activity_workouts": Source("/activity-service/activity/{activityId}/workouts", "activity",
        lambda c, k, t: c.get_activity_workouts(k)),
    "activities": Source("/activitylist-service/activities/search/activities", "activity_list"),
    "original": Source("/download-service/files/activity/{activityId}", "file"),
}
DAILY_SOURCES = tuple(name for name, source in SOURCES.items() if source.scope == "daily")


def search_activities(client, day: date, offset: int, limit: int):
    # The SDK wrapper omits excludeChildren. Its API default is true, losing
    # individual multisport legs; explicitly include them in the archive.
    return client.get(SOURCES["activities"].path, params={"start": offset, "limit": limit,
        "startDate": day.isoformat(), "endDate": day.isoformat(), "excludeChildren": "false"})

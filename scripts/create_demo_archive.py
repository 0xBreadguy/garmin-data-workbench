"""Create a new offline demo archive with generated values and coverage cases.

From the checkout: uv run --locked python scripts/create_demo_archive.py ../garmin-demo
The destination must not exist. No credentials, sync, clients or schedules are used.
"""
from __future__ import annotations

import argparse
import math
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from garmin_archive.archive import Archive
from garmin_archive.platforms import shell_command
from garmin_archive.queries import DAILY_METRICS


def create_demo_archive(destination: Path) -> None:
    destination = destination.expanduser()
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    (destination / "SYNTHETIC.txt").write_text(
        "Generated demo values, not real health data. Render charts with --synthetic.\n", encoding="utf-8")
    archive = Archive(destination)
    try:
        archive.save_preferences("statute_us", "Etc/UTC")
        for i in range(30):
            day = (date(2026, 1, 1) + timedelta(days=i)).isoformat()
            if i == 3:  # Never checked, distinct from a successful empty response.
                continue
            steps = 0 if i == 15 else round(7500 + 2500 * math.sin(i * .9))
            duration = round((7.4 + .7 * math.sin(i * 1.3)) * 3600)
            deep, rem = round(duration * .2), round(duration * .23)
            wake = datetime(2026, 1, 1, 7, tzinfo=UTC) + timedelta(days=i)
            data = {
                "daily_summary_legacy": {"calendarDate": day, **{
                    field: {"kcal": 1500, "steps": 10000, "pushes": 100,
                            "m": 1000, "s": 600, "min": 20, "floors": 5,
                            "mL": 2000, "%": 95, "breaths/min": 15, "Garmin stress": 25}[unit]
                    for field, unit, title in DAILY_METRICS.values()}},
                "daily_summary": {"data": [{"calendarDate": day, "movement": {"steps": {
                    "value": steps, "distanceInMeters": round(steps * .72, 2)}}}]},
                "sleep": {"calendarDate": day, "sleepTimeSeconds": duration,
                    "deepSleepSeconds": deep, "remSleepSeconds": rem,
                    "lightSleepSeconds": duration - deep - rem, "unmeasurableSleepSeconds": 0,
                    "awakeSleepSeconds": 600, "napTimeSeconds": 1200 if i % 5 == 0 else 0,
                    "avgSleepStress": round(20 + 10 * math.sin(i)),
                    "sleepScores": {"overall": {"value": round(80 + 12 * math.sin(i * .8))}},
                    "sleepNeed": {"calendarDate": day, "actual": 480 + (i % 3) * 10, "baseline": 480},
                    "nextSleepNeed": {"calendarDate": (date.fromisoformat(day) + timedelta(days=1)).isoformat(),
                                      "actual": 470 + (i % 3) * 10, "baseline": 480},
                    "sleepStartTimestampGMT": (wake - timedelta(seconds=duration + 600)).isoformat(),
                    "sleepEndTimestampGMT": wake.isoformat(),
                    "sleepStartTimestampLocal": (wake - timedelta(seconds=duration + 600)).isoformat(),
                    "sleepEndTimestampLocal": wake.isoformat()},
                "heart_rate": {"restingHeartRate": round(58 + 3 * math.cos(i * .8)),
                               "minHeartRate": 45, "maxHeartRate": 150},
                "hrv": {"hrvSummary": {"lastNightAvg": round(48 + 8 * math.sin(i * .7))}},
                "body_battery": [{"date": day, "charged": 60, "drained": 50,
                    "startTimestampGMT": wake.replace(hour=0).isoformat(),
                    "endTimestampGMT": wake.replace(hour=23, minute=59).isoformat(),
                    "bodyBatteryValueDescriptorDTOList": [
                        {"bodyBatteryValueDescriptorKey": "bodyBatteryLevel", "bodyBatteryValueDescriptorIndex": 0},
                        {"bodyBatteryValueDescriptorKey": "timestamp", "bodyBatteryValueDescriptorIndex": 1}],
                    "bodyBatteryValuesArray": [[level, int(wake.replace(hour=hour).timestamp() * 1000)]
                                               for hour, level in ((0, 25), (7, 85), (18, 40), (23, 30))]}],
            }
            for dataset, payload in data.items():
                if i == 7:
                    archive.save_daily(dataset, day, {})
                elif i == 16:
                    # A nonempty response that does not include the queried metric.
                    archive.save_daily(dataset, day, {"calendarDate": day, "demo": True})
                else:
                    archive.save_daily(dataset, day, payload)
                    if i == 11:
                        archive.mark_error(dataset, day, "Synthetic failed refresh; retained values must be masked")
    finally:
        archive.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="New demo directory outside the repository")
    args = parser.parse_args(argv)
    try:
        create_demo_archive(args.destination)
    except FileExistsError:
        parser.error("Destination already exists; choose a new directory. Nothing was overwritten.")
    except OSError:
        parser.error("Could not create demo; check destination and permissions.")
    print("Created synthetic data for January 1–30, 2026. No live data was used.")
    print(shell_command(["garmin-archive", "--data-dir", str(args.destination.expanduser().resolve()),
                         "chart", "sleep_duration", "--from", "2026-01-01", "--to", "2026-01-30",
                         "--synthetic", "--output", "synthetic-sleep.png"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

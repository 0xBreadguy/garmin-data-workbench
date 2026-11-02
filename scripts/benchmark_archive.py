"""Small, credential-free synthetic benchmark; never touches the real archive."""
from __future__ import annotations

import statistics
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path

from garmin_archive.archive import Archive
from garmin_archive.queries import metric_trend


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="garmin-benchmark-") as directory:
        archive = Archive(Path(directory))
        try:
            first = date(2026, 1, 1)
            last = first + timedelta(days=89)
            for i in range(90):
                day = (first + timedelta(days=i)).isoformat()
                archive.save_daily("heart_rate", day, {
                    "calendarDate": day, "restingHeartRate": 58,
                    "heartRateValues": [[j, 60] for j in range(10_000)],
                })
            timings = []
            for _ in range(12):
                start = time.perf_counter()
                result = metric_trend(archive.connection, "resting_heart_rate", first.isoformat(), last.isoformat())
                timings.append((time.perf_counter() - start) * 1000)
                assert result["coverage"]["days_with_value"] == 90
            print(f"90-day trend, 10,000 synthetic samples/day: median {statistics.median(timings):.1f} ms; max {max(timings):.1f} ms")

            archive.connection.execute(
                "INSERT INTO activities(activity_id, day, summary_json, updated_at) VALUES (1, ?, '{}', ?)",
                (first.isoformat(), first.isoformat()),
            )
            archive.connection.commit()
            rows = [{"timestamp": "2026-01-01T12:00:00+00:00", "heart_rate": 123,
                     "power": 220, "cadence": 85, "distance": i * 10} for i in range(100_000)]
            start = time.perf_counter()
            archive.save_messages(1, {"record_mesgs": rows})
            print(f"100,000 synthetic FIT records, one transaction: {time.perf_counter() - start:.2f} s")
            print(f"Temporary archive size: {archive.path.stat().st_size / 1_048_576:.1f} MiB")
        finally:
            archive.close()


if __name__ == "__main__":
    main()

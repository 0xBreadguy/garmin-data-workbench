"""Create a new offline demo archive with generated values and coverage cases.

From the checkout: uv run --locked python scripts/create_demo_archive.py ../garmin-demo
The destination must not exist. No credentials, sync, clients or schedules are used.
Dates and simulated fetch times stay fixed; the demo is never shifted to today.
Sleep score and stage formulas are independent, not a physiological model.
Body Battery values are intentionally fixed, apart from coverage/ambiguity cases.
"""
from __future__ import annotations

import argparse
import math
import json
import random
from zoneinfo import ZoneInfo
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from garmin_archive.archive import Archive
from garmin_archive.platforms import shell_command
from garmin_archive.queries import DAILY_METRICS


CORPUS_VERSION = '2'
DEFAULT_SEED = 42
FETCHED_AT = '2026-05-01T12:00:00+00:00'


def create_demo_archive(destination: Path, *, days: int = 120, seed: int = DEFAULT_SEED,
                        profile: str = 'statute', empty: bool = False) -> None:
    if not 1 <= days <= 366 or profile not in {'statute', 'metric-dst'} or not 0 <= seed <= 2**63 - 1:
        raise ValueError('Choose 1–366 days, statute or metric-dst profile, and a seed between 0 and 2^63-1')
    rng = random.Random(seed)
    zone = ZoneInfo('Europe/Berlin' if profile == 'metric-dst' else 'Etc/UTC')
    expected = {name: [] for name in ('steps', 'sleep_duration', 'sleep_score', 'sleep_need', 'body_battery_last')}
    destination = destination.expanduser()
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    (destination / "SYNTHETIC.txt").write_text(
        "Generated demo values, not real health data. Synthetic labeling is automatic.\n", encoding="utf-8")
    archive = Archive(destination)
    try:
        archive.mark_synthetic(CORPUS_VERSION, seed, datetime.now(UTC).isoformat())
        archive.save_preferences('metric' if profile == 'metric-dst' else 'statute_us', str(zone))
        for i in range(0 if empty else days):
            day = (date(2026, 1, 1) + timedelta(days=i)).isoformat()
            steps = 0 if i == 15 else round(7500 + 2500 * math.sin(i * .9))
            duration = round((7.4 + .7 * math.sin(i * 1.3)) * 3600)
            deep, rem = round(duration * rng.uniform(.14, .25)), round(duration * rng.uniform(.17, .28))
            awake = rng.randrange(180, 1801, 60)
            wake_local = (datetime(2026, 1, 1, 7) + timedelta(days=i, minutes=rng.randrange(-45, 61))).replace(tzinfo=zone)
            wake = wake_local.astimezone(UTC)
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
                    "awakeSleepSeconds": awake, "napTimeSeconds": 1200 if i % 5 == 0 else 0,
                    "avgSleepStress": round(20 + 10 * math.sin(i)),
                    "sleepScores": {"overall": {"value": round(80 + 12 * math.sin(i * .8))}},
                    "sleepNeed": {"calendarDate": day, "actual": rng.randrange(455, 516, 5), "baseline": 480},
                    "nextSleepNeed": {"calendarDate": (date.fromisoformat(day) + timedelta(days=1)).isoformat(),
                                      "actual": 470 + (i % 3) * 10, "baseline": 480},
                    "sleepStartTimestampGMT": (wake - timedelta(seconds=duration + awake)).isoformat(),
                    "sleepEndTimestampGMT": wake.isoformat(),
                    "sleepStartTimestampLocal": (wake - timedelta(seconds=duration + awake)).astimezone(zone).isoformat(),
                    "sleepEndTimestampLocal": wake_local.isoformat(),
                    "dailyNapDTOS": ([{"calendarDate": day, "napTimeSec": 1200,
                        "napStartTimestampGMT": wake.replace(hour=13, minute=0, second=0).isoformat(),
                        "napEndTimestampGMT": wake.replace(hour=13, minute=20).isoformat(),
                        "napStartTimeOffset": int(wake_local.utcoffset().total_seconds() / 60),
                        "napEndTimeOffset": int(wake_local.utcoffset().total_seconds() / 60)}] if i % 5 == 0 else [])},
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
            # Deliberate semantic cases, independent of the transport corpus.
            if i == 20:
                data['sleep'].pop('dailyNapDTOS')  # Reported duration without episode detail.
            if i == 35:
                data['sleep'].pop('remSleepSeconds')
            if i == 36:
                data['sleep'].pop('sleepScores')
            if i == 37:
                data['sleep'].pop('sleepNeed')
            if i == 38:
                data['sleep']['lightSleepSeconds'] += 1200  # Inconsistent stages.
            battery = data['body_battery'][0]
            if i % 2:
                battery['bodyBatteryValueDescriptorDTOList'].reverse()
                battery['bodyBatteryValuesArray'].reverse()
            if i == 40:
                battery.pop('bodyBatteryValueDescriptorDTOList')
            if i == 41:
                battery['bodyBatteryValuesArray'].append([31, battery['bodyBatteryValuesArray'][0][1]])
            offsets = {'sleep': 0, 'daily_summary': 1, 'heart_rate': 2, 'body_battery': 3,
                       'hrv': 4, 'daily_summary_legacy': 5}
            states = {}
            for dataset, payload in data.items():
                offset = offsets[dataset]
                state = ('not_checked' if 70 <= i <= 76 or i == 3 + offset else
                         'empty' if i == 7 + offset else 'error' if i == 11 + offset else
                         'metric_not_returned' if i == 16 + offset else 'ok')
                states[dataset] = state
                if state == 'not_checked':
                    continue
                if state == 'empty':
                    archive.save_daily(dataset, day, {})
                elif state == 'metric_not_returned':
                    archive.save_daily(dataset, day, {'calendarDate': day, 'demo': True})
                else:
                    archive.save_daily(dataset, day, payload)
                    if state == 'error':
                        archive.mark_error(dataset, day, 'Synthetic failed refresh; retained values must be masked')
            # Independent expected answers from the scenario definition, never from production queries.
            for metric, dataset, value in (
                ('steps', 'daily_summary', steps), ('sleep_duration', 'sleep', duration),
                ('sleep_score', 'sleep', None if i == 36 else round(80 + 12 * math.sin(i * .8))),
                ('sleep_need', 'sleep', data['sleep'].get('sleepNeed', {}).get('actual')),
                ('body_battery_last', 'body_battery', None if i == 40 else 40 if i == 41 else 30),
            ):
                status = states[dataset]
                if status == 'ok' and value is None:
                    status = 'metric_not_returned'
                expected[metric].append({'day': day, 'status': status, 'value': value if status == 'ok' else None})
            if i in (22, 23):
                archive.save_activities(day, [{'activityId': i, 'activityName': 'Synthetic indoor ride' if i == 22 else 'Synthetic outdoor ride',
                    'activityType': {'typeKey': 'cycling'}, 'distance': 10000, 'duration': 1800}])
                archive.save_snapshot('activity', str(i), {'activityId': i,
                    'metadataDTO': {'hasGPS': i == 23}, **({'startLatitude': 0.0, 'startLongitude': 0.0} if i == 23 else {})})
        # Fixed simulated collection times keep fixture freshness deterministic.
        for table, columns in {'daily_data': ['fetched_at'], 'sync_state': ['updated_at'],
                               'profile_preferences': ['fetched_at'], 'activities': ['updated_at'],
                               'source_snapshots': ['fetched_at', 'last_attempt']}.items():
            for column in columns:
                archive.connection.execute(f'UPDATE {table} SET {column}=?', (FETCHED_AT,))
        archive.connection.commit()
        cases = []
        for first, last in (('2026-01-01', '2026-01-30'), ('2026-01-01', '2026-03-31'),
                            ('2026-03-12', '2026-03-18'), ('2026-03-28', '2026-03-30')):
            metrics = {}
            for metric, points in expected.items():
                by_day = {p['day']: p for p in points}
                selected = []
                for offset in range((date.fromisoformat(last) - date.fromisoformat(first)).days + 1):
                    day = (date.fromisoformat(first) + timedelta(days=offset)).isoformat()
                    selected.append(by_day.get(day, {'day': day, 'status': 'not_checked', 'value': None}))
                values = [p['value'] for p in selected if p['value'] is not None]
                counts = {status: sum(p['status'] == status for p in selected) for status in sorted({p['status'] for p in selected})}
                metrics[metric] = {'days_with_value': len(values), 'statuses': counts,
                    'mean_of_available_days': round(sum(values) / len(values), 2) if values else None,
                    'masked_dates': [p['day'] for p in selected if p['value'] is None], 'points': selected}
            if metrics:
                cases.append({'from': first, 'to': last, 'metrics': metrics})
        manifest = {'corpus_version': CORPUS_VERSION, 'seed': seed, 'profile': profile, 'days': 0 if empty else days,
                    'simulated_fetched_at': FETCHED_AT, 'cases': cases}
        # Corpus fingerprints cover canonical UTF-8/LF bytes on every host.
        (destination / 'known-answers.json').write_bytes((json.dumps(manifest, indent=2) + '\n').encode('utf-8'))
    finally:
        archive.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="New demo directory outside the repository")
    parser.add_argument('--days', type=int, default=120)
    parser.add_argument('--seed', type=int, default=DEFAULT_SEED)
    parser.add_argument('--profile', choices=('statute', 'metric-dst'), default='statute')
    parser.add_argument('--empty', action='store_true', help='Create a marked synthetic archive with no observations')
    args = parser.parse_args(argv)
    try:
        create_demo_archive(args.destination, days=args.days, seed=args.seed, profile=args.profile, empty=args.empty)
    except FileExistsError:
        parser.error("Destination already exists; choose a new directory. Nothing was overwritten.")
    except ValueError as error:
        parser.error(str(error))
    except OSError:
        parser.error("Could not create demo; check destination and permissions.")
    destination = args.destination.expanduser().resolve()
    print(f"Created synthetic corpus v{CORPUS_VERSION}, seed {args.seed}, and known-answers.json at {destination}.")
    print("Manual/offline demo: no live data used; no sync, client registration or recurring job configured by this command.")
    print(f"Simulated fetch timestamp: {FETCHED_AT} (fixed fixture time, not live freshness).")
    print("Sleep scores and stages use independent formulas; they cannot explain physiological causes.")
    print("Body Battery values are intentionally fixed; they cannot demonstrate changing weekly trends.")
    if args.empty:
        print("Available dates: none (--empty); no observations or latest demo week.")
        return 0
    first = date(2026, 1, 1)
    last = first + timedelta(days=args.days - 1)
    start = max(first, last - timedelta(days=6))
    print(f"Demo date window (inclusive): {first} through {last} ({args.days} dates; coverage varies by dataset).")
    print(f"Latest demo {'week' if args.days >= 7 else 'dates'} (inclusive): {start} through {last}.")
    print('If "this week" falls outside this window, there are no observations for it; disclose any demo-date substitution.')
    print("Dates are not shifted to today. Choose fixture dates, or generate a separate longer corpus in a new directory outside the repo.")
    print(f'First question: "How was sleep in the synthetic demo from {start} through {last}, inclusive? Show the sleep overview."')
    command = ["garmin-archive", "--data-dir", str(destination)]
    dates = ["--from", str(start), "--to", str(last)]
    print("Read the full sleep summary (stages, score, need, naps and source times):")
    print(shell_command([*command, "sleep", *dates]))
    print("Render the sleep overview (requires the charts extra; output must be new):")
    print(shell_command([*command, "chart", "sleep", *dates, "--synthetic",
                         "--output", str(destination / "synthetic-sleep-overview.png")]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

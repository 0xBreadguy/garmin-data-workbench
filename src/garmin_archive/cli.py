"""Command-line interface for a local Garmin archive."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from garmin_personal_api import (
    GarminPersonalApiClient,
    PersonalApiAuthenticator,
    resolve_api_key,
)

from .archive import Archive, default_data_dir
from .sync import DATASETS, sync


def _date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use a date in YYYY-MM-DD format") from error


def _positive(value: str) -> int:
    try:
        number = int(value)
        if number < 1:
            raise ValueError
        return number
    except ValueError as error:
        raise argparse.ArgumentTypeError("Must be a positive integer") from error


def _nonnegative(value: str) -> int:
    try:
        number = int(value)
        if number < 0:
            raise ValueError
        return number
    except ValueError as error:
        raise argparse.ArgumentTypeError("Must be a non-negative integer") from error


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Download and query your own Garmin data locally.")
    result.add_argument(
        "--data-dir", type=Path, default=default_data_dir(),
        help="Private archive directory (default: XDG_DATA_HOME/garmin-extraction or ~/.local/share/garmin-extraction)",
    )
    commands = result.add_subparsers(dest="command", required=True)

    sync_parser = commands.add_parser("sync", help="Sync health and activity data for an inclusive date range")
    sync_parser.add_argument("--from", dest="start", type=_date, default=None, help="Start date, YYYY-MM-DD (default: six days ago)")
    sync_parser.add_argument("--to", dest="end", type=_date, default=None, help="End date, YYYY-MM-DD (default: today)")
    sync_parser.add_argument("--refresh", action="store_true", help="Re-fetch completed days in the selected range")
    sync_parser.add_argument("--pause", type=float, default=0.3, help="Seconds between requests (default: 0.3)")

    commands.add_parser("status", help="Show archive coverage and sync errors")
    commands.add_parser("path", help="Print the SQLite database path")
    activities = commands.add_parser("activities", help="List stored activity summaries")
    activities.add_argument("--limit", type=_positive, default=20)
    activities.add_argument("--offset", type=_nonnegative, default=0)

    health = commands.add_parser("health", help="Print a stored daily health response as JSON")
    health.add_argument("dataset", choices=sorted(DATASETS))
    health.add_argument("day", type=_date)

    records = commands.add_parser("records", help="Show decoded time-series records for one activity")
    records.add_argument("activity_id", type=_positive)
    records.add_argument("--limit", type=_positive, default=100)
    records.add_argument("--offset", type=_nonnegative, default=0)
    records.add_argument("--format", choices=("json", "csv"), default="json")
    records.add_argument("--full", action="store_true", help="Include complete decoded fields, including location when recorded")

    original = commands.add_parser("export-original", help="Save the original downloaded activity ZIP")
    original.add_argument("activity_id", type=_positive)
    original.add_argument("path", type=Path)
    return result


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def _sync(archive: Archive, args: argparse.Namespace) -> int:
    end = args.end or date.today()
    start = args.start or end - timedelta(days=6)
    if start > end or args.pause < 0:
        print("Start must not be after end, and pause must not be negative.", file=sys.stderr)
        return 2
    # The official client logs URLs and HTTP errors can contain response bodies.
    logging.disable(logging.CRITICAL)
    try:
        with PersonalApiAuthenticator() as auth:
            token = auth.obtain_token(resolve_api_key())
        with GarminPersonalApiClient(token.access_token) as client:
            report = sync(archive, client, start, end, refresh=args.refresh, pause=args.pause)
    except Exception as error:  # noqa: BLE001 -- keep private API response bodies out of the terminal
        print(f"Sync could not start ({type(error).__name__}). Check your key and connection.", file=sys.stderr)
        return 1
    _print_json({
        "range": {"from": start.isoformat(), "to": end.isoformat()},
        "health_requests_succeeded": report.checked,
        "completed_days_skipped": report.skipped,
        "activities_seen": report.activities,
        "activity_files_decoded": report.decoded,
        "non_fit_originals": report.unsupported,
        "stopped": report.stopped,
        "errors": report.errors,
    })
    return 1 if report.errors else 0


def _status(archive: Archive) -> int:
    states = [dict(row) for row in archive.connection.execute(
        """SELECT dataset, status, COUNT(*) AS days, MIN(day) AS first_day,
                  MAX(day) AS last_day, MAX(updated_at) AS last_attempt
           FROM sync_state GROUP BY dataset, status ORDER BY dataset, status"""
    )]
    fit = [dict(row) for row in archive.connection.execute(
        "SELECT fit_status, COUNT(*) AS activities FROM activities GROUP BY fit_status ORDER BY fit_status"
    )]
    errors = [dict(row) for row in archive.connection.execute(
        "SELECT dataset, day, error FROM sync_state WHERE status='error' ORDER BY day, dataset"
    )]
    fit_errors = [dict(row) for row in archive.connection.execute(
        "SELECT activity_id, fit_error AS error FROM activities WHERE fit_status='error' ORDER BY activity_id"
    )]
    _print_json({"database": str(archive.path), "coverage": states, "activity_files": fit, "errors": errors, "fit_errors": fit_errors})
    return 0


def _activities(archive: Archive, args: argparse.Namespace) -> int:
    rows = archive.connection.execute(
        """SELECT activity_id, day, json_extract(summary_json, '$.activityType.typeKey') AS type,
                  json_extract(summary_json, '$.activityName') AS name, fit_status
           FROM activities ORDER BY day DESC, activity_id DESC LIMIT ? OFFSET ?""",
        (args.limit, args.offset),
    )
    _print_json([dict(row) for row in rows])
    return 0


def _records(archive: Archive, args: argparse.Namespace) -> int:
    row = archive.connection.execute(
        "SELECT fit_status FROM activities WHERE activity_id=?", (args.activity_id,)
    ).fetchone()
    if row is None:
        print("Activity not found in this archive.", file=sys.stderr)
        return 1
    if row["fit_status"] != "ok":
        print(f"Activity has no decoded FIT records (status: {row['fit_status']}).", file=sys.stderr)
        return 1
    columns = "activity_id, record_index, timestamp, heart_rate_bpm, power_w, cadence_rpm, distance_m, enhanced_speed_mps"
    if args.full:
        columns += ", data_json"
    rows = [dict(row) for row in archive.connection.execute(
        f"SELECT {columns} FROM activity_records WHERE activity_id=? ORDER BY record_index LIMIT ? OFFSET ?",
        (args.activity_id, args.limit, args.offset),
    )]
    if args.format == "csv":
        writer = csv.DictWriter(sys.stdout, fieldnames=columns.split(", "), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    else:
        if args.full:
            for record in rows:
                record["data"] = json.loads(record.pop("data_json"))
        _print_json(rows)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    # Restrict SQLite's journal files too, without modifying the parent shell.
    os.umask(0o077)
    try:
        archive = Archive(args.data_dir)
    except (OSError, ValueError) as error:
        print(f"Cannot open archive ({type(error).__name__}).", file=sys.stderr)
        return 1
    try:
        if args.command == "sync":
            return _sync(archive, args)
        if args.command == "status":
            return _status(archive)
        if args.command == "path":
            print(archive.path)
            return 0
        if args.command == "activities":
            return _activities(archive, args)
        if args.command == "records":
            return _records(archive, args)
        if args.command == "health":
            row = archive.connection.execute(
                "SELECT data_json FROM daily_data WHERE dataset=? AND day=?",
                (args.dataset, args.day.isoformat()),
            ).fetchone()
            if row is None:
                print("No stored response for that dataset and date.", file=sys.stderr)
                return 1
            _print_json(json.loads(row["data_json"]))
            return 0
        if args.command == "export-original":
            row = archive.connection.execute(
                "SELECT original_zip FROM activities WHERE activity_id=?", (args.activity_id,)
            ).fetchone()
            if row is None or row["original_zip"] is None:
                print("No original file found for that activity.", file=sys.stderr)
                return 1
            try:
                with args.path.open("xb") as output:
                    output.write(row["original_zip"])
            except OSError as error:
                print(f"Could not write original file ({type(error).__name__}).", file=sys.stderr)
                return 1
            print(f"Saved original activity ZIP to {args.path}.")
            return 0
        raise AssertionError("Unknown command")
    finally:
        archive.close()


if __name__ == "__main__":
    raise SystemExit(main())

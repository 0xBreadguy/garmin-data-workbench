"""Command-line interface for a local Garmin archive."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import os
import sqlite3
import subprocess
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from filelock import FileLock, Timeout
from garmin_personal_api import (
    GarminPersonalApiClient,
    PersonalApiAuthenticator,
    resolve_api_key,
)

from .archive import Archive, default_data_dir, now
from .preferences import clean_profile, local_today, profile_preferences
from .platforms import shell_command
from .queries import METRICS, METRIC_TITLES, get_day, get_trend, health_response, open_archive
from .api_data import api_catalog, source_data, source_series, snapshot_coverage
from .sources import SOURCES
from .sleep import get_sleep
from .body_battery import get_body_battery
from .sync import DATASETS, SyncStopped, _call, sync
from garmin_personal_api.errors import HttpError


def _error(code: str, message: str, exit_code: int = 1) -> int:
    """Keep diagnostics separate from successful command output."""
    print(json.dumps({"error": {"code": code, "message": message}}, ensure_ascii=False), file=sys.stderr)
    return exit_code


class CLIArgumentParser(argparse.ArgumentParser):
    def _check_value(self, action, value):
        # argparse normally echoes invalid values, which may be pasted secrets.
        if action.choices is not None and value not in action.choices:
            choices = ", ".join(str(choice) for choice in action.choices)
            raise argparse.ArgumentError(action, f"Choose one of: {choices}")

    def error(self, message: str) -> None:
        if "ignored explicit argument" in message:
            message = message.split(": ignored explicit argument", 1)[0] + ": does not accept a value; use COMMAND --help."
        if message.startswith("ambiguous option:"):
            message = "Ambiguous option; use the full option name from COMMAND --help."
        if message.startswith("unrecognized arguments:"):
            message = "Unrecognized arguments; use --help or COMMAND --help. Put --data-dir before the command."
        self.exit(_error("invalid_argument", message, 2))


def _date(value: str) -> date:
    try:
        parsed = date.fromisoformat(value)
        if parsed.isoformat() != value:
            raise ValueError
        return parsed
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use a date in YYYY-MM-DD format") from error


def _number(value: str) -> float:
    try:
        return float(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Must be a number") from error


def _positive(value: str) -> int:
    try:
        number = int(value)
        if not 1 <= number <= 2**63 - 1:
            raise ValueError
        return number
    except ValueError as error:
        raise argparse.ArgumentTypeError("Must be a positive integer no greater than 9223372036854775807") from error


def _nonnegative(value: str) -> int:
    try:
        number = int(value)
        if not 0 <= number <= 2**63 - 1:
            raise ValueError
        return number
    except ValueError as error:
        raise argparse.ArgumentTypeError("Must be a non-negative integer no greater than 9223372036854775807") from error


def parser() -> argparse.ArgumentParser:
    result = CLIArgumentParser(
        description="Download and query your own Garmin data locally.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Start here (no archive or key needed):
  garmin-archive agent-guide           Installed agent instructions and examples
  garmin-archive metrics               Interpreted metric names, source units and titles
  garmin-archive api-catalog           Native sources; add SOURCE to discover fields
  garmin-archive version               Package/build revision, OS and chart availability

Archive selection: put --data-dir DIRECTORY before the command.
Read-only queries: day, trend, sleep, body-battery, status, activities, health,
records, source-data, source-series. They never sync or create an archive.
Exports: chart and export-original write new files and never overwrite.
Live/configuration: sync uses credentials/network; install also connects clients
and may schedule; connect registers clients; setup changes the macOS schedule;
save-key authenticates and saves a key unless --dry-run is selected.
Use COMMAND --help for arguments. Read output is JSON; parser/read errors are
JSON on stderr (exit 2 invalid input, 1 operational failure, 3 not found).
""")
    from importlib.metadata import PackageNotFoundError, version
    try:
        package_version = version("garmin-data-workbench")
    except PackageNotFoundError:
        package_version = "unknown"
    result.add_argument("--version", action="version", version=f"garmin-data-workbench {package_version}")
    result.add_argument(
        "--data-dir", type=Path, default=default_data_dir(),
        help="Private archive directory (default: XDG_DATA_HOME/garmin-extraction or ~/.local/share/garmin-extraction)",
    )
    commands = result.add_subparsers(dest="command", required=True)

    commands.add_parser("version", help="Print package/build provenance, OS and chart availability as JSON; no archive needed")
    commands.add_parser("metrics", help="List interpreted metric names, titles, datasets and source units as JSON; no archive needed")

    sync_parser = commands.add_parser("sync", help="Sync an inclusive date range using live Garmin requests and credentials")
    sync_parser.add_argument("--from", dest="start", type=_date, default=None, help="Start date, YYYY-MM-DD (default: six days ago)")
    sync_parser.add_argument("--to", dest="end", type=_date, default=None, help="End date, YYYY-MM-DD (default: today)")
    sync_parser.add_argument("--refresh", action="store_true", help="Re-fetch completed days in the selected range")
    sync_parser.add_argument("--pause", type=_number, default=0.3, help="Seconds between requests (default: 0.3)")
    sync_parser.add_argument("--catch-up", action="store_true", help="Resume from the last successful catch-up run; suitable for scheduling")
    sync_parser.add_argument("--lookback-days", type=_positive, default=7, help="Days to recheck for late uploads during catch-up (1–31; default: 7)")

    setup = commands.add_parser("setup", help="Configure or change scheduled sync on macOS")
    setup.add_argument("--every-hours", type=_positive, help="Hours between scheduled syncs (1–168)")
    setup.add_argument("--lookback-days", type=_positive, default=2, help="Recent days to recheck each run (1–31; default: 2)")

    install = commands.add_parser("install", help="Live sync, prepare credentials, connect an assistant and optionally schedule")
    frequency = install.add_mutually_exclusive_group()
    frequency.add_argument("--every-hours", type=_positive, help="Hours between scheduled syncs (1–168)")
    frequency.add_argument("--manual", action="store_true", help="Use manual sync; leave any existing schedule alone")
    install.add_argument("--lookback-days", type=_positive, default=2, help="Recent days to recheck each run (1–31; default: 2)")
    install.add_argument("--client", choices=("codex", "claude", "chatgpt", "other", "shell"), default="codex",
                         help="Assistant to connect (default: codex)")

    connect = commands.add_parser("connect", help="Probe local MCP and register a client for an existing archive; no Garmin sync")
    connect.add_argument("--client", choices=("codex", "claude", "chatgpt", "other", "shell"), default="codex")

    guide = commands.add_parser("assistant-guide", help="Print a handoff for your assistant")
    guide.add_argument("--client", choices=("dot", "codex", "claude", "muse", "other"), default="dot")
    agent = commands.add_parser("agent-guide", help="Read installed query, visualization and interpretation guidance; no archive needed")
    agent.add_argument('--client', choices=('dot', 'codex', 'claude', 'muse', 'other'),
                       help='Append the assistant-guide handoff for this client; the generic guide is always included')
    commands.add_parser("setup-receipt", help="Read installation, archive and schedule evidence as JSON without syncing")
    routine = commands.add_parser("routine-template", help="Print a provider-neutral sync routine template as JSON; schedules nothing")
    routine.add_argument("--lookback-days", type=_positive, default=2)

    key = commands.add_parser(
        "save-key", help="Validate and save a key from a private secret file; makes live Garmin requests",
        description="Read a privately delivered secret file, validate it through live Garmin authentication "
                    "and a profile request, then save an owner-only key file without overwriting. "
                    "Does not sync, connect a client or schedule anything.",
    )
    key.add_argument("--from-file", type=Path, required=True, help="Private file supplied through the host's secure secret facility (never a key value)")

    key.add_argument('--dry-run', action='store_true', help='Check local source shape/privacy and destination only; no authentication, cache or key writes')
    key.add_argument('--timeout', type=_number, default=15, help='Live validation timeout per request in seconds (1–120; default 15)')

    day = commands.add_parser("day", help="Read a day overview as JSON without syncing (default: Garmin profile's today)")
    day.add_argument("day", nargs="?", type=_date)
    trend = commands.add_parser("trend", help="Read 1–90 days of a metric as JSON without syncing")
    trend.add_argument("metric", choices=sorted(METRICS))
    trend.add_argument("--from", dest="start", type=_date, help="Start date (default: six days before end)")
    trend.add_argument("--to", dest="end", type=_date, help="End date (default: Garmin profile's today)")
    sleep = commands.add_parser("sleep", help="Read a bounded sleep summary as JSON: stages, score, stress, naps and source times")
    sleep.add_argument("--from", dest="start", type=_date, help="First of 1–90 inclusive dates (default: six days before end)")
    sleep.add_argument("--to", dest="end", type=_date, help="Last date (default: Garmin profile's today, possibly incomplete)")
    battery = commands.add_parser("body-battery", help="Read daily Body Battery charge/drain and descriptor-aware observed levels as JSON")
    battery.add_argument("--from", dest="start", type=_date, help="First of 1–90 inclusive dates (default: six days before end)")
    battery.add_argument("--to", dest="end", type=_date, help="Last date (default: Garmin profile's today, possibly incomplete)")

    chart = commands.add_parser("chart", help="Render a branded archive trend as a PNG (requires charts extra)",
        description="Read an existing archive and render a branded PNG without syncing. "
                    "Example: garmin-archive --data-dir /private/archive chart sleep_duration "
                    "--from 2026-01-01 --to 2026-01-30 --output sleep.png. "
                    "The global --data-dir option goes before chart. Sleep seconds are displayed as hours.")
    chart.add_argument("metric", choices=sorted([*METRICS, "sleep"]), help="A metric, or sleep for stages/duration and score panels")
    chart.add_argument("--from", dest="start", type=_date)
    chart.add_argument("--to", dest="end", type=_date)
    chart.add_argument("--output", required=True, type=Path, help="New PNG file; existing files are not overwritten")
    chart.add_argument("--json", action="store_true", help="Print the saved PNG path and shared caption, coverage and freshness metadata as JSON")
    chart.add_argument("--synthetic", action="store_true", help="Label generated/demo data visibly and identify its source as synthetic")
    chart.add_argument("--layout", choices=("chat", "wide"), default="chat", help="Readable chat/phone layout or wide report layout (default: chat)")
    commands.add_parser("brand", help="Print shared brand colors, rules and local logo paths as JSON; no archive needed")

    commands.add_parser("status", help="Show archive coverage and sync errors as JSON",
                        description="Read existing archive coverage and sync errors as JSON without syncing or modifying it.")
    commands.add_parser("path", help="Print the SQLite database path without opening or creating it")
    activities = commands.add_parser("activities", help="List stored activity summaries as JSON",
                                    description="List stored activity summaries as JSON without syncing or modifying the archive.")
    activities.add_argument("--limit", type=_positive, default=20, help="Page size, 1–10000 (default: 20); continue with --offset")
    activities.add_argument("--offset", type=_nonnegative, default=0)

    health = commands.add_parser("health", help="Print raw stored daily JSON; use --metadata to mask failed-refresh values")
    health.add_argument("dataset", choices=sorted(DATASETS))
    health.add_argument("day", type=_date)
    health.add_argument("--metadata", action="store_true", help="Include refresh status/fetch times and mask retained data after a failed refresh")

    catalog = commands.add_parser("api-catalog", help="Discover all Personal API sources and native response fields; no archive needed")
    catalog.add_argument("dataset", nargs="?", default="", choices=["", *SOURCES])
    catalog.add_argument("--pointer", default="", help="JSON Pointer; use * for an array item schema")
    catalog.add_argument("--limit", type=_positive, default=100, help="Page size, 1–100 (default: 100); follow next_offset")
    catalog.add_argument("--offset", type=_nonnegative, default=0)
    source = commands.add_parser("source-data", help="Page any archived Personal API response field, including nested arrays")
    source.add_argument("dataset", choices=list(SOURCES))
    source.add_argument("--day", type=_date, help="Required for daily sources; omit for current/activity sources")
    source.add_argument("--activity-id", type=_positive, default=0, help="Required for activity/list/file sources; omit for daily/current sources")
    source.add_argument("--pointer", default="", help="JSON Pointer; empty for root, numeric indices for array items")
    source.add_argument("--limit", type=_positive, default=100, help="Page size, 1–100 (default: 100); follow next_offset")
    source.add_argument("--offset", type=_nonnegative, default=0)
    source.add_argument("--include-location", action="store_true", help="Explicitly include native coordinates; omitted by default")
    series = commands.add_parser("source-series", help="Read a native scalar field over 1–90 request dates without inferring an aggregation")
    series.add_argument("dataset", choices=list(DATASETS))
    series.add_argument("pointer", help="JSON Pointer to a scalar field")
    series.add_argument("--from", dest="start", type=_date)
    series.add_argument("--to", dest="end", type=_date)

    records = commands.add_parser("records", help="Show decoded time-series records as JSON (or CSV with --format csv)",
                                 description="Read decoded time-series records as JSON, or CSV with --format csv, without modifying the archive.")
    records.add_argument("activity_id", type=_positive)
    records.add_argument("--limit", type=_positive, default=100, help="Page size, 1–10000 (default: 100); continue with --offset")
    records.add_argument("--offset", type=_nonnegative, default=0)
    records.add_argument("--format", choices=("json", "csv"), default="json", help="Output format (default: json)")
    records.add_argument("--full", action="store_true", help="Include complete decoded fields, including location when recorded")

    original = commands.add_parser("export-original", help="Export original ZIP to a new file; may contain GPS; never overwrites")
    original.add_argument("activity_id", type=_positive)
    original.add_argument("path", type=Path)
    # Keep detailed help useful when an agent starts at a subcommand.
    for name, command_parser in commands.choices.items():
        if name != "chart":  # Chart help/output is maintained by its feature owner.
            command_parser.epilog = (
                "Put --data-dir DIRECTORY before the command. Dates use YYYY-MM-DD. "
                "For examples, units, freshness and safe query guidance: garmin-archive agent-guide. "
                "Discover metrics with garmin-archive metrics and native fields with api-catalog."
            )
    return result


def _print_json(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def _sync(archive: Archive, args: argparse.Namespace) -> int:
    end = args.end or date.today()
    start = args.start or end - timedelta(days=6)
    if (args.end is not None and start > end) or not math.isfinite(args.pause) or args.pause < 0:
        print("Start must not be after end, and pause must not be negative.", file=sys.stderr)
        return 2
    if not 1 <= getattr(args, "lookback_days", 7) <= 31:
        print("Lookback must be between 1 and 31 days.", file=sys.stderr)
        return 2
    if args.catch_up and args.end:
        print("--catch-up always syncs through today; omit --to.", file=sys.stderr)
        return 2
    try:
        # The lock covers the checkpoint, authentication and all network work.
        # A process crash releases the OS lock; the file itself is harmless.
        with FileLock(str(archive.data_dir / "sync.lock"), timeout=0, mode=0o600):
            return _sync_locked(archive, args, start, end, use_profile_default=args.end is None)
    except Timeout:
        print("Another sync is already running for this archive.", file=sys.stderr)
        return 1


def _sync_locked(archive: Archive, args: argparse.Namespace, start: date, end: date, *, use_profile_default: bool = False) -> int:
    row = None
    if args.catch_up:
        row = archive.connection.execute("SELECT * FROM catchup_state WHERE id=1").fetchone()
        if row and args.start:
            print("--from sets the initial catch-up date only; it has already been set.", file=sys.stderr)
            return 2
        if not use_profile_default and row and row["last_success_day"] and date.fromisoformat(row["last_success_day"]) > end:
            print("Catch-up checkpoint is in the future; check the system date.", file=sys.stderr)
            return 1
        if row is None:
            with archive.connection:
                archive.connection.execute(
                    "INSERT INTO catchup_state (id, start_day) VALUES (1, ?)", (start.isoformat(),)
                )
        else:
            # Recheck a week for late uploads, and include all time missed while offline.
            overlap = timedelta(days=getattr(args, "lookback_days", 7) - 1)
            start = (max(date.fromisoformat(row["start_day"]),
                         min(end - overlap, date.fromisoformat(row["last_success_day"]) - overlap))
                     if row["last_success_day"] else date.fromisoformat(row["start_day"]))
        if not use_profile_default and start > end:
            print("Catch-up checkpoint is in the future; check the system date.", file=sys.stderr)
            return 1
        with archive.connection:
            archive.connection.execute(
                "UPDATE catchup_state SET last_attempt_at=?, last_result='running' WHERE id=1", (now(),)
            )
    # The official client logs URLs and HTTP errors can contain response bodies.
    logging.disable(logging.CRITICAL)
    try:
        with PersonalApiAuthenticator() as auth:
            token = auth.obtain_token(resolve_api_key())
        with GarminPersonalApiClient(token.access_token) as client:
            warning = None
            try:
                profile = _call(client.get_user_profile_settings, args.pause, time.sleep)
            except SyncStopped as error:
                archive.mark_snapshot_error("profile", "current", str(error))
                raise
            except (HttpError, ValueError, TypeError) as error:
                archive.mark_snapshot_error("profile", "current", f"HTTP {error.status_code}" if isinstance(error, HttpError) else type(error).__name__)
                # Keep the last successful preferences if a nonfatal request fails.
                warning = f"Profile settings unavailable ({type(error).__name__}); using cached settings or host date."
            else:
                archive.save_snapshot("profile", "current", profile)
                try:
                    archive.save_preferences(*clean_profile(profile))
                except ValueError:
                    warning = "Profile response has no usable defaults; using cached settings or host date."
            garmin_today, _ = local_today(profile_preferences(archive.connection))
            if use_profile_default:
                end = garmin_today
                if args.catch_up and row is not None:
                    if row["last_success_day"]:
                        if date.fromisoformat(row["last_success_day"]) > end:
                            raise ValueError("Catch-up checkpoint is in the future")
                        overlap = timedelta(days=getattr(args, "lookback_days", 7) - 1)
                        start = max(date.fromisoformat(row["start_day"]),
                                    min(end - overlap, date.fromisoformat(row["last_success_day"]) - overlap))
                    else:
                        start = date.fromisoformat(row["start_day"])
                elif args.start is None:
                    start = end - timedelta(days=6)
                    if args.catch_up:
                        with archive.connection:
                            archive.connection.execute("UPDATE catchup_state SET start_day=? WHERE id=1", (start.isoformat(),))
                if start > end:
                    raise ValueError("Start date is after Garmin's current date")
            report = sync(archive, client, start, end, refresh=args.refresh, pause=args.pause, today=garmin_today,
                          profile_checked=True)
    except Exception as error:  # noqa: BLE001 -- keep private API response bodies out of the terminal
        if args.catch_up:
            with archive.connection:
                archive.connection.execute("UPDATE catchup_state SET last_result='error' WHERE id=1")
        print(f"Sync could not start ({type(error).__name__}). Check your key and connection.", file=sys.stderr)
        return 1
    if args.catch_up:
        with archive.connection:
            if report.errors:
                archive.connection.execute("UPDATE catchup_state SET last_result='error' WHERE id=1")
            else:
                archive.connection.execute(
                    "UPDATE catchup_state SET last_result='ok', last_success_day=? WHERE id=1", (end.isoformat(),)
                )
    _print_json({
        "range": {"from": start.isoformat(), "to": end.isoformat()},
        "health_requests_succeeded": report.checked,
        "completed_days_skipped": report.skipped,
        "activities_seen": report.activities,
        "activity_files_decoded": report.decoded,
        "source_snapshots_succeeded": report.snapshots,
        "non_fit_originals": report.unsupported,
        "stopped": report.stopped,
        "errors": report.errors,
        "profile_warning": warning,
    })
    return 1 if report.errors else 0


def _status(db: sqlite3.Connection, path: Path) -> int:
    states = [dict(row) for row in db.execute(
        """SELECT dataset, status, COUNT(*) AS days, MIN(day) AS first_day,
                  MAX(day) AS last_day, MAX(updated_at) AS last_attempt
           FROM sync_state GROUP BY dataset, status ORDER BY dataset, status"""
    )]
    fit = [dict(row) for row in db.execute(
        "SELECT fit_status, COUNT(*) AS activities FROM activities GROUP BY fit_status ORDER BY fit_status"
    )]
    errors = [dict(row) for row in db.execute(
        "SELECT dataset, day, error FROM sync_state WHERE status='error' ORDER BY day, dataset"
    )]
    fit_errors = [dict(row) for row in db.execute(
        "SELECT activity_id, fit_error AS error FROM activities WHERE fit_status='error' ORDER BY activity_id"
    )]
    catchup = db.execute("SELECT * FROM catchup_state WHERE id=1").fetchone()
    from .provenance import archive_provenance
    _print_json({"archive_provenance": archive_provenance(db), "database": str(path), "catch_up": dict(catchup) if catchup else None, "coverage": states,
                 "source_snapshots": snapshot_coverage(db), "activity_files": fit, "errors": errors, "fit_errors": fit_errors})
    return 0


def _activities(db: sqlite3.Connection, args: argparse.Namespace) -> int:
    rows = db.execute(
        """SELECT activity_id, day, json_extract(summary_json, '$.activityType.typeKey') AS type,
                  json_extract(summary_json, '$.activityName') AS name, fit_status
           FROM activities ORDER BY day DESC, activity_id DESC LIMIT ? OFFSET ?""",
        (args.limit, args.offset),
    )
    _print_json([dict(row) for row in rows])
    return 0


def _records(db: sqlite3.Connection, args: argparse.Namespace) -> int:
    row = db.execute(
        "SELECT fit_status FROM activities WHERE activity_id=?", (args.activity_id,)
    ).fetchone()
    if row is None:
        return _error("not_found", "Activity not found in this archive.", 3)
    if row["fit_status"] != "ok":
        return _error("records_unavailable", "Activity has no decoded FIT records; inspect status for sync or decoding failures.")
    columns = "activity_id, record_index, timestamp, heart_rate_bpm, power_w, cadence_rpm, distance_m, enhanced_speed_mps"
    if args.full:
        columns += ", data_json"
    rows = [dict(row) for row in db.execute(
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


def _export_original(db: sqlite3.Connection, args: argparse.Namespace) -> int:
    row = db.execute(
        "SELECT original_zip FROM activities WHERE activity_id=?", (args.activity_id,)
    ).fetchone()
    if row is None or row["original_zip"] is None:
        return _error("not_found", "No original file found for that activity.", 3)
    try:
        # The archive is read-only; protect the exported copy without changing
        # the caller's umask. Exclusive creation preserves existing files.
        with open(args.path, "xb", opener=lambda path, flags: os.open(path, flags, 0o600)) as output:
            output.write(row["original_zip"])
    except OSError:
        return _error("output_error", "Could not write original file; check the destination and permissions. Existing files are not overwritten.")
    print(f"Saved original activity ZIP to {args.path}.")
    return 0


def _read(args: argparse.Namespace) -> int:
    """Query an existing archive without creating, migrating or syncing it."""
    try:
        with open_archive(args.data_dir) as db:
            if args.command == "source-data":
                _print_json(source_data(db, args.dataset, args.day.isoformat() if args.day else "", args.activity_id,
                    args.pointer, limit=args.limit, offset=args.offset, include_location=args.include_location))
            elif args.command == "source-series":
                _print_json(source_series(db, args.dataset, args.pointer,
                    args.start.isoformat() if args.start else "", args.end.isoformat() if args.end else ""))
            elif args.command == "day":
                _print_json(get_day(db, args.day.isoformat() if args.day else ""))
            elif args.command in {"trend", "chart", "sleep", "body-battery"}:
                start, end = args.start.isoformat() if args.start else "", args.end.isoformat() if args.end else ""
                result = (get_body_battery(db, start, end) if args.command == "body-battery" else
                          get_sleep(db, start, end) if args.command == "sleep" or args.metric == "sleep" else
                          get_trend(db, args.metric, start, end))
                if args.command == "chart":
                    from .charts import render_trend
                    try:
                        render_trend(result, args.output, synthetic=args.synthetic, layout=args.layout)
                    except ImportError:
                        return _error("dependency_unavailable", "Charts require the optional charts extra; see docs/VISUALIZATION.md.", 2)
                    except OSError:
                        return _error("output_error", "Could not write chart; choose a new writable PNG path. Existing files are not overwritten.")
                    if args.json:
                        from .chart_delivery import chart_metadata
                        metadata = chart_metadata(result, synthetic=args.synthetic, layout=args.layout)
                        metadata["output_path"] = str(args.output)
                        metadata["delivery"] = "PNG file saved; host attachment and display must be verified separately."
                        _print_json(metadata)
                    else:
                        print(f"Chart saved to {args.output}")
                else:
                    _print_json(result)
            elif args.command == "status":
                return _status(db, args.data_dir.expanduser() / "archive.sqlite3")
            elif args.command == "activities":
                return _activities(db, args)
            elif args.command == "records":
                return _records(db, args)
            elif args.command == "export-original":
                return _export_original(db, args)
            elif args.command == "health":
                if args.metadata:
                    _print_json(health_response(db, args.dataset, args.day.isoformat()))
                    return 0
                row = db.execute(
                    "SELECT data_json FROM daily_data WHERE dataset=? AND day=?",
                    (args.dataset, args.day.isoformat()),
                ).fetchone()
                if row is None:
                    return _error("not_found", "No stored response for that dataset and date.", 3)
                _print_json(json.loads(row["data_json"]))
            else:
                raise AssertionError("Unknown read command")
        return 0
    except json.JSONDecodeError:
        return _error("invalid_data", "Stored response is not valid JSON; check the archive and sync status.")
    except OverflowError:
        return _error("invalid_argument", "Date or integer is outside the supported range; supply explicit --from and --to dates.", 2)
    except ValueError as error:
        return _error("invalid_argument", str(error), 2)
    except (OSError, sqlite3.Error):
        return _error("archive_unavailable", "Cannot read existing archive; check --data-dir, permissions and archive compatibility, and sync first if needed.")


def _install(archive: Archive, args: argparse.Namespace) -> int:
    """Initialize the archive before connecting the chosen client."""
    from .install import ensure_key, scheduled_key_available
    from .schedule import configure_schedule

    hours = args.every_hours
    if not args.manual and hours is None:
        if not sys.stdin.isatty():
            print("Run install interactively or pass --every-hours or --manual.", file=sys.stderr)
            return 2
        try:
            answer = input("How often should Garmin data update? Enter hours [6], or 0 for manual: ").strip()
            hours = int(answer) if answer else 6
        except (EOFError, KeyboardInterrupt, ValueError):
            print("Setup cancelled; enter a whole number of hours.", file=sys.stderr)
            return 2
    if hours == 0:
        hours = None
    if (hours is not None and not 1 <= hours <= 168) or not 1 <= args.lookback_days <= 31:
        print("Frequency must be 1–168 hours, and lookback must be 1–31 days.", file=sys.stderr)
        return 2

    try:
        key_status = ensure_key()
    except (OSError, RuntimeError, KeyboardInterrupt) as error:
        print(f"Could not prepare Garmin key: {error}", file=sys.stderr)
        return 1
    print("Garmin key ready (" + key_status + "). Syncing the archive; the first sync covers the last seven days.")
    sync_args = argparse.Namespace(start=None, end=None, refresh=False, pause=0.3,
                                   catch_up=True, lookback_days=args.lookback_days)
    if _sync(archive, sync_args):
        print("Initial sync did not finish; fix the error above and run install again.", file=sys.stderr)
        return 1

    schedule_error = None
    if hours is None:
        print("Manual sync selected. Any existing schedule was left unchanged.")
    elif sys.platform != "darwin":
        schedule_error = "Automatic schedule setup currently supports macOS only; configure your OS scheduler or rerun with --manual."
    elif not scheduled_key_available():
        schedule_error = ("Scheduled sync cannot use this shell-only key. Save the same key in "
                          "~/.config/garmin/connect-personal-api-key with owner-only permissions, then rerun install.")
    else:
        try:
            configure_schedule(archive.data_dir, hours, args.lookback_days)
            print(f"Scheduled sync every {hours} hours; rechecking {args.lookback_days} recent days.")
        except (OSError, RuntimeError, ValueError) as error:
            schedule_error = f"Could not configure scheduled sync: {error}"

    connection_result = _connect(archive, args.client)
    from .onboarding import setup_receipt
    print("Setup verification receipt (assistant query and recurring execution still require independent verification):")
    _print_json(setup_receipt(archive.data_dir))
    if schedule_error:
        print(schedule_error, file=sys.stderr)
        return 1
    if connection_result == 2:
        print("Local setup is complete; the assistant connection still needs the steps above.")
    return connection_result


def _connect(archive: Archive, client: str) -> int:
    from .install import probe_server, register_claude, register_codex, verify_codex_discovery
    from .platforms import installed_executable

    command = shell_command([str(installed_executable("garmin-archive")), "agent-guide"])
    print(f"Before answering Garmin questions, read the installed guide: {command}")
    if client == "shell":
        from .install import assistant_guide
        print(assistant_guide("other", data_dir=archive.data_dir))
        print("Same-host CLI selected; verify an actual archive question in your assistant.")
        return 0

    try:
        probe_server(archive.data_dir)
        print("Local MCP server can read the archive.")
        if client == "codex":
            registration = register_codex(archive.data_dir)
            verify_codex_discovery()
            if registration == "existing":
                print("Existing Codex registration was preserved; confirm it points to this archive if you use a custom path.")
            else:
                print("Codex registration added; a fresh Codex runtime discovered its tools.")
            print('Start a fresh Codex conversation and ask: "How did my sleep change over the last week?"')
        elif client == "claude":
            registration = register_claude(archive.data_dir)
            if registration == "existing":
                print("Existing Claude Code registration was preserved; confirm it points to this archive if you use a custom path.")
            else:
                print("Claude Code registration added. Its tool connection has not been checked in a Claude conversation.")
            print("Start a fresh Claude Code session, check /mcp, and ask about your Garmin data.")
        elif client == "chatgpt":
            print("This command has not configured or verified a ChatGPT connection. A regular ChatGPT conversation needs a separate MCP connection.")
            print("If Codex is configured too, connect this computer to your dot and ask for a local Codex task; this route is unverified.")
            print("Run `garmin-archive assistant-guide --client dot` for a handoff to give your dot.")
            print("For direct ChatGPT MCP access, follow https://developers.openai.com/api/docs/guides/secure-mcp-tunnels")
            print("to create a tunnel, run its client with garmin-archive-mcp, and add it in ChatGPT. Availability depends on your account.")
            return 2
        else:
            from .install import executable_path
            command = shell_command([str(executable_path()), "--data-dir", str(archive.data_dir.resolve())])
            if sys.platform == "win32":
                print("The following launch command uses PowerShell syntax.")
            print(f"Configure your MCP client to launch: {command}")
            print("Start a fresh client session and test an archive question.")
            return 2
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        print(f"Could not finish the assistant connection: {error}", file=sys.stderr)
        return 1
    return 0


def _validate_args(args: argparse.Namespace) -> None:
    """Reject locally decidable input errors before archive creation or auth."""
    if hasattr(args, "lookback_days") and not 1 <= args.lookback_days <= 31:
        raise ValueError("--lookback-days must be between 1 and 31")
    if getattr(args, "every_hours", None) is not None and not 1 <= args.every_hours <= 168:
        raise ValueError("--every-hours must be between 1 and 168")
    if args.command in {"install", "setup"} and args.every_hours is None and not getattr(args, "manual", False) and not sys.stdin.isatty():
        raise ValueError("Choose --every-hours (or install --manual) when running noninteractively")
    if args.command == "sync":
        if not math.isfinite(args.pause) or args.pause < 0:
            raise ValueError("--pause must be finite and nonnegative")
        if args.catch_up and args.end is not None:
            raise ValueError("--catch-up always syncs through today; omit --to")
    if args.command == "save-key" and (not math.isfinite(args.timeout) or not 1 <= args.timeout <= 120):
        raise ValueError("--timeout must be between 1 and 120 seconds")
    start, end = getattr(args, "start", None), getattr(args, "end", None)
    if start is not None and end is not None:
        if start > end:
            raise ValueError("Date range must be between 1 and 90 days, inclusive" if args.command != "sync" else "--from must not be after --to")
        if args.command != "sync" and (end - start).days >= 90:
            raise ValueError("Date range must be between 1 and 90 days, inclusive")
    if start is None and end is not None and end < date.min + timedelta(days=6):
        raise ValueError("Default seven-day range precedes year 1; supply --from explicitly")
    if hasattr(args, "limit"):
        maximum = 100 if args.command in {"api-catalog", "source-data"} else 10000
        if args.limit > maximum:
            raise ValueError(f"--limit must be between 1 and {maximum}; use --offset to page")
    if args.command == "source-data":
        scope = SOURCES[args.dataset].scope
        if scope == "daily" and (args.day is None or args.activity_id):
            raise ValueError("Daily sources require --day YYYY-MM-DD and omit --activity-id")
        if scope != "daily" and args.day is not None:
            raise ValueError("Current/activity sources omit --day")
        if scope == "current" and args.activity_id:
            raise ValueError("Current sources omit --activity-id")
        if scope not in {"daily", "current"} and not args.activity_id:
            raise ValueError("Activity/list/file sources require --activity-id")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        _validate_args(args)
    except ValueError as error:
        return _error("invalid_argument", str(error), 2)
    if args.command == "version":
        from .onboarding import installation_info
        _print_json(installation_info())
        return 0
    if args.command == "metrics":
        _print_json({"metrics": [{"name": name, "title": METRIC_TITLES[name], "dataset": dataset, "unit": unit}
                                for name, (dataset, _path, unit) in sorted(METRICS.items())],
                     "units": "Source units; distance also has profile-based display units in query results.",
                     "native_fields": "Use api-catalog for native fields; interpreted metrics may use fallbacks/aggregation. See agent-guide."})
        return 0
    if args.command == "api-catalog":
        try:
            _print_json(api_catalog(args.dataset, args.pointer, limit=args.limit, offset=args.offset))
        except ValueError as error:
            return _error("invalid_argument", str(error), 2)
        return 0
    if args.command == "agent-guide":
        from .guidance import agent_guide
        print(agent_guide())
        if args.client:
            from .install import assistant_guide
            print(assistant_guide(args.client, data_dir=args.data_dir, include_guide=False))
        return 0
    if args.command == "setup-receipt":
        from .onboarding import setup_receipt
        _print_json(setup_receipt(args.data_dir))
        return 0
    if args.command == "routine-template":
        from .onboarding import routine_template
        try:
            _print_json(routine_template(args.data_dir, args.lookback_days))
        except ValueError as error:
            return _error("invalid_argument", str(error), 2)
        return 0
    if args.command == "brand":
        from .brand import get_brand
        _print_json(get_brand())
        return 0
    if args.command == "assistant-guide":
        from .install import assistant_guide
        print(assistant_guide(args.client, data_dir=args.data_dir))
        return 0
    if args.command == "save-key":
        from .install import save_key_from_file
        try:
            preflight = save_key_from_file(args.from_file, dry_run=args.dry_run, timeout=args.timeout)
        except (OSError, RuntimeError, KeyboardInterrupt) as error:
            # Never print file contents, paths from OS errors, or response bodies.
            detail = str(error) if isinstance(error, RuntimeError) else type(error).__name__
            print(f"Could not save Garmin key: {detail}", file=sys.stderr)
            return 1
        if args.dry_run:
            _print_json(preflight)
            return 0
        print("Validated key saved to ~/.config/garmin/connect-personal-api-key with owner-only permissions.")
        if "GARMIN_PERSONAL_API_KEY" in os.environ:
            print("GARMIN_PERSONAL_API_KEY is set and takes precedence over the saved file during sync.")
        return 0
    if args.command == "path":
        print(args.data_dir.expanduser() / "archive.sqlite3")
        return 0
    if args.command in {"day", "trend", "sleep", "body-battery", "chart", "status", "activities", "records", "health", "export-original", "source-data", "source-series"}:
        return _read(args)
    if args.command == "connect" and not (args.data_dir.expanduser() / "archive.sqlite3").is_file():
        print("No local archive found; run `garmin-archive install` first.", file=sys.stderr)
        return 1
    # Restrict SQLite's journal files too, without modifying the parent shell.
    os.umask(0o077)
    try:
        archive = Archive(args.data_dir)
    except (OSError, ValueError) as error:
        print(f"Cannot open archive ({type(error).__name__}).", file=sys.stderr)
        return 1
    try:
        if args.command == "install":
            return _install(archive, args)
        if args.command == "connect":
            return _connect(archive, args.client)
        if args.command == "setup":
            from .schedule import configure_schedule
            hours = args.every_hours
            if hours is None:
                if not sys.stdin.isatty():
                    print("Run setup interactively or pass --every-hours.", file=sys.stderr)
                    return 2
                try:
                    answer = input("How often should Garmin data update? Enter hours [6]: ").strip()
                    hours = int(answer) if answer else 6
                except (EOFError, KeyboardInterrupt, ValueError):
                    print("Setup cancelled; enter a whole number of hours.", file=sys.stderr)
                    return 2
            try:
                result = configure_schedule(archive.data_dir, hours, args.lookback_days)
            except (OSError, RuntimeError, ValueError) as error:
                print(f"Could not configure scheduled sync: {error}", file=sys.stderr)
                return 1
            _print_json(result)
            return 0
        if args.command == "sync":
            return _sync(archive, args)
        raise AssertionError("Unknown command")
    finally:
        archive.close()


if __name__ == "__main__":
    raise SystemExit(main())

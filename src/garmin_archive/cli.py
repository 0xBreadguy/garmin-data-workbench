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
from .queries import METRICS, get_day, get_trend, open_archive
from .sync import DATASETS, SyncStopped, _call, sync
from garmin_personal_api.errors import HttpError


def _error(code: str, message: str, exit_code: int = 1) -> int:
    """Keep diagnostics separate from successful command output."""
    print(json.dumps({"error": {"code": code, "message": message}}, ensure_ascii=False), file=sys.stderr)
    return exit_code


class CLIArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.exit(_error("invalid_argument", message, 2))


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
    result = CLIArgumentParser(description="Download and query your own Garmin data locally.")
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
    sync_parser.add_argument("--catch-up", action="store_true", help="Resume from the last successful catch-up run; suitable for scheduling")
    sync_parser.add_argument("--lookback-days", type=_positive, default=7, help="Days to recheck for late uploads during catch-up (1–31; default: 7)")

    setup = commands.add_parser("setup", help="Configure or change scheduled sync on macOS")
    setup.add_argument("--every-hours", type=_positive, help="Hours between scheduled syncs (1–168)")
    setup.add_argument("--lookback-days", type=_positive, default=2, help="Recent days to recheck each run (1–31; default: 2)")

    install = commands.add_parser("install", help="Set up a local archive and connect an assistant")
    frequency = install.add_mutually_exclusive_group()
    frequency.add_argument("--every-hours", type=_positive, help="Hours between scheduled syncs (1–168)")
    frequency.add_argument("--manual", action="store_true", help="Use manual sync; leave any existing schedule alone")
    install.add_argument("--lookback-days", type=_positive, default=2, help="Recent days to recheck each run (1–31; default: 2)")
    install.add_argument("--client", choices=("codex", "claude", "chatgpt", "other"), default="codex",
                         help="Assistant to connect (default: codex)")

    connect = commands.add_parser("connect", help="Connect an assistant to an existing local archive")
    connect.add_argument("--client", choices=("codex", "claude", "chatgpt", "other"), default="codex")

    guide = commands.add_parser("assistant-guide", help="Print a handoff for your assistant")
    guide.add_argument("--client", choices=("dot", "codex", "claude", "muse", "other"), default="dot")

    key = commands.add_parser(
        "save-key", help="Validate and save a key from a private secret file; makes live Garmin requests",
        description="Read a privately delivered secret file, validate it through live Garmin authentication "
                    "and a profile request, then save an owner-only key file without overwriting. "
                    "Does not sync, connect a client or schedule anything.",
    )
    key.add_argument("--from-file", type=Path, required=True, help="Private file supplied through the host's secure secret facility (never a key value)")

    day = commands.add_parser("day", help="Read a day overview as JSON without syncing (default: Garmin profile's today)")
    day.add_argument("day", nargs="?", type=_date)
    trend = commands.add_parser("trend", help="Read 1–90 days of a metric as JSON without syncing")
    trend.add_argument("metric", choices=sorted(METRICS))
    trend.add_argument("--from", dest="start", type=_date, help="Start date (default: six days before end)")
    trend.add_argument("--to", dest="end", type=_date, help="End date (default: Garmin profile's today)")

    chart = commands.add_parser("chart", help="Render an archive trend as a PNG (requires charts extra)")
    chart.add_argument("metric", choices=sorted(METRICS))
    chart.add_argument("--from", dest="start", type=_date)
    chart.add_argument("--to", dest="end", type=_date)
    chart.add_argument("--output", required=True, type=Path, help="New PNG file; existing files are not overwritten")

    commands.add_parser("status", help="Show archive coverage and sync errors as JSON",
                        description="Read existing archive coverage and sync errors as JSON without syncing or modifying it.")
    commands.add_parser("path", help="Print the SQLite database path without opening or creating it")
    activities = commands.add_parser("activities", help="List stored activity summaries as JSON",
                                    description="List stored activity summaries as JSON without syncing or modifying the archive.")
    activities.add_argument("--limit", type=_positive, default=20)
    activities.add_argument("--offset", type=_nonnegative, default=0)

    health = commands.add_parser("health", help="Print a stored daily health response as JSON")
    health.add_argument("dataset", choices=sorted(DATASETS))
    health.add_argument("day", type=_date)

    records = commands.add_parser("records", help="Show decoded time-series records as JSON (or CSV with --format csv)",
                                 description="Read decoded time-series records as JSON, or CSV with --format csv, without modifying the archive.")
    records.add_argument("activity_id", type=_positive)
    records.add_argument("--limit", type=_positive, default=100)
    records.add_argument("--offset", type=_nonnegative, default=0)
    records.add_argument("--format", choices=("json", "csv"), default="json", help="Output format (default: json)")
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
                archive.save_preferences(*clean_profile(profile))
            except SyncStopped:
                raise
            except (HttpError, ValueError, TypeError) as error:
                # Keep the last successful preferences if a nonfatal request fails.
                warning = f"Profile settings unavailable ({type(error).__name__}); using cached settings or host date."
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
            report = sync(archive, client, start, end, refresh=args.refresh, pause=args.pause, today=garmin_today)
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
    _print_json({"database": str(path), "catch_up": dict(catchup) if catchup else None, "coverage": states, "activity_files": fit, "errors": errors, "fit_errors": fit_errors})
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
            if args.command == "day":
                _print_json(get_day(db, args.day.isoformat() if args.day else ""))
            elif args.command in {"trend", "chart"}:
                result = get_trend(db, args.metric, args.start.isoformat() if args.start else "",
                                   args.end.isoformat() if args.end else "")
                if args.command == "chart":
                    from .charts import render_trend
                    try:
                        render_trend(result, args.output)
                    except ImportError:
                        return _error("dependency_unavailable", "Charts require the optional charts extra; see docs/VISUALIZATION.md.", 2)
                    except OSError:
                        return _error("output_error", "Could not write chart; choose a new writable PNG path. Existing files are not overwritten.")
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
    if schedule_error:
        print(schedule_error, file=sys.stderr)
        return 1
    if connection_result == 2:
        print("Local setup is complete; the assistant connection still needs the steps above.")
    return connection_result


def _connect(archive: Archive, client: str) -> int:
    from .install import probe_server, register_claude, register_codex, verify_codex_discovery

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


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "assistant-guide":
        from .install import assistant_guide
        print(assistant_guide(args.client, data_dir=args.data_dir))
        return 0
    if args.command == "save-key":
        from .install import save_key_from_file
        try:
            save_key_from_file(args.from_file)
        except (OSError, RuntimeError, KeyboardInterrupt) as error:
            # Never print file contents, paths from OS errors, or response bodies.
            detail = str(error) if isinstance(error, RuntimeError) else type(error).__name__
            print(f"Could not save Garmin key: {detail}", file=sys.stderr)
            return 1
        print("Validated key saved to ~/.config/garmin/connect-personal-api-key with owner-only permissions.")
        if "GARMIN_PERSONAL_API_KEY" in os.environ:
            print("GARMIN_PERSONAL_API_KEY is set and takes precedence over the saved file during sync.")
        return 0
    if args.command == "path":
        print(args.data_dir.expanduser() / "archive.sqlite3")
        return 0
    if args.command in {"day", "trend", "chart", "status", "activities", "records", "health", "export-original"}:
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

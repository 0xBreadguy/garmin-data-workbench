"""Read-only setup evidence and a printable provider-neutral routine template."""
from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import platform
import sqlite3
import subprocess
from pathlib import Path

from .platforms import installed_executable, shell_command
from .queries import open_archive
from .schedule import schedule_status


def installation_info() -> dict:
    try:
        version = importlib.metadata.version("garmin-data-workbench")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    stamp = Path(__file__).with_name("build_info.json")
    provenance = {"revision": None, "dirty": None}
    root = Path(__file__).resolve().parents[2]
    if (root / ".git").exists():
        try:
            # Git must not inherit the MCP transport's input pipe. On Windows,
            # probing an inherited pipe can block behind the stdio reader.
            provenance = {"revision": subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", "HEAD"], text=True,
                stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5).strip(),
                "dirty": bool(subprocess.check_output(
                    ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=normal"],
                    text=True, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5).strip())}
        except (OSError, subprocess.SubprocessError):
            pass
    elif stamp.is_file():
        provenance = json.loads(stamp.read_text(encoding="utf-8"))
    return {"version": version, "source": provenance, "os": platform.system(),
            "python": platform.python_version(), "charts_available": importlib.util.find_spec("matplotlib") is not None}


def setup_receipt(data_dir: Path) -> dict:
    from .provenance import archive_provenance
    path = data_dir.expanduser().resolve()
    archive = {"status": "unavailable", "coverage": [], "catch_up": None}
    try:
        with open_archive(path) as db:
            coverage = [dict(row) for row in db.execute(
                "SELECT dataset, status, COUNT(*) AS days, MIN(day) AS first_day, MAX(day) AS last_day, "
                "MAX(updated_at) AS last_attempt FROM sync_state GROUP BY dataset, status ORDER BY dataset, status")]
            has_catchup = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='catchup_state'").fetchone()
            row = db.execute("SELECT * FROM catchup_state WHERE id=1").fetchone() if has_catchup else None
            fit_failures = db.execute("SELECT COUNT(*) FROM activities WHERE fit_status='error'").fetchone()[0]
            archive = {"archive_provenance": archive_provenance(db), "status": "readable", "coverage": coverage, "catch_up": dict(row) if row else None,
                       "fit_failures": fit_failures}
    except (OSError, sqlite3.Error):
        pass
    try:
        native_schedule = schedule_status(data_dir=path)
    except (OSError, RuntimeError, subprocess.SubprocessError):
        native_schedule = {"status": "unavailable"}
    return {"installation": installation_info(), "archive_path": str(path), "archive": archive,
            "query_paths": ["same-host CLI", "local stdio MCP with a separately verified client connection"],
            "native_schedule": native_schedule,
            "verification": {"assistant_query": "not_verified_by_receipt", "recurring_execution": "not_verified",
                             "external_routine": "not_inspected"},
            "next_steps": ["Verify an assistant query against the archive and a representative Garmin Connect value.",
                           "If automatic updates were selected, independently verify a scheduled execution can access the key "
                           "and update coverage. A configured schedule or successful manual sync is not that evidence."]}


def routine_template(data_dir: Path, lookback_days: int = 2) -> dict:
    if not 1 <= lookback_days <= 31:
        raise ValueError("Lookback must be between 1 and 31 days")
    args = [str(installed_executable("garmin-archive")), "--data-dir", str(data_dir.expanduser().resolve()),
            "sync", "--catch-up", "--lookback-days", str(lookback_days)]
    return {"created": False, "argv": args, "command": shell_command(args),
            "instructions": ["Obtain the user's update interval and check for existing jobs before creating a routine.",
                "Use the same OS user, persistent archive and privately supplied key. Never include key values in the prompt or command.",
                "A shell-only environment variable may not reach the scheduled process. Verify the host's secret mechanism or saved key without displaying values.",
                "Capture stdout, stderr and exit code separately. Sync runtime errors may be non-JSON; nonzero exit or report errors need attention.",
                "Inspect status after the run for failed datasets, FIT failures and the catch-up checkpoint. Read success is not sync success.",
                "Keep routine output private. Be quiet on success; send failure/expired-key notices only to a destination authorized by the user.",
                "Record actual scheduler execution and archive freshness before reporting recurrence as verified. This template schedules nothing."]}

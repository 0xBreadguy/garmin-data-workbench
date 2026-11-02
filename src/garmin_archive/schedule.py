"""Opt-in per-user macOS scheduling, shared by CLI and MCP setup."""
from __future__ import annotations

import os
import plistlib
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable
from xml.parsers.expat import ExpatError

from filelock import FileLock, Timeout

LABEL = "org.garmin-data-workbench.sync"
MARKER = "GARMIN_WORKBENCH_MANAGED"


def _locations(home: Path) -> Path:
    return home / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def _run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False, timeout=10)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError("launchctl timed out; check the existing schedule before retrying") from error
    if check and result.returncode:
        raise RuntimeError(f"{command[1]} failed (exit {result.returncode}); check launchctl and try again")
    return result


def schedule_status(*, data_dir: Path | None = None, home: Path | None = None, platform: str | None = None,
                    run: Callable = _run) -> dict:
    home = home or Path.home()
    platform = platform or sys.platform
    if platform != "darwin":
        return {"status": "unsupported", "message": "Automatic setup is available on macOS; use your OS scheduler elsewhere."}
    path = _locations(home)
    if not path.exists():
        return {"status": "not_configured", "recommended_hours": 6, "recommended_lookback_days": 2,
                "message": "Ask how often the user wants updates before configuring the local schedule."}
    try:
        data = plistlib.loads(path.read_bytes())
        env = data.get("EnvironmentVariables", {})
        if data.get("Label") != LABEL or env.get(MARKER) != "1":
            return {"status": "unmanaged", "message": "A schedule with this name exists but was not created by this setup."}
        interval = data.get("StartInterval")
        hours = int(env["GARMIN_WORKBENCH_INTERVAL_HOURS"])
        lookback = int(env["GARMIN_WORKBENCH_LOOKBACK_DAYS"])
        if not 1 <= hours <= 168 or not 1 <= lookback <= 31 or interval != hours * 3600:
            raise ValueError("invalid schedule")
    except (OSError, ValueError, KeyError, TypeError, AttributeError, ExpatError):
        return {"status": "invalid", "message": "The schedule file could not be read safely."}
    loaded = run(["launchctl", "print", f"gui/{os.getuid()}/{LABEL}"], check=False).returncode == 0
    if data_dir is not None and env.get("GARMIN_WORKBENCH_DATA_DIR") != str(data_dir.expanduser().resolve()):
        return {"status": "different_archive", "message": "The managed schedule belongs to a different archive."}
    return {"status": "scheduled" if loaded else "installed_not_loaded", "every_hours": hours,
            "lookback_days": lookback, "archive": env.get("GARMIN_WORKBENCH_DATA_DIR"),
            "message": "A Mac that is off or asleep may run later; catch-up resumes missed days."}


def _atomic_write(path: Path, content: bytes) -> None:
    fd, name = tempfile.mkstemp(prefix=".garmin-schedule-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def configure_schedule(data_dir: Path, hours: int, lookback_days: int = 2, *,
                       home: Path | None = None, platform: str | None = None,
                       executable: Path | None = None, run: Callable = _run) -> dict:
    """Set a local LaunchAgent only after a user explicitly chooses an interval."""
    if (platform or sys.platform) != "darwin":
        raise RuntimeError("automatic scheduling currently supports macOS only")
    if isinstance(hours, bool) or not isinstance(hours, int) or not 1 <= hours <= 168:
        raise ValueError("update frequency must be 1–168 hours")
    if isinstance(lookback_days, bool) or not isinstance(lookback_days, int) or not 1 <= lookback_days <= 31:
        raise ValueError("lookback must be 1–31 days")
    home = home or Path.home()
    data_dir = data_dir.expanduser().resolve()
    executable = executable or Path(sys.executable).parent / "garmin-archive"
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise RuntimeError("the installed garmin-archive executable could not be found")
    path = _locations(home)
    domain = f"gui/{os.getuid()}"
    path.parent.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        with FileLock(str(data_dir / "sync.lock"), timeout=0, mode=0o600):
            old_bytes = path.read_bytes() if path.exists() else None
            if old_bytes is not None:
                try:
                    previous = plistlib.loads(old_bytes)
                    previous_env = previous.get("EnvironmentVariables", {})
                    if (previous.get("Label") != LABEL or previous_env.get(MARKER) != "1"
                            or previous_env.get("GARMIN_WORKBENCH_DATA_DIR") != str(data_dir)):
                        raise ValueError
                except (ValueError, TypeError, AttributeError, ExpatError):
                    raise RuntimeError("an unmanaged or different-archive schedule already exists; it was not changed") from None
            logs = data_dir / "logs"
            logs.mkdir(mode=0o700, parents=True, exist_ok=True)
            for name in ("workbench-scheduled.out", "workbench-scheduled.err"):
                fd = os.open(logs / name, os.O_CREAT | os.O_WRONLY | os.O_APPEND, 0o600)
                os.close(fd)
            env = {"HOME": str(home), MARKER: "1", "GARMIN_WORKBENCH_INTERVAL_HOURS": str(hours),
                   "GARMIN_WORKBENCH_LOOKBACK_DAYS": str(lookback_days), "GARMIN_WORKBENCH_DATA_DIR": str(data_dir)}
            plist = {"Label": LABEL, "ProgramArguments": [str(executable), "--data-dir", str(data_dir),
                     "sync", "--catch-up", "--lookback-days", str(lookback_days)],
                     "StartInterval": hours * 3600, "WorkingDirectory": str(home), "EnvironmentVariables": env,
                     "StandardOutPath": str(logs / "workbench-scheduled.out"),
                     "StandardErrorPath": str(logs / "workbench-scheduled.err")}
            loaded = run(["launchctl", "print", f"{domain}/{LABEL}"], check=False).returncode == 0
            if loaded and old_bytes is None:
                raise RuntimeError("a service with this name is already running; it was not changed")
            if loaded:
                run(["launchctl", "bootout", domain, str(path)])
            try:
                _atomic_write(path, plistlib.dumps(plist))
                run(["launchctl", "bootstrap", domain, str(path)])
            except (OSError, RuntimeError):
                # Restore the previous configuration if activating the replacement fails.
                if old_bytes is None:
                    path.unlink(missing_ok=True)
                else:
                    _atomic_write(path, old_bytes)
                if loaded and old_bytes is not None:
                    try:
                        run(["launchctl", "bootstrap", domain, str(path)])
                    except RuntimeError:
                        raise RuntimeError("new schedule failed and the previous schedule could not be reloaded") from None
                raise
    except Timeout as error:
        raise RuntimeError("a sync is running; retry setup when it finishes") from error
    return {"status": "scheduled", "every_hours": hours, "lookback_days": lookback_days,
            "archive": str(data_dir), "message": "Schedule installed. No sync was started by setup."}

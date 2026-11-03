"""Small OS boundaries for installed commands and copyable shell examples."""
from __future__ import annotations

import shlex
import sys
from pathlib import Path
from typing import Sequence


def installed_executable(name: str, *, platform: str | None = None) -> Path:
    """Find a sibling entry point in the current Python installation."""
    suffix = ".exe" if (platform or sys.platform) == "win32" else ""
    return Path(sys.executable).parent / f"{name}{suffix}"


def shell_command(arguments: Sequence[str], *, platform: str | None = None) -> str:
    """Render for PowerShell on Windows, or a POSIX shell elsewhere.

    This is display-only. Launch subprocesses with argument lists instead.
    """
    if (platform or sys.platform) == "win32":
        return "& " + " ".join("'" + arg.replace("'", "''") + "'" for arg in arguments)
    return shlex.join(arguments)

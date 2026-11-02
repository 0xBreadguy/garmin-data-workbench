"""Helpers for installing and checking an agent connection."""
from __future__ import annotations

import asyncio
import getpass
import json
import logging
import os
import queue
import shlex
import shutil
import socket
import stat
import subprocess
import sys
import threading
import time
import warnings
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from garmin_personal_api import (
    DEFAULT_API_KEY_FILE, GarminPersonalApiClient, PersonalApiAuthenticator, resolve_api_key,
)
from garmin_personal_api.errors import GarminPersonalApiError

SERVER_NAME = "garmin-workbench"
REQUIRED_TOOLS = {"archive_status", "get_day", "get_trend", "setup_status", "configure_sync"}


def ensure_key() -> str:
    """Use an existing key or privately prompt for and validate a new one."""
    try:
        resolve_api_key()
        return "existing"
    except (OSError, GarminPersonalApiError, ValueError):
        pass
    if "GARMIN_PERSONAL_API_KEY" in os.environ:
        raise RuntimeError("GARMIN_PERSONAL_API_KEY is empty or unusable; fix or unset it and retry.")
    if not sys.stdin.isatty():
        raise RuntimeError("No Garmin key found. Use a supported private secret facility, then run "
                           "`garmin-archive save-key --from-file /private/secret-file`, or provide "
                           "GARMIN_PERSONAL_API_KEY through that facility. Never put the key in chat or a command.")
    path = Path(DEFAULT_API_KEY_FILE).expanduser()
    if os.path.lexists(path):
        raise RuntimeError("The Garmin key file exists but is not usable; it was not overwritten.")
    print("Create a Personal API key at https://connect.garmin.com/app/settings/personalApiToken")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            key = getpass.getpass("Paste your Garmin Personal API key (hidden): ").strip()
    except (EOFError, getpass.GetPassWarning) as error:
        raise RuntimeError("Hidden key entry is unavailable; use a supported private secret facility.") from error
    _validate_and_save_key(key)
    return "created"


def save_key_from_file(source: Path) -> None:
    """Import a host-provided secret file without a TTY, sync or client changes."""
    # Open without following a final symlink or blocking on a FIFO. Check the
    # opened descriptor rather than a path which could change between checks.
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(source.expanduser(), flags)
    with os.fdopen(fd, "rb") as input_file:
        info = os.fstat(input_file.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise RuntimeError("The secret source must be a regular private file.")
        if os.name == "posix" and (info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077):
            raise RuntimeError("The secret file must be owned by the current user with no group or other permissions.")
        raw = input_file.read(16_385)
    if len(raw) > 16_384:
        raise RuntimeError("The secret file is too large; expected a single API key.")
    try:
        key = raw.decode("utf-8").strip()
    except UnicodeError as error:
        raise RuntimeError("The secret file must contain a UTF-8 API key.") from error
    if "\n" in key or "\r" in key or "\x00" in key:
        raise RuntimeError("The secret file must contain a single API key.")
    _validate_and_save_key(key)


def _validate_and_save_key(key: str) -> None:
    path = Path(DEFAULT_API_KEY_FILE).expanduser()
    if os.path.lexists(path):
        raise RuntimeError("The Garmin key file already exists; it was not overwritten.")
    if not key:
        raise RuntimeError("No key supplied; setup stopped.")
    previous_log_level = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        with PersonalApiAuthenticator() as auth:
            token = auth.obtain_token(key)
        with GarminPersonalApiClient(token.access_token) as client:
            client.get_user_profile_settings()
    except Exception as error:  # response details can contain sensitive data
        raise RuntimeError(f"Garmin could not validate the key ({type(error).__name__}); it was not saved.") from error
    finally:
        logging.disable(previous_log_level)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w") as output:
        output.write(key + "\n")


def scheduled_key_available() -> bool:
    """launchd does not inherit the shell key; check the file matches this run."""
    try:
        current = resolve_api_key()
        scheduled = resolve_api_key(key_file=DEFAULT_API_KEY_FILE)
        return current == scheduled
    except (OSError, GarminPersonalApiError, ValueError):
        return False


def executable_path() -> Path:
    suffix = ".exe" if os.name == "nt" else ""
    return Path(sys.executable).parent / f"garmin-archive-mcp{suffix}"


def register_codex(data_dir: Path, *, executable: Path | None = None) -> str:
    """Register only when absent. Never overwrite an existing server configuration."""
    codex = shutil.which("codex")
    executable = executable or executable_path()
    if not codex:
        raise RuntimeError("Codex CLI was not found. Install it, then run install again.")
    if not executable.is_file():
        raise RuntimeError("The installed MCP executable was not found. Reinstall garmin-data-workbench.")
    existing = subprocess.run([codex, "mcp", "get", SERVER_NAME], stdout=subprocess.DEVNULL,
                              stderr=subprocess.PIPE, text=True, timeout=15, check=False)
    if existing.returncode == 0:
        return "existing"
    if "No MCP server named" not in existing.stderr:
        raise RuntimeError("Could not check Codex MCP configuration; no configuration was changed.")
    result = subprocess.run([codex, "mcp", "add", SERVER_NAME, "--", str(executable),
                             "--data-dir", str(data_dir.expanduser().resolve())],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=False)
    if result.returncode:
        raise RuntimeError("Codex could not register the MCP server. Run `codex mcp list` to inspect its configuration.")
    return "added"


def register_claude(data_dir: Path, *, executable: Path | None = None) -> str:
    """Register a per-user Claude Code server only when the name is unused."""
    claude = shutil.which("claude")
    executable = executable or executable_path()
    if not claude:
        raise RuntimeError("Claude Code CLI was not found. Install it, then run install again.")
    if not executable.is_file():
        raise RuntimeError("The installed MCP executable was not found. Reinstall garmin-data-workbench.")
    existing = subprocess.run([claude, "mcp", "get", SERVER_NAME], stdout=subprocess.DEVNULL,
                              stderr=subprocess.PIPE, text=True, timeout=15, check=False)
    if existing.returncode == 0:
        return "existing"
    if "No MCP server named" not in existing.stderr:
        raise RuntimeError("Could not check Claude Code MCP configuration; no configuration was changed.")
    result = subprocess.run([claude, "mcp", "add", "--scope", "user", "--transport", "stdio", SERVER_NAME,
                             "--", str(executable), "--data-dir", str(data_dir.expanduser().resolve())],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, check=False)
    if result.returncode:
        raise RuntimeError("Claude Code could not register the MCP server. Run `claude mcp list` to inspect its configuration.")
    return "added"


def assistant_guide(client: str, *, data_dir: Path | None = None) -> str:
    """Build a copyable handoff; it contains no health data or credentials."""
    computer = socket.gethostname()
    common = ("Use the archive's status and freshness when answering, include missing-data caveats, "
              "and never ask me for my Garmin key. If access fails, tell me which connection or computer is unavailable.")
    if client == "dot":
        return (f"Please remember: my Garmin Data Workbench is on my connected computer {computer}. "
                "When I ask about my Garmin health or activity data, use a local Codex task on that computer "
                "and its garmin-workbench MCP tools to answer. " + common)
    if client in {"codex", "claude"}:
        return ("My Garmin data is in the local Garmin Data Workbench. Use its garmin-workbench MCP tools "
                "for questions about my health and activities. " + common)
    if client == "muse":
        from .archive import default_data_dir
        suffix = ".exe" if os.name == "nt" else ""
        executable = Path(sys.executable).parent / f"garmin-archive{suffix}"
        command = shlex.join([str(executable), "--data-dir", str((data_dir or default_data_dir()).expanduser().resolve())])
        return (f"My Garmin Data Workbench is on {computer}. If you can run commands on that same host, "
                f"use its local CLI: `{command} day YYYY-MM-DD` for an overview, or "
                f"`{command} trend sleep_duration --from YYYY-MM-DD --to YYYY-MM-DD` for up to 90 days. "
                "Replace the dates with the requested range; omitting them uses Garmin profile dates "
                "(host date as fallback) and a seven-day trend. Commands return JSON with source units, "
                "preferences, freshness and coverage. Queries need an existing synced archive but no key or MCP client. "
                "Use `status` to inspect sync errors. Do not sync, register another client or create a routine "
                "unless I ask. This handoff does not establish a connection to another host. " + common)
    return (f"My Garmin Data Workbench is on {computer}. To answer Garmin questions, use its "
            "garmin-workbench MCP server through a supported connection to that computer. " + common)


async def _probe_server(executable: Path, data_dir: Path) -> None:
    params = StdioServerParameters(command=str(executable), args=["--data-dir", str(data_dir.expanduser().resolve())])
    with open(os.devnull, "w") as errors:
        async with stdio_client(params, errlog=errors) as (read, write):
            async with ClientSession(read, write) as client:
                await client.initialize()
                tools = await client.list_tools()
                names = {tool.name for tool in tools.tools}
                if not REQUIRED_TOOLS.issubset(names):
                    raise RuntimeError("The MCP server is missing expected tools.")
                status = await client.call_tool("archive_status", {})
                if status.isError:
                    raise RuntimeError("The MCP server could not read the local archive.")


def probe_server(data_dir: Path, *, executable: Path | None = None) -> None:
    executable = executable or executable_path()
    if not executable.is_file():
        raise RuntimeError("The installed MCP executable was not found.")
    try:
        asyncio.run(asyncio.wait_for(_probe_server(executable, data_dir), timeout=20))
    except TimeoutError as error:
        raise RuntimeError("The local MCP server did not respond within 20 seconds.") from error
    except Exception as error:
        raise RuntimeError(f"The local MCP server could not be verified ({type(error).__name__}).") from error


def verify_codex_discovery() -> list[str]:
    """Check discovery via a fresh Codex app-server, without starting a model turn."""
    codex = shutil.which("codex")
    if not codex:
        raise RuntimeError("Codex CLI was not found.")
    try:
        process = subprocess.Popen([codex, "app-server"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, text=True, bufsize=1)
    except OSError as error:
        raise RuntimeError("Could not start the Codex app-server for discovery.") from error
    messages: queue.Queue[dict[str, Any]] = queue.Queue()

    def read() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            try:
                value = json.loads(line)
                if isinstance(value, dict):
                    messages.put(value)
            except json.JSONDecodeError:
                continue

    thread = threading.Thread(target=read, daemon=True)
    thread.start()
    deadline = time.monotonic() + 25

    def send(value: dict) -> None:
        assert process.stdin is not None
        process.stdin.write(json.dumps(value) + "\n")
        process.stdin.flush()

    def response(request_id: int) -> dict:
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RuntimeError("Codex did not report MCP status within 25 seconds.")
            try:
                message = messages.get(timeout=remaining)
            except queue.Empty as error:
                raise RuntimeError("Codex did not report MCP status within 25 seconds.") from error
            if message.get("id") == request_id:
                if "error" in message:
                    raise RuntimeError("Codex could not report MCP status. Check your Codex version and settings.")
                return message.get("result", {})

    try:
        send({"id": 1, "method": "initialize", "params": {
            "clientInfo": {"name": "garmin-workbench-install", "version": "1"}}})
        response(1)
        send({"method": "initialized", "params": {}})
        send({"id": 2, "method": "mcpServerStatus/list", "params": {
            "serverName": SERVER_NAME, "detail": "toolsAndAuthOnly"}})
        entries = response(2).get("data", [])
        server = next((x for x in entries if x.get("name") == SERVER_NAME), None)
        if not server:
            raise RuntimeError("A fresh Codex runtime did not discover garmin-workbench.")
        tools = server.get("tools") or {}
        names = set(tools) if isinstance(tools, dict) else set()
        if not REQUIRED_TOOLS.issubset(names):
            raise RuntimeError("Codex discovered the server but not its expected tools.")
        return sorted(names)
    except (BrokenPipeError, OSError) as error:
        raise RuntimeError("Could not start the Codex app-server for discovery.") from error
    finally:
        if process.stdin:
            process.stdin.close()
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        if process.stdout:
            process.stdout.close()

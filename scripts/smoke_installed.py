"""Check a built wheel in a disposable environment using synthetic data only.

Run after `uv build`: uv run --locked python scripts/smoke_installed.py
Dependency installation may use the network; no Garmin account is used.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def check_mcp(executable: Path, archive: Path, workdir: Path, env: dict[str, str]) -> None:
    params = StdioServerParameters(command=str(executable), args=["--data-dir", str(archive)],
                                  cwd=str(workdir), env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            tools = await client.list_tools()
            assert {"archive_status", "get_day"}.issubset({tool.name for tool in tools.tools})
            result = await client.call_tool("get_day", {"day": "2026-01-01"})
            assert not result.isError, result.content
            data = result.structuredContent or json.loads(result.content[0].text)
            assert data["metrics"]["steps"]["value"] == 1234, data


def main() -> None:
    project = Path(__file__).resolve().parents[1]
    wheels = list((project / "dist").glob("*.whl"))
    if len(wheels) != 1:
        raise SystemExit("Expected one wheel in dist/. Build into a clean output directory first.")
    env = dict(os.environ)
    for name in ("PYTHONPATH", "PYTHONHOME", "GARMIN_PERSONAL_API_KEY"):
        env.pop(name, None)
    env["PYTHONUTF8"] = "1"

    # Exercise spaces, non-ASCII characters and apostrophes in real file paths.
    with tempfile.TemporaryDirectory(prefix="garmin smoke Zoë's ") as temp:
        workdir = Path(temp).resolve()

        def run(arguments: list[str], *, cwd: Path = workdir) -> str:
            result = subprocess.run(arguments, cwd=cwd, env=env, capture_output=True,
                                    text=True, encoding="utf-8", timeout=180)
            if result.returncode:
                raise RuntimeError(f"Smoke command failed: {arguments[0]}\n{result.stdout}\n{result.stderr}")
            return result.stdout

        requirements = workdir / "requirements.txt"
        run(["uv", "export", "--locked", "--no-dev", "--no-emit-project", "--no-hashes",
             "--output-file", str(requirements)], cwd=project)
        environment = workdir / "environment"
        run(["uv", "venv", "--python", sys.executable, str(environment)])
        binary_dir = environment / ("Scripts" if sys.platform == "win32" else "bin")
        suffix = ".exe" if sys.platform == "win32" else ""
        python = binary_dir / f"python{suffix}"
        run(["uv", "pip", "install", "--python", str(python), "--no-deps",
             "--requirement", str(requirements), str(wheels[0])])

        cli = binary_dir / f"garmin-archive{suffix}"
        mcp = binary_dir / f"garmin-archive-mcp{suffix}"
        assert "usage:" in run([str(cli), "--help"])
        assert "usage:" in run([str(mcp), "--help"])
        archive = workdir / "archive #1"
        run([str(python), "-c", """
import sys
from pathlib import Path
import garmin_archive
from garmin_archive.archive import Archive
assert Path(garmin_archive.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
archive = Archive(Path(sys.argv[1]))
try:
    archive.save_daily('daily_summary', '2026-01-01', {'data': [
        {'calendarDate': '2026-01-01', 'movement': {'steps': {'value': 1234}}}
    ]})
finally:
    archive.close()
""", str(archive)])
        database = archive / "archive.sqlite3"
        original = database.read_bytes()
        day = json.loads(run([str(cli), "--data-dir", str(archive), "day", "2026-01-01"]))
        assert day["metrics"]["steps"]["value"] == 1234, day
        asyncio.run(asyncio.wait_for(check_mcp(mcp, archive, workdir, env), timeout=30))
        assert database.read_bytes() == original, "Queries changed the archive"
    print("Installed wheel: CLI help, synthetic CLI/MCP queries and read-only archive checks passed.")


if __name__ == "__main__":
    main()

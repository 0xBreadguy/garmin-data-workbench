"""Check a built wheel in a disposable environment using synthetic data only.

Run after `uv build`: uv run --locked python scripts/smoke_installed.py
Dependency installation may use the network; no Garmin account is used.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from garmin_archive.onboarding import installation_info


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
            sleep = await client.call_tool("get_sleep", {"start": "2026-01-01", "end": "2026-01-01"})
            assert not sleep.isError, sleep.content
            data = sleep.structuredContent or json.loads(sleep.content[0].text)
            assert data["nights"][0]["values"]["sleep_score"] == 80, data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--charts", action="store_true", help="Also install and verify the optional chart extra")
    args = parser.parse_args()
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
             *(["--extra", "charts"] if args.charts else []),
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
        assert "chart sleep" in run([str(cli), "agent-guide"])
        assert "same host" in run([str(cli), "assistant-guide", "--client", "other"])
        receipt = json.loads(run([str(cli), "--data-dir", str(workdir / "missing"), "setup-receipt"]))
        assert receipt["archive"]["status"] == "unavailable", receipt
        assert receipt["verification"]["recurring_execution"] == "not_verified", receipt
        assert receipt["installation"]["source"] == installation_info()["source"], "Wheel provenance differs from checkout; rebuild it"
        assert receipt["installation"]["charts_available"] == args.charts, receipt
        assert not (workdir / "missing").exists()
        run([str(python), "-c", "from pathlib import Path; import garmin_archive; assert Path(garmin_archive.__file__).with_name('build_info.json').is_file()"])
        brand = json.loads(run([str(cli), "brand"]))
        assert brand["colors"]["primary"] == "#0863E8", brand
        for asset in brand["assets"].values():
            path = Path(asset)
            assert path.is_file() and path.is_relative_to(environment), asset
        run([str(python), "-c", "import sys; from garmin_archive.brand import get_brand; get_brand(); assert 'matplotlib' not in sys.modules"])
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
    archive.save_daily('sleep', '2026-01-01', {'sleepTimeSeconds': 27000,
        'deepSleepSeconds': 5000, 'remSleepSeconds': 6000, 'lightSleepSeconds': 16000,
        'unmeasurableSleepSeconds': 0, 'sleepScores': {'overall': {'value': 80}}})
finally:
    archive.close()
""", str(archive)])
        database = archive / "archive.sqlite3"
        original = database.read_bytes()
        day = json.loads(run([str(cli), "--data-dir", str(archive), "day", "2026-01-01"]))
        assert day["metrics"]["steps"]["value"] == 1234, day
        sleep = json.loads(run([str(cli), "--data-dir", str(archive), "sleep", "--from", "2026-01-01", "--to", "2026-01-01"]))
        assert sleep["nights"][0]["stages_complete"], sleep
        asyncio.run(asyncio.wait_for(check_mcp(mcp, archive, workdir, env), timeout=30))
        if args.charts:
            chart = workdir / "steps.png"
            run([str(cli), "--data-dir", str(archive), "chart", "steps", "--from", "2026-01-01",
                 "--to", "2026-01-03", "--synthetic", "--layout", "wide", "--output", str(chart)])
            assert chart.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), "Installed chart command did not write a PNG"
            run([str(python), "-c", "from PIL import Image; import sys; image=Image.open(sys.argv[1]); assert 'Synthetic data' in image.info['Description']; image.verify()", str(chart)])
            report = workdir / "sleep.png"
            run([str(cli), "--data-dir", str(archive), "chart", "sleep", "--from", "2026-01-01", "--to", "2026-01-03",
                 "--synthetic", "--output", str(report)])
            assert report.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), "Sleep report missing"
        assert database.read_bytes() == original, "Queries changed the archive"
    print("Installed wheel: CLI help, synthetic CLI/MCP queries and read-only archive checks passed.")


if __name__ == "__main__":
    main()

"""Check a built wheel in a disposable environment using synthetic data only.

Run after `uv build`: uv run --locked python scripts/smoke_installed.py
Dependency installation may use the network; no Garmin account is used.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import subprocess
import sys
import tempfile
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from garmin_archive.onboarding import installation_info


async def check_mcp(executable: Path, archive: Path, workdir: Path, env: dict[str, str], charts: bool) -> dict:
    params = StdioServerParameters(command=str(executable), args=["--data-dir", str(archive)],
                                  cwd=str(workdir), env=env)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write, read_timeout_seconds=timedelta(seconds=30)) as client:
            await client.initialize()
            tools = await client.list_tools()
            assert {"archive_status", "get_day", "chart", "brand", "explore_sleep_recovery"}.issubset({tool.name for tool in tools.tools})
            recovery_ui = await client.read_resource('ui://garmin-workbench/sleep-recovery-v1.html')
            assert recovery_ui.contents[0].mimeType == 'text/html;profile=mcp-app'
            assert 'ui/initialize' in recovery_ui.contents[0].text
            assert '/*__' not in recovery_ui.contents[0].text
            recovery = await client.call_tool('explore_sleep_recovery', {'start': '2026-01-01', 'end': '2026-01-03'})
            assert not recovery.isError
            assert recovery.structuredContent['archive_provenance']['synthetic'] is True
            assert recovery.structuredContent['sleep']['nights'][0]['values']['sleep_need'] == 500
            branding = await client.call_tool('brand', {})
            assert not branding.isError
            resource = await client.read_resource('garmin-brand://assets/icon_png')
            assert resource.contents[0].mimeType == 'image/png'
            image = await client.call_tool('chart', {'metric': 'sleep', 'start': '2026-01-01', 'end': '2026-01-03'})
            if charts:
                assert not image.isError
                assert image.structuredContent['synthetic'] is True
                assert image.structuredContent['units']['sleep_duration'] == 'hours'
                png = next(c for c in image.content if c.type == 'image')
                assert base64.b64decode(png.data).startswith(b'\x89PNG\r\n\x1a\n')
            else:
                assert image.isError
                assert image.structuredContent['error']['code'] == 'dependency_unavailable'
                assert not any(c.type == 'image' for c in image.content)
            result = await client.call_tool("get_day", {"day": "2026-01-01"})
            assert not result.isError, result.content
            data = result.structuredContent or json.loads(result.content[0].text)
            assert data["metrics"]["steps"]["value"] == 1234, data
            sleep = await client.call_tool("get_sleep", {"start": "2026-01-01", "end": "2026-01-01"})
            assert not sleep.isError, sleep.content
            data = sleep.structuredContent or json.loads(sleep.content[0].text)
            assert data["nights"][0]["values"]["sleep_score"] == 80, data
            assert data["nights"][0]["values"]["sleep_need"] == 500, data
            battery = await client.call_tool("get_body_battery", {"start": "2026-01-01", "end": "2026-01-01"})
            assert not battery.isError, battery.content
            data = battery.structuredContent or json.loads(battery.content[0].text)
            assert data["days"][0]["values"]["body_battery_last"] == 20, data
            catalog = await client.call_tool("api_catalog", {"dataset": "sleep", "pointer": "/dailyNapDTOS/*"})
            assert not catalog.isError, catalog.content
            data = catalog.structuredContent or json.loads(catalog.content[0].text)
            assert any(field["pointer"].endswith("/napTimeSec") for field in data["fields"]), data
            native = await client.call_tool("source_data", {"dataset": "hydration", "day": "2026-01-01", "pointer": "/0/valueInML"})
            assert not native.isError, native.content
            data = native.structuredContent or json.loads(native.content[0].text)
            assert data["value"] == 0, data
            comparison = await client.call_tool("compare_periods", {"metric": "steps", "start": "2026-01-02", "end": "2026-01-02",
                "baseline_start": "2026-01-01", "baseline_end": "2026-01-01"})
            assert not comparison.isError, comparison.content
            workouts = await client.call_tool("get_workout_summary", {"start": "2026-01-01", "end": "2026-01-02", "activity_type": "running"})
            assert not workouts.isError, workouts.content
            activities = await client.call_tool("list_activities", {"start": "2026-01-01", "end": "2026-01-02", "activity_type": "running", "limit": 1})
            assert not activities.isError, activities.content
            data = activities.structuredContent or json.loads(activities.content[0].text)
            assert data["activities"][0]["activity_id"] == 42
            return {"comparison": comparison.structuredContent or json.loads(comparison.content[0].text),
                    "workouts": workouts.structuredContent or json.loads(workouts.content[0].text)}


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
        assert len(json.loads(run([str(cli), "api-catalog"]))["sources"]) == 26
        metrics = json.loads(run([str(cli), "--data-dir", str(workdir / "missing"), "metrics"]))
        assert {"sleep_duration", "sleep_need", "body_battery_max"}.issubset({item["name"] for item in metrics["metrics"]})
        installed_version = json.loads(run([str(cli), "--data-dir", str(workdir / "missing"), "version"]))
        assert installed_version["source"] == installation_info()["source"], "Installed version command has stale provenance"
        assert "garmin-data-workbench" in run([str(cli), "--version"])
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
from datetime import UTC, datetime
from garmin_archive.archive import Archive
assert Path(garmin_archive.__file__).resolve().is_relative_to(Path(sys.prefix).resolve())
archive = Archive(Path(sys.argv[1]))
try:
    archive.mark_synthetic('wheel-smoke', 42, '2026-01-01T00:00:00Z')
    archive.save_daily('hydration', '2026-01-01', [{'calendarDate': '2026-01-01', 'valueInML': 0}])
    archive.save_daily('daily_summary', '2026-01-01', {'data': [
        {'calendarDate': '2026-01-01', 'movement': {'steps': {'value': 1234}}}
    ]})
    archive.save_daily('daily_summary', '2026-01-02', {'data': [
        {'calendarDate': '2026-01-02', 'movement': {'steps': {'value': 2468}}}]})
    archive.save_activities('2026-01-01', [{'activityId': 42, 'activityType': {'typeKey': 'running'},
        'distance': 5000, 'duration': 1800}])
    archive.save_activities('2026-01-02', [])
    archive.save_daily('sleep', '2026-01-01', {'sleepTimeSeconds': 27000,
        'deepSleepSeconds': 5000, 'remSleepSeconds': 6000, 'lightSleepSeconds': 16000,
        'unmeasurableSleepSeconds': 0, 'sleepScores': {'overall': {'value': 80}},
        'sleepNeed': {'calendarDate': '2026-01-01', 'actual': 500, 'baseline': 470},
        'nextSleepNeed': {'calendarDate': '2026-01-02', 'actual': 480, 'baseline': 470}})
    archive.save_daily('body_battery', '2026-01-01', [{'date': '2026-01-01', 'charged': 60, 'drained': 50,
        'bodyBatteryValueDescriptorDTOList': [
            {'bodyBatteryValueDescriptorKey': 'bodyBatteryLevel', 'bodyBatteryValueDescriptorIndex': 0},
            {'bodyBatteryValueDescriptorKey': 'timestamp', 'bodyBatteryValueDescriptorIndex': 1}],
        'bodyBatteryValuesArray': [[v, int(datetime(2026,1,1,h,tzinfo=UTC).timestamp()*1000)]
                                  for h,v in ((0,10),(7,80),(23,20))]}])
finally:
    archive.close()
""", str(archive)])
        database = archive / "archive.sqlite3"
        original = database.read_bytes()
        day = json.loads(run([str(cli), "--data-dir", str(archive), "day", "2026-01-01"]))
        assert day["metrics"]["steps"]["value"] == 1234, day
        native = json.loads(run([str(cli), "--data-dir", str(archive), "source-data", "hydration", "--day", "2026-01-01", "--pointer", "/0/valueInML"]))
        assert native["value"] == 0, native
        native = json.loads(run([str(cli), "--data-dir", str(archive), "source-series", "hydration", "/0/valueInML", "--from", "2026-01-01", "--to", "2026-01-01"]))
        assert native["points"][0]["value"] == 0, native
        sleep = json.loads(run([str(cli), "--data-dir", str(archive), "sleep", "--from", "2026-01-01", "--to", "2026-01-01"]))
        assert sleep["nights"][0]["stages_complete"], sleep
        assert sleep["nights"][0]["next_sleep_need"]["day"] == "2026-01-02", sleep
        battery = json.loads(run([str(cli), "--data-dir", str(archive), "body-battery", "--from", "2026-01-01", "--to", "2026-01-01"]))
        assert battery["days"][0]["values"]["body_battery_last"] == 20, battery
        comparison = json.loads(run([str(cli), "--data-dir", str(archive), "compare", "steps", "--from", "2026-01-02", "--to", "2026-01-02",
                                     "--baseline-from", "2026-01-01", "--baseline-to", "2026-01-01"]))
        assert comparison["change"]["mean_difference"] == 1234 and comparison["change"]["mean_percent_change"] == 100, comparison
        workouts = json.loads(run([str(cli), "--data-dir", str(archive), "workout-summary", "--from", "2026-01-01", "--to", "2026-01-02", "--type", "running"]))
        assert workouts["totals"]["distance_m"] == 5000 and workouts["totals"]["duration_s"] == 1800, workouts
        activities = json.loads(run([str(cli), "--data-dir", str(archive), "activities", "--from", "2026-01-01", "--to", "2026-01-02", "--type", "running"]))
        assert [row["activity_id"] for row in activities] == [42], activities
        mcp_results = asyncio.run(asyncio.wait_for(check_mcp(mcp, archive, workdir, env, args.charts), timeout=30))
        widget = workdir / "recovery.html"
        widget_info = json.loads(run([str(cli), "--data-dir", str(archive), "widget", "sleep-recovery",
            "--from", "2026-01-01", "--to", "2026-01-03", "--output", str(widget)]))
        assert widget_info["output_path"] == str(widget) and widget_info["archive_provenance"]["synthetic"]
        fragment = widget.read_text(encoding="utf-8")
        assert 'id="recovery-snapshot"' in fragment and 'window.hatchWidget' in fragment
        assert '<form' not in fragment and '/*__' not in fragment
        assert widget.stat().st_size < 1_000_000
        canvas = workdir / "recovery.canvas.tsx"
        canvas_info = json.loads(run([str(cli), "--data-dir", str(archive), "widget", "sleep-recovery",
            "--host", "grok", "--from", "2026-01-01", "--to", "2026-01-03", "--output", str(canvas),
            "--handoff-dir", str(workdir / "grok-handoff")]))
        assert canvas_info["output_path"] == str(canvas) and canvas_info["archive_provenance"]["synthetic"]
        source = canvas.read_text(encoding="utf-8")
        assert 'grok/canvas' in source and '/*__RECOVERY_SNAPSHOT__*/' not in source and '/*__BRAND_TOKENS__*/' not in source
        assert '\\"codec_version\\":1' in source and '\\"schema_version\\":1' in source
        assert 'const transportPart0 = ' in source and 'decodeTransport(JSON.parse([' in source
        assert 'WriteCanvas' in canvas_info["delivery"] and 'private Page' in canvas_info["delivery"]
        assert canvas_info["bytes"] == canvas.stat().st_size <= 1_048_576
        handoff = canvas_info["handoff"]
        assert Path(handoff["source_path"]).read_bytes() == canvas.read_bytes()
        plan = json.loads(Path(handoff["plan_path"]).read_text(encoding="utf-8"))
        assert len(plan["steps"]) > 2 and len(plan["verification_steps"]) > 2
        assert all(step["reserved_arguments_json_bytes"] <= 12000
                   for step in [*plan["steps"], *plan["verification_steps"]])
        assert mcp_results == {"comparison": comparison, "workouts": workouts}, "Installed CLI and MCP disagree"
        if args.charts:
            chart = workdir / "steps.png"
            metadata = json.loads(run([str(cli), "--data-dir", str(archive), "chart", "steps", "--from", "2026-01-01",
                 "--to", "2026-01-03", "--synthetic", "--layout", "wide", "--output", str(chart), "--json"]))
            assert metadata["output_path"] == str(chart) and metadata["synthetic"], metadata
            assert metadata["delivery"] == "PNG file saved; host attachment and display must be verified separately."
            assert chart.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), "Installed chart command did not write a PNG"
            run([str(python), "-c", "from PIL import Image; import sys; image=Image.open(sys.argv[1]); assert 'Synthetic data' in image.info['Description']; image.verify()", str(chart)])
            report = workdir / "sleep.png"
            run([str(cli), "--data-dir", str(archive), "chart", "sleep", "--from", "2026-01-01", "--to", "2026-01-03",
                 "--synthetic", "--output", str(report)])
            assert report.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), "Sleep report missing"
            for metric in ("sleep_need", "body_battery_last"):
                run([str(cli), "--data-dir", str(archive), "chart", metric, "--from", "2026-01-01", "--to", "2026-01-03",
                     "--synthetic", "--output", str(workdir / (metric + ".png"))])
        assert database.read_bytes() == original, "Queries changed the archive"
    print("Installed wheel: CLI help, synthetic CLI/MCP queries and read-only archive checks passed.")


if __name__ == "__main__":
    main()

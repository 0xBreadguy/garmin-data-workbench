"""Stamp build provenance without writing generated files into the checkout."""
import json
import subprocess
import tempfile
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        root = Path(self.root)
        info = {"revision": None, "dirty": None}
        if (root / ".git").exists():
            try:
                info = {"revision": subprocess.check_output(
                    ["git", "-C", str(root), "rev-parse", "HEAD"], text=True, timeout=5).strip(),
                    "dirty": bool(subprocess.check_output(
                        ["git", "-C", str(root), "status", "--porcelain", "--untracked-files=normal"],
                        text=True, timeout=5).strip())}
            except (OSError, subprocess.SubprocessError):
                pass
        else:
            stamp = root / "src" / "garmin_archive" / "build_info.json"
            if stamp.is_file():
                info = json.loads(stamp.read_text(encoding="utf-8"))
        self.temp = tempfile.TemporaryDirectory(prefix="garmin-build-")
        path = Path(self.temp.name) / "build_info.json"
        path.write_text(json.dumps(info), encoding="utf-8")
        prefix = "src/" if self.target_name == "sdist" else ""
        build_data.setdefault("force_include", {})[str(path)] = prefix + "garmin_archive/build_info.json"

    def finalize(self, version, build_data, artifact_path):
        self.temp.cleanup()

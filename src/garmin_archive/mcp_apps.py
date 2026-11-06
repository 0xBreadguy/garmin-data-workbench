"""Packaged, network-free MCP Apps resource; no health data in the template."""
from functools import lru_cache
from pathlib import Path

RECOVERY_URI = "ui://garmin-workbench/sleep-recovery-v1.html"
APP_MIME = "text/html;profile=mcp-app"
APP_META = {"ui": {"prefersBorder": False, "csp": {
    "connectDomains": [], "resourceDomains": [], "frameDomains": [], "baseUriDomains": []}}}


@lru_cache(maxsize=1)
def recovery_template() -> str:
    """Shared unbundled document; adapters may alter markup before inlining code."""
    return (Path(__file__).with_name("ui") / "recovery.html").read_text(encoding="utf-8")


def bundle_recovery(page: str) -> str:
    root = Path(__file__).with_name("ui")
    for name in ("recovery.css", "d3.min.js", "recovery.js"):
        page = page.replace("/*__" + name + "__*/", (root / name).read_text(encoding="utf-8"))
    return page


@lru_cache(maxsize=1)
def recovery_app_html() -> str:
    return bundle_recovery(recovery_template())

"""Native in-chat HTML snapshots using the same renderer and shared queries.

The export contains bounded health observations. It never syncs, hosts a server,
or publishes a page. The assistant must present it with its native widget tool.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .mcp_apps import bundle_recovery, recovery_template
from .recovery import _snapshot, compare_sleep_recovery, get_sleep_recovery

MAX_WIDGET_BYTES = 1_000_000


def recovery_widget_snapshot(db, start: str = "", end: str = "") -> dict:
    """One coherent 1–90 day snapshot, with a comparison of its two halves."""
    with _snapshot(db):
        report = get_sleep_recovery(db, start, end)
        nights = report["sleep"]["nights"]
        middle = len(nights) // 2
        comparison = (compare_sleep_recovery(db, nights[middle]["day"], report["to"],
                      report["from"], nights[middle - 1]["day"]) if middle else None)
        return {"schema_version": 1, "report": report, "comparison": comparison}


def recovery_widget_html(snapshot: dict) -> str:
    """Muse-compatible fragment: inline code, no forms or document wrappers."""
    template = recovery_template()
    # Transform only our fixed template, before inserting scripts or data.
    style = re.search(r"<style>.*?</style>", template, re.S).group()
    body = template.split("<body>", 1)[1].split("</body>", 1)[0]
    body = re.sub(r"<form\b.*?</form>", "", body, flags=re.S)
    body = body.replace("1–90 days per period. Earlier period must finish before the later period starts.",
                        "The loaded dates are split into earlier and later periods. Ask Muse for other dates.")
    body = body.replace("Reads your local archive; loading dates never starts a Garmin sync.",
                        "Saved archive snapshot. Ask Muse to load another date range; this widget never syncs.")
    body = re.sub(r'<button\b[^>]*\bid="ask-night".*?</button>', "", body, flags=re.S)
    payload = json.dumps(snapshot, ensure_ascii=True, separators=(",", ":"), allow_nan=False).replace("<", "\\u003c")
    bootstrap = '<script type="application/json" id="recovery-snapshot">' + payload + '</script>'
    theme = """<style>:root{--background:var(--hatch-widget-bg,var(--brand-background));
--foreground:var(--hatch-widget-text,var(--brand-ink));
--muted-foreground:var(--hatch-widget-muted,var(--brand-secondary));
--secondary:var(--hatch-widget-surface,var(--brand-tint));
--border:var(--hatch-widget-border,var(--brand-rule));
--ring:var(--hatch-widget-focus,#438dff)}
#demo{width:100%;max-width:880px;margin:auto;overflow-wrap:anywhere;padding:4px}
</style>"""
    html = bundle_recovery(style + theme + bootstrap + body)
    if len(html.encode("utf-8")) > MAX_WIDGET_BYTES:
        raise ValueError("Widget exceeds the 1 MB host limit; choose a shorter date range.")
    return html


def write_recovery_widget(db, output: Path, start: str = "", end: str = "") -> dict:
    snapshot = recovery_widget_snapshot(db, start, end)
    html = recovery_widget_html(snapshot)
    output = output.expanduser().absolute()
    if output.suffix.lower() != ".html":
        raise ValueError("Widget output must be a new .html file.")
    with open(output, "x", encoding="utf-8", opener=lambda path, flags: os.open(path, flags, 0o600)) as file:
        file.write(html)
    report = snapshot["report"]
    return {"output_path": str(output), "bytes": len(html.encode("utf-8")),
            "from": report["from"], "to": report["to"],
            "archive_provenance": report["archive_provenance"],
            "delivery": "Saved HTML fragment. Present unchanged using widget.create_html_file_widget; file creation does not prove display."}

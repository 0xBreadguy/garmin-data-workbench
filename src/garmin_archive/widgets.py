"""Native interactive snapshots using shared queries and packaged views.

The export contains bounded health observations. It never syncs, hosts a server,
or publishes a page. The assistant must present it with its native widget tool.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .grok_transport import pack_grok_snapshot
from .mcp_apps import bundle_recovery, recovery_template
from .recovery import _snapshot, compare_sleep_recovery, get_sleep_recovery

MAX_WIDGET_BYTES = 1_000_000
# Project guardrail for bounded exports, not a documented Grok host limit.
MAX_GROK_CANVAS_BYTES = 1_048_576
GROK_SNAPSHOT_MARKER = "/*__RECOVERY_SNAPSHOT__*/"
GROK_INITIALIZER = "const snapshot = decodeTransport(" + GROK_SNAPSHOT_MARKER + ");"
GROK_DATA_CHARS = 2048


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


def recovery_grok_canvas(snapshot: dict) -> str:
    """Embed the canonical view fields in the packaged native Grok Page source."""
    template = (Path(__file__).with_name("ui") / "recovery.canvas.tsx").read_text(encoding="utf-8")
    if template.count(GROK_SNAPSHOT_MARKER) != 1:
        raise ValueError("Grok Page template must contain exactly one snapshot marker.")
    # ASCII JSON also escapes JS line separators. Escape HTML delimiters even
    # though this is source code, so data cannot terminate a later script wrapper.
    payload = json.dumps(pack_grok_snapshot(snapshot), ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    for character, escaped in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026")):
        payload = payload.replace(character, escaped)
    if template.count(GROK_INITIALIZER) != 1:
        raise ValueError("Grok Page template has an unsupported snapshot initializer.")
    # Complete, inert declarations can be inserted in separate native edits.
    # Join before parsing, so a boundary may safely bisect a JSON escape sequence.
    parts = [payload[i:i + GROK_DATA_CHARS] for i in range(0, len(payload), GROK_DATA_CHARS)]
    names = [f"transportPart{i}" for i in range(len(parts))]
    declarations = "\n".join(f"const {name} = {json.dumps(part, ensure_ascii=True)};"
                             for name, part in zip(names, parts))
    initializer = "const snapshot = decodeTransport(JSON.parse([" + ",".join(names) + "].join(\"\")));"
    source = template.replace(GROK_INITIALIZER, declarations + "\n" + initializer)
    if len(source.encode("utf-8")) > MAX_GROK_CANVAS_BYTES:
        raise ValueError("Grok Page exceeds the workbench's 1 MiB export limit; choose a shorter date range. This is not a documented Grok host limit.")
    return source


def write_recovery_widget(db, output: Path, start: str = "", end: str = "", *, host: str = "muse") -> dict:
    output = output.expanduser().absolute()
    if host not in {"muse", "grok"}:
        raise ValueError("Widget host must be muse or grok.")
    if host == "grok" and not output.name.endswith(".canvas.tsx"):
        raise ValueError("Grok Page output must be a new .canvas.tsx file.")
    if host == "muse" and output.suffix.lower() != ".html":
        raise ValueError("Widget output must be a new .html file.")
    snapshot = recovery_widget_snapshot(db, start, end)
    source = recovery_grok_canvas(snapshot) if host == "grok" else recovery_widget_html(snapshot)
    encoded = source.encode("utf-8")
    with open(output, "xb", opener=lambda path, flags: os.open(path, flags, 0o600)) as file:
        file.write(encoded)
    report = snapshot["report"]
    delivery = ("Saved native Grok Page source. Include --handoff-dir when exporting with "
                "widget sleep-recovery --host grok, using new output paths, to generate bounded "
                "WriteCanvas/EditCanvas delivery and source verification calls for a private Page. "
                "Do not pass a file path or $file substitution to WriteCanvas. "
                "Keep the packaged source unchanged, compare full ReadCanvas output, and verify Only you access. "
                "Stop on a failed handoff instead of silently rewriting the chart. "
                "File creation does not prove native compilation or display."
                if host == "grok" else
                "Saved HTML fragment. Present unchanged using widget.create_html_file_widget; file creation does not prove display.")
    return {"output_path": str(output), "bytes": len(encoded),
            "from": report["from"], "to": report["to"],
            "archive_provenance": report["archive_provenance"],
            "delivery": delivery}

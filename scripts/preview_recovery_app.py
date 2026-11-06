"""Generate a synthetic MCP Apps host harness for browser inspection (no server).

Development only. Open through the assistant's HTML preview or a test browser;
this is not an end-user HTML export or a claim of actual assistant integration.
"""
import argparse
import json
import tempfile
from pathlib import Path

from create_demo_archive import create_demo_archive
from garmin_archive.mcp_apps import recovery_app_html
from garmin_archive.queries import open_archive
from garmin_archive.recovery import compare_sleep_recovery, get_sleep_recovery
from garmin_archive.widgets import recovery_widget_html, recovery_widget_snapshot


def safe_json(value):
    return json.dumps(value).replace('<', '\\u003c')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--view', choices=('trends', 'night', 'compare'), default='trends')
    parser.add_argument('--host', choices=('mcp', 'muse'), default='mcp')
    args = parser.parse_args()
    ranges = [('2026-04-17', '2026-04-30'), ('2026-01-12', '2026-01-18'),
              ('2026-02-05', '2026-02-08'), ('2026-03-12', '2026-03-18'),
              ('2026-01-16', '2026-01-16')]
    with tempfile.TemporaryDirectory(prefix='garmin-ui-harness-') as temp:
        archive = Path(temp) / 'synthetic'
        create_demo_archive(archive)
        with open_archive(archive) as db:
            payloads = {'|'.join(r): get_sleep_recovery(db, *r) for r in ranges}
            comparison = compare_sleep_recovery(db, '2026-04-24', '2026-04-30', '2026-04-17', '2026-04-23')
            widget = recovery_widget_html(recovery_widget_snapshot(db, *ranges[0])) if args.host == 'muse' else None
    template = Path(__file__).with_name('recovery_widget_harness.html' if widget else 'recovery_app_harness.html').read_text(encoding='utf-8')
    template = template.replace('__APP_JSON__', safe_json(widget or recovery_app_html()))
    template = template.replace('__PAYLOADS__', safe_json(payloads)).replace('__COMPARISON__', safe_json(comparison))
    template = template.replace('__FINAL_VIEW__', safe_json(args.view))
    with args.output.open('x', encoding='utf-8') as out:
        out.write(template)
    print(args.output)


if __name__ == '__main__':
    main()

"""Export synthetic Grok sources and query receipts for the local browser harness.

Development only: no credentials, existing archive, HTTP server or native Grok
connection. The browser harness substitutes React wrappers for grok/canvas; it
does not verify Grok's compiler, sandbox, delivery or native theme implementation.

    uv run --locked python scripts/preview_grok_widget.py --output-dir /new/fixtures
    npm ci --prefix scripts/grok_harness
    npm exec --prefix scripts/grok_harness -- playwright install chromium webkit
    node scripts/test_grok_widget.mjs --fixtures /new/fixtures --output-dir /checks
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path

from create_demo_archive import create_demo_archive
from garmin_archive.archive import Archive
from garmin_archive.brand import brand_tokens_canvas, get_brand
from garmin_archive.queries import open_archive
from garmin_archive.widgets import recovery_grok_canvas, recovery_widget_snapshot


def edge_archive(destination: Path) -> None:
    """Invented zero and independent failure cases, never derived from user data."""
    archive = Archive(destination)
    try:
        archive.mark_synthetic('grok-renderer-edges-1', 42, '2026-02-01T00:00:00+00:00')
        for index, duration in enumerate((27000, 0, 28800), 1):
            day = f'2026-01-{index:02d}'
            archive.save_daily('sleep', day, {
                'calendarDate': day, 'sleepTimeSeconds': duration,
                'deepSleepSeconds': 0, 'lightSleepSeconds': duration,
                'remSleepSeconds': 0, 'unmeasurableSleepSeconds': 0,
                'awakeSleepSeconds': 0, 'napTimeSeconds': 0,
                'sleepScores': {'overall': {'value': 0}},
                'sleepNeed': {'actual': 480},
                'sleepStartTimestampLocal': '2026-01-01T22:30:00',
            })
            archive.save_daily('hrv', day, {'hrvSummary': {'lastNightAvg': 55}})
            archive.save_daily('heart_rate', day, {'restingHeartRate': 50})
        archive.mark_error('hrv', '2026-01-02', 'Invented failed refresh')
        archive.mark_error('sleep', '2026-01-03', 'Invented failed refresh')
    finally:
        archive.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='New destination for synthetic source files and fixtures.json')
    args = parser.parse_args()
    destination = args.output_dir.expanduser().absolute()
    destination.mkdir(parents=True, exist_ok=False)
    scenarios = [
        ('normal', 'demo', '2026-04-17', '2026-04-30'),
        ('failure', 'demo', '2026-01-12', '2026-01-18'),
        ('incomplete', 'demo', '2026-02-05', '2026-02-09'),
        ('missing', 'demo', '2026-03-12', '2026-03-18'),
        ('single', 'demo', '2026-01-16', '2026-01-16'),
        ('ninety', 'demo', '2026-01-01', '2026-03-31'),
        ('zero', 'edges', '2026-01-01', '2026-01-04'),
        ('warning', 'demo', '2026-04-17', '2026-04-30'),
    ]
    snapshots, source_hashes = {}, {}
    with tempfile.TemporaryDirectory(prefix='garmin-grok-harness-') as temporary:
        root = Path(temporary)
        create_demo_archive(root / 'demo')
        edge_archive(root / 'edges')
        for name, archive, first, last in scenarios:
            with open_archive(root / archive) as db:
                snapshots[name] = recovery_widget_snapshot(db, first, last)
            if name == 'warning':
                # Controlled presentation fixture. These warning flags are injected
                # into invented data so this check is independent of today's date.
                for comparison in snapshots[name]['comparison']['metrics'].values():
                    comparison['warnings'].extend([
                        'baseline_includes_today_or_future', 'period_includes_today_or_future'])
            source = recovery_grok_canvas(snapshots[name])
            source_hashes[name] = hashlib.sha256(source.encode('utf-8')).hexdigest()
            with (destination / f'{name}.canvas.tsx').open('x', encoding='utf-8', newline='') as out:
                out.write(source)
    with (destination / 'fixtures.json').open('x', encoding='utf-8') as out:
        brand = get_brand()
        json.dump({'synthetic': True, 'source_sha256': source_hashes,
                   'brand': {'colors': brand['colors'], 'dark_colors': brand['dark_colors']},
                   'brand_tokens': brand_tokens_canvas(),
                   'scenario_notes': {'warning': 'Current/future query warning flags injected into invented demo data for presentation testing; dates and observations are unchanged.'},
                   'snapshots': snapshots}, out, ensure_ascii=True, indent=2)
        out.write('\n')
    print(destination)


if __name__ == '__main__':
    main()

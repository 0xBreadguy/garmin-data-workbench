"""Read explicit archive provenance without migration or filesystem date guesses."""
from pathlib import Path


def archive_provenance(db) -> dict:
    row = None
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='archive_provenance'").fetchone():
        row = db.execute("SELECT * FROM archive_provenance WHERE id=1").fetchone()
    # Legacy demos only have a sidecar. Never read its contents into tool output.
    filename = next((r[2] for r in db.execute('PRAGMA database_list') if r[1] == 'main'), '')
    marker = bool(filename and (Path(filename).parent / 'SYNTHETIC.txt').is_file())
    synthetic = marker or bool(row and row['kind'] == 'synthetic')
    return {'kind': 'synthetic' if synthetic else 'unmarked',
            'synthetic': True if synthetic else None, 'marker_present': marker,
            'created_at': row['created_at'] if row else None,
            'corpus_version': row['corpus_version'] if row else None,
            'seed': row['seed'] if row else None,
            'freshness_meaning': ('Fixture timestamps are simulated; no live Garmin fetch was performed.' if synthetic else
                                  'Fetch times describe local collection, not measurement times. Unmarked provenance is unknown.')}

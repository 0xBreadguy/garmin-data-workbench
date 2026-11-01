"""SQLite storage and query helpers. The original activity ZIP is retained."""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS daily_data (
    dataset TEXT NOT NULL,
    day TEXT NOT NULL,
    data_json TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    PRIMARY KEY (dataset, day)
);
CREATE TABLE IF NOT EXISTS sync_state (
    dataset TEXT NOT NULL,
    day TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ok', 'empty', 'error')),
    error TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (dataset, day)
);
CREATE TABLE IF NOT EXISTS activities (
    activity_id INTEGER PRIMARY KEY,
    day TEXT NOT NULL,
    summary_json TEXT NOT NULL,
    original_zip BLOB,
    fit_status TEXT NOT NULL DEFAULT 'pending',
    fit_error TEXT,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS activities_by_day ON activities(day);
CREATE TABLE IF NOT EXISTS activity_messages (
    activity_id INTEGER NOT NULL REFERENCES activities(activity_id) ON DELETE CASCADE,
    message_type TEXT NOT NULL,
    message_index INTEGER NOT NULL,
    timestamp TEXT,
    data_json TEXT NOT NULL,
    PRIMARY KEY (activity_id, message_type, message_index)
);
CREATE INDEX IF NOT EXISTS activity_messages_timestamp
    ON activity_messages(activity_id, message_type, timestamp);
CREATE VIEW IF NOT EXISTS activity_records AS
    SELECT activity_id, message_index AS record_index, timestamp,
           json_extract(data_json, '$.heart_rate') AS heart_rate_bpm,
           json_extract(data_json, '$.power') AS power_w,
           json_extract(data_json, '$.cadence') AS cadence_rpm,
           json_extract(data_json, '$.distance') AS distance_m,
           json_extract(data_json, '$.enhanced_speed') AS enhanced_speed_mps,
           data_json
    FROM activity_messages WHERE message_type = 'record_mesgs';
"""


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        # FIT timestamps are UTC instants. The SDK may return naive UTC values.
        return value.replace(tzinfo=UTC).isoformat() if value.tzinfo is None else value.isoformat()
    if isinstance(value, bytes):
        return {"bytes_hex": value.hex()}
    raise TypeError(f"Unsupported value type: {type(value).__name__}")


def json_text(value: Any) -> str:
    return json.dumps(value, default=_json_default, ensure_ascii=False, separators=(",", ":"))


def now() -> str:
    return datetime.now(UTC).isoformat()


def default_data_dir() -> Path:
    # Keep health data out of the source checkout by default on every platform.
    configured = os.environ.get("XDG_DATA_HOME")
    root = Path(configured) if configured and Path(configured).is_absolute() else Path.home() / ".local" / "share"
    return root / "garmin-extraction"


class Archive:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir.expanduser()
        self.data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.path = self.data_dir / "archive.sqlite3"
        # Create a new database with private permissions independently of umask.
        fd = os.open(self.path, os.O_CREAT | os.O_WRONLY, 0o600)
        os.close(fd)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        version = self.connection.execute("PRAGMA user_version").fetchone()[0]
        if version > 1:
            self.connection.close()
            raise ValueError("Archive schema is newer than this version of the tool")
        self.connection.executescript(SCHEMA)
        self.connection.execute("PRAGMA user_version = 1")
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def state(self, dataset: str, day: str) -> str | None:
        row = self.connection.execute(
            "SELECT status FROM sync_state WHERE dataset = ? AND day = ?", (dataset, day)
        ).fetchone()
        return row["status"] if row else None

    def set_state(self, dataset: str, day: str, status: str, error: str | None = None) -> None:
        self.connection.execute(
            """INSERT INTO sync_state VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(dataset, day) DO UPDATE SET
               status=excluded.status, error=excluded.error, updated_at=excluded.updated_at""",
            (dataset, day, status, error, now()),
        )

    def save_daily(self, dataset: str, day: str, data: Any) -> None:
        empty = data is None or data == {} or data == [] or data == {"data": []}
        with self.connection:
            self.connection.execute(
                """INSERT INTO daily_data VALUES (?, ?, ?, ?)
                   ON CONFLICT(dataset, day) DO UPDATE SET
                   data_json=excluded.data_json, fetched_at=excluded.fetched_at""",
                (dataset, day, json_text(data), now()),
            )
            self.set_state(dataset, day, "empty" if empty else "ok")

    def mark_error(self, dataset: str, day: str, error: str) -> None:
        with self.connection:
            self.set_state(dataset, day, "error", error)

    def save_activities(self, day: str, activities: list[dict[str, Any]]) -> None:
        with self.connection:
            for activity in activities:
                activity_id = activity.get("activityId")
                if isinstance(activity_id, bool) or not isinstance(activity_id, int) or activity_id <= 0:
                    raise ValueError("Activity is missing a valid activityId")
                self.connection.execute(
                    """INSERT INTO activities(activity_id, day, summary_json, updated_at)
                       VALUES (?, ?, ?, ?) ON CONFLICT(activity_id) DO UPDATE SET
                       day=excluded.day, summary_json=excluded.summary_json,
                       updated_at=excluded.updated_at""",
                    (activity_id, day, json_text(activity), now()),
                )
            self.set_state("activities", day, "ok" if activities else "empty")

    def activities_needing_fit(self, start: str, end: str) -> list[int]:
        rows = self.connection.execute(
            """SELECT activity_id FROM activities WHERE day BETWEEN ? AND ?
               AND fit_status NOT IN ('ok', 'unsupported') ORDER BY day, activity_id""",
            (start, end),
        )
        return [row["activity_id"] for row in rows]

    def save_original(self, activity_id: int, content: bytes) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE activities SET original_zip=?, fit_status='pending', fit_error=NULL WHERE activity_id=?",
                (content, activity_id),
            )

    def save_messages(self, activity_id: int, messages: dict[Any, list[dict[Any, Any]]]) -> None:
        # Replace messages and mark completion in one transaction, so a decoder
        # failure never destroys an earlier successful parse.
        with self.connection:
            self.connection.execute("DELETE FROM activity_messages WHERE activity_id=?", (activity_id,))
            for kind, entries in messages.items():
                for index, message in enumerate(entries):
                    timestamp = message.get("timestamp")
                    stamp = _json_default(timestamp) if isinstance(timestamp, datetime) else timestamp
                    self.connection.execute(
                        "INSERT INTO activity_messages VALUES (?, ?, ?, ?, ?)",
                        (activity_id, str(kind), index, stamp, json_text(message)),
                    )
            self.connection.execute(
                "UPDATE activities SET fit_status='ok', fit_error=NULL WHERE activity_id=?", (activity_id,)
            )

    def set_fit_status(self, activity_id: int, status: str, error: str | None = None) -> None:
        with self.connection:
            self.connection.execute(
                "UPDATE activities SET fit_status=?, fit_error=? WHERE activity_id=?",
                (status, error, activity_id),
            )

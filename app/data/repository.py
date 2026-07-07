import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class PredictionRepository:
    def __init__(self, db_path: str = "data/predictions.sqlite3") -> None:
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_db(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS prediction_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )

    def save_snapshot(self, match_id: str, payload: dict[str, Any]) -> int:
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            cursor = connection.execute(
                "INSERT INTO prediction_snapshots (match_id, created_at, payload) VALUES (?, ?, ?)",
                (match_id, created_at, json.dumps(payload)),
            )
            return int(cursor.lastrowid)

    def list_snapshots(self, match_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, match_id, created_at, payload FROM prediction_snapshots WHERE match_id = ? ORDER BY id DESC",
                (match_id,),
            ).fetchall()
        return [
            {
                "id": row["id"],
                "match_id": row["match_id"],
                "created_at": row["created_at"],
                "payload": json.loads(row["payload"]),
            }
            for row in rows
        ]

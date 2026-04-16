from __future__ import annotations

import sqlite3
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any

from models import AutoReplyLog


class AutoReplyLogStore:
    def __init__(self, storage_path: str) -> None:
        self.storage_path = Path(storage_path)
        self._lock = threading.Lock()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.storage_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS auto_reply_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    sender_name TEXT NOT NULL,
                    sender_tag TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    team_id TEXT,
                    team_name TEXT NOT NULL,
                    template_id TEXT NOT NULL,
                    manual_required INTEGER NOT NULL,
                    reason TEXT NOT NULL,
                    reply_text TEXT NOT NULL
                )
                """
            )
            connection.commit()

    def insert(self, entry: AutoReplyLog) -> int:
        payload = asdict(entry)
        payload["manual_required"] = int(entry.manual_required)

        with self._lock, self._connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO auto_reply_logs (
                    created_at, user_id, sender_name, sender_tag, message_text,
                    intent, team_id, team_name, template_id, manual_required,
                    reason, reply_text
                ) VALUES (
                    :created_at, :user_id, :sender_name, :sender_tag, :message_text,
                    :intent, :team_id, :team_name, :template_id, :manual_required,
                    :reason, :reply_text
                )
                """,
                payload,
            )
            connection.commit()
        return int(cursor.lastrowid)

    def list_recent(self, limit: int = 100) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 500))
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM auto_reply_logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
        return [dict(row) for row in rows]

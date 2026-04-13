from __future__ import annotations

import sqlite3
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class PendingManualReply:
    request_id: str
    user_id: str
    message_text: str
    reply_token: str
    team_id: str | None
    team_name: str
    template_id: str
    reason: str
    created_at: str
    status: str = "pending"
    manual_reply_text: str = ""
    replied_at: str = ""


class ManualReplyStore:
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
                CREATE TABLE IF NOT EXISTS manual_replies (
                    request_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    message_text TEXT NOT NULL,
                    reply_token TEXT NOT NULL,
                    team_id TEXT,
                    team_name TEXT NOT NULL,
                    template_id TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    manual_reply_text TEXT NOT NULL,
                    replied_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_manual_replies_pending_reply_token
                ON manual_replies(reply_token, status)
                """
            )
            connection.commit()

    def enqueue(self, entry: PendingManualReply) -> None:
        payload = asdict(entry)
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO manual_replies (
                    request_id, user_id, message_text, reply_token, team_id, team_name,
                    template_id, reason, created_at, status, manual_reply_text, replied_at
                ) VALUES (
                    :request_id, :user_id, :message_text, :reply_token, :team_id, :team_name,
                    :template_id, :reason, :created_at, :status, :manual_reply_text, :replied_at
                )
                """,
                payload,
            )
            connection.commit()

    def has_pending(self, *, reply_token: str) -> bool:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM manual_replies
                WHERE reply_token = ? AND status = 'pending'
                LIMIT 1
                """,
                (reply_token,),
            ).fetchone()
        return row is not None

    def list_pending(self) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM manual_replies
                WHERE status = 'pending'
                ORDER BY created_at ASC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_replied(self, request_id: str, manual_reply_text: str) -> dict[str, Any] | None:
        replied_at = datetime.now(timezone.utc).isoformat()
        with self._lock, self._connect() as connection:
            connection.execute(
                """
                UPDATE manual_replies
                SET status = 'replied',
                    manual_reply_text = ?,
                    replied_at = ?
                WHERE request_id = ?
                """,
                (manual_reply_text, replied_at, request_id),
            )
            row = connection.execute(
                """
                SELECT *
                FROM manual_replies
                WHERE request_id = ?
                """,
                (request_id,),
            ).fetchone()
            connection.commit()
        return dict(row) if row else None

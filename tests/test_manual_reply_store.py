from __future__ import annotations

from pathlib import Path

from manual_reply_store import ManualReplyStore, PendingManualReply


def test_manual_reply_store_enqueue_and_list_pending(tmp_path: Path) -> None:
    store = ManualReplyStore(str(tmp_path / "pending.json"))
    store.enqueue(
        PendingManualReply(
            request_id="req-001",
            user_id="user-001",
            message_text="価格を教えて",
            reply_token="token-001",
            team_id=None,
            team_name="",
            template_id="TMP-002",
            reason="team_not_found",
            created_at="2026-04-12T00:00:00+00:00",
        )
    )

    rows = store.list_pending()

    assert len(rows) == 1
    assert rows[0]["request_id"] == "req-001"
    assert rows[0]["status"] == "pending"


def test_manual_reply_store_mark_replied(tmp_path: Path) -> None:
    store = ManualReplyStore(str(tmp_path / "pending.json"))
    store.enqueue(
        PendingManualReply(
            request_id="req-002",
            user_id="user-002",
            message_text="未登録チームです",
            reply_token="token-002",
            team_id=None,
            team_name="",
            template_id="TMP-002",
            reason="team_not_found",
            created_at="2026-04-12T00:00:00+00:00",
        )
    )

    updated = store.mark_replied("req-002", "担当者が確認してご連絡します。")

    assert updated is not None
    assert updated["status"] == "replied"
    assert updated["manual_reply_text"] == "担当者が確認してご連絡します。"
    assert store.list_pending() == []


def test_manual_reply_store_deduplicates_pending_reply_token(tmp_path: Path) -> None:
    store = ManualReplyStore(str(tmp_path / "pending.db"))
    common_reply_token = "token-dup"

    store.enqueue(
        PendingManualReply(
            request_id="req-010",
            user_id="user-010",
            message_text="確認してください",
            reply_token=common_reply_token,
            team_id=None,
            team_name="",
            template_id="TMP-002",
            reason="team_not_found",
            created_at="2026-04-12T00:00:00+00:00",
        )
    )
    store.enqueue(
        PendingManualReply(
            request_id="req-011",
            user_id="user-010",
            message_text="確認してください",
            reply_token=common_reply_token,
            team_id=None,
            team_name="",
            template_id="TMP-002",
            reason="team_not_found",
            created_at="2026-04-12T00:00:01+00:00",
        )
    )

    rows = store.list_pending()

    assert len(rows) == 1
    assert store.has_pending(reply_token=common_reply_token) is True

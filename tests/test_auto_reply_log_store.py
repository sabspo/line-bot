from __future__ import annotations

from auto_reply_log_store import AutoReplyLogStore
from models import AutoReplyLog


def test_auto_reply_log_store_inserts_and_lists_recent(tmp_path) -> None:
    store = AutoReplyLogStore(str(tmp_path / "auto_reply_logs.db"))

    row_id = store.insert(
        AutoReplyLog(
            created_at="2026-04-16T00:00:00+00:00",
            user_id="user-001",
            sender_name="つくしヤングラガーズ小学部",
            sender_tag="小学部保護者",
            message_text="価格を教えてください",
            intent="price_inquiry",
            team_id="TEAM-001",
            team_name="つくしヤングラガーズ小学部",
            template_id="TMP-001",
            manual_required=False,
            reason="auto_price_list",
            reply_text="価格一覧です",
        )
    )

    rows = store.list_recent()

    assert row_id >= 1
    assert len(rows) == 1
    assert rows[0]["user_id"] == "user-001"
    assert rows[0]["sender_tag"] == "小学部保護者"
    assert rows[0]["manual_required"] == 0

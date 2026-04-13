from __future__ import annotations

from pathlib import Path

import app as app_module
from manual_reply_store import ManualReplyStore, PendingManualReply


def _build_store(tmp_path: Path) -> ManualReplyStore:
    return ManualReplyStore(str(tmp_path / "pending_manual_replies.json"))


def test_list_manual_replies_requires_token(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "MANUAL_REPLY_ADMIN_TOKEN", "secret-token")
    monkeypatch.setattr(app_module, "manual_reply_store", _build_store(tmp_path))
    client = app_module.app.test_client()

    response = client.get("/manual-replies")

    assert response.status_code == 403


def test_list_manual_replies_returns_pending_rows(tmp_path: Path, monkeypatch) -> None:
    store = _build_store(tmp_path)
    store.enqueue(
        PendingManualReply(
            request_id="req-003",
            user_id="user-003",
            message_text="手動対応してください",
            reply_token="token-003",
            team_id="TEAM-003",
            team_name="未登録チーム",
            template_id="TMP-002",
            reason="team_not_found",
            created_at="2026-04-12T00:00:00+00:00",
        )
    )
    monkeypatch.setattr(app_module, "MANUAL_REPLY_ADMIN_TOKEN", "secret-token")
    monkeypatch.setattr(app_module, "manual_reply_store", store)
    client = app_module.app.test_client()

    response = client.get("/manual-replies", headers={"X-Admin-Token": "secret-token"})

    assert response.status_code == 200
    payload = response.get_json()
    assert len(payload) == 1
    assert payload[0]["request_id"] == "req-003"


def test_manual_replies_ui_renders_pending_rows(tmp_path: Path, monkeypatch) -> None:
    store = _build_store(tmp_path)
    store.enqueue(
        PendingManualReply(
            request_id="req-004",
            user_id="user-004",
            message_text="価格が分かりません",
            reply_token="token-004",
            team_id="TEAM-004",
            team_name="確認待ちチーム",
            template_id="TMP-004",
            reason="no_items",
            created_at="2026-04-12T00:00:00+00:00",
        )
    )
    monkeypatch.setattr(app_module, "MANUAL_REPLY_ADMIN_TOKEN", "secret-token")
    monkeypatch.setattr(app_module, "manual_reply_store", store)
    client = app_module.app.test_client()

    response = client.get("/manual-replies/ui", headers={"X-Admin-Token": "secret-token"})

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "手動返信キュー" in body
    assert "確認待ちチーム" in body
    assert "req-004" in body


def test_send_manual_reply_marks_request_replied(tmp_path: Path, monkeypatch) -> None:
    store = _build_store(tmp_path)
    store.enqueue(
        PendingManualReply(
            request_id="req-005",
            user_id="user-005",
            message_text="人が確認してください",
            reply_token="token-005",
            team_id=None,
            team_name="",
            template_id="TMP-002",
            reason="team_not_found",
            created_at="2026-04-12T00:00:00+00:00",
        )
    )
    sent_messages: list[tuple[str, str]] = []

    monkeypatch.setattr(app_module, "MANUAL_REPLY_ADMIN_TOKEN", "secret-token")
    monkeypatch.setattr(app_module, "manual_reply_store", store)
    monkeypatch.setattr(
        app_module,
        "_push_manual_reply",
        lambda user_id, message_text: sent_messages.append((user_id, message_text)),
    )
    client = app_module.app.test_client()

    response = client.post(
        "/manual-replies/req-005/reply",
        headers={"X-Admin-Token": "secret-token"},
        json={"user_id": "user-005", "message_text": "担当者が折り返します。"},
    )

    assert response.status_code == 200
    assert sent_messages == [("user-005", "担当者が折り返します。")]
    payload = response.get_json()
    assert payload["status"] == "replied"


def test_list_manual_replies_requires_basic_auth_when_enabled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "MANUAL_REPLY_ADMIN_TOKEN", "secret-token")
    monkeypatch.setattr(app_module, "MANUAL_REPLY_ADMIN_USERNAME", "admin")
    monkeypatch.setattr(app_module, "MANUAL_REPLY_ADMIN_PASSWORD", "password")
    monkeypatch.setattr(app_module, "manual_reply_store", _build_store(tmp_path))
    client = app_module.app.test_client()

    response = client.get("/manual-replies", headers={"X-Admin-Token": "secret-token"})

    assert response.status_code == 401


def test_handle_message_queues_manual_reply_only_once(tmp_path: Path, monkeypatch) -> None:
    store = _build_store(tmp_path)
    monkeypatch.setattr(app_module, "manual_reply_store", store)
    monkeypatch.setattr(
        app_module,
        "generate_reply_decision",
        lambda _message: type(
            "Decision",
            (),
            {
                "reply_text": "確認してご案内します。",
                "team_id": None,
                "team_name": "",
                "template_id": "TMP-002",
                "manual_required": True,
                "reason": "team_not_found",
            },
        )(),
    )
    sent_replies: list[str] = []

    class DummyApiClient:
        def __init__(self, _configuration):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyMessagingApi:
        def __init__(self, _api_client):
            pass

        def reply_message(self, request):
            sent_replies.append(request.messages[0].text)

    monkeypatch.setattr(app_module, "configuration", object())
    monkeypatch.setattr(app_module, "handler", object())
    monkeypatch.setattr(app_module, "ApiClient", DummyApiClient)
    monkeypatch.setattr(app_module, "MessagingApi", DummyMessagingApi)

    event = type(
        "Event",
        (),
        {
            "message": type("Message", (), {"text": "手動対応してください"})(),
            "reply_token": "dup-token",
            "source": type("Source", (), {"user_id": "user-dup"})(),
        },
    )()

    app_module.handle_message(event)
    app_module.handle_message(event)

    assert len(store.list_pending()) == 1
    assert len(sent_replies) == 2

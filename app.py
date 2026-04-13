from __future__ import annotations

import base64
import logging
import os
from datetime import datetime, timezone
from uuid import uuid4

from flask import Flask, abort, jsonify, render_template_string, request
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PushMessageRequest,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

from config import (
    MANUAL_REPLY_ADMIN_PASSWORD,
    MANUAL_REPLY_ADMIN_TOKEN,
    MANUAL_REPLY_ADMIN_USERNAME,
    MANUAL_REPLY_STORAGE_FILE,
)
from manual_reply_store import ManualReplyStore, PendingManualReply
from reply_service import generate_reply_decision

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CHANNEL_ACCESS_TOKEN = os.environ.get("CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.environ.get("CHANNEL_SECRET")

configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN) if CHANNEL_ACCESS_TOKEN else None
handler = WebhookHandler(CHANNEL_SECRET) if CHANNEL_SECRET else None
manual_reply_store = ManualReplyStore(MANUAL_REPLY_STORAGE_FILE)


def _require_line_configuration() -> tuple[Configuration, WebhookHandler]:
    if not configuration or not handler:
        raise RuntimeError("CHANNEL_ACCESS_TOKEN and CHANNEL_SECRET must be configured.")
    return configuration, handler


def _require_admin_token() -> None:
    if not MANUAL_REPLY_ADMIN_TOKEN:
        abort(503, description="MANUAL_REPLY_ADMIN_TOKEN is not configured.")
    provided = request.headers.get("X-Admin-Token", "")
    if provided != MANUAL_REPLY_ADMIN_TOKEN:
        abort(403)


def _require_admin_basic_auth() -> None:
    if not MANUAL_REPLY_ADMIN_USERNAME and not MANUAL_REPLY_ADMIN_PASSWORD:
        return

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Basic "):
        abort(401)

    encoded = auth_header.split(" ", 1)[1].strip()
    try:
        decoded = base64.b64decode(encoded).decode("utf-8")
    except Exception:
        abort(401)

    username, _, password = decoded.partition(":")
    if username != MANUAL_REPLY_ADMIN_USERNAME or password != MANUAL_REPLY_ADMIN_PASSWORD:
        abort(403)


def _require_admin_access() -> None:
    _require_admin_token()
    _require_admin_basic_auth()


def _push_manual_reply(user_id: str, message_text: str) -> None:
    current_configuration, _ = _require_line_configuration()
    with ApiClient(current_configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.push_message(
            PushMessageRequest(
                to=user_id,
                messages=[TextMessage(text=message_text)],
            )
        )


@app.route("/", methods=["GET"])
def hello():
    return "Hello LINE Bot!"


@app.route("/callback", methods=["POST"])
def callback():
    _, current_handler = _require_line_configuration()
    signature = request.headers.get("X-Line-Signature")
    body = request.get_data(as_text=True)

    try:
        current_handler.handle(body, signature)
    except InvalidSignatureError:
        return "Invalid signature", 400

    return "OK"


@app.route("/manual-replies", methods=["GET"])
def list_manual_replies():
    _require_admin_access()
    return jsonify(manual_reply_store.list_pending())


@app.route("/manual-replies/ui", methods=["GET"])
def manual_replies_ui():
    _require_admin_access()
    pending_rows = manual_reply_store.list_pending()
    return render_template_string(
        """
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <title>Manual Replies</title>
  <style>
    :root {
      --bg: #f5f1e8;
      --panel: #fffaf0;
      --line: #d9c9a3;
      --text: #2f2419;
      --accent: #8a4b08;
      --muted: #6e6255;
    }
    body {
      margin: 0;
      padding: 24px;
      background: linear-gradient(180deg, #efe3c5, var(--bg));
      color: var(--text);
      font-family: "Yu Gothic UI", "Hiragino Sans", sans-serif;
    }
    h1 {
      margin: 0 0 16px;
      font-size: 28px;
    }
    .meta {
      margin-bottom: 20px;
      color: var(--muted);
    }
    .list {
      display: grid;
      gap: 16px;
    }
    .card {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 16px;
      box-shadow: 0 10px 30px rgba(47, 36, 25, 0.08);
    }
    .row {
      margin-bottom: 8px;
      white-space: pre-wrap;
      word-break: break-word;
    }
    .label {
      color: var(--accent);
      font-weight: 700;
    }
    textarea {
      width: 100%;
      min-height: 120px;
      margin-top: 12px;
      border-radius: 12px;
      border: 1px solid var(--line);
      padding: 12px;
      font: inherit;
      box-sizing: border-box;
      background: #fff;
    }
    button {
      margin-top: 12px;
      border: 0;
      border-radius: 999px;
      padding: 10px 18px;
      background: var(--accent);
      color: #fff;
      font: inherit;
      cursor: pointer;
    }
    .empty {
      padding: 24px;
      background: var(--panel);
      border-radius: 16px;
      border: 1px dashed var(--line);
    }
  </style>
</head>
<body>
  <h1>手動返信キュー</h1>
  <div class="meta">未対応 {{ pending_rows|length }} 件</div>
  {% if pending_rows %}
    <div class="list">
      {% for row in pending_rows %}
        <form class="card" method="post" action="/manual-replies/{{ row.request_id }}/reply">
          <input type="hidden" name="user_id" value="{{ row.user_id }}">
          <div class="row"><span class="label">request_id:</span> {{ row.request_id }}</div>
          <div class="row"><span class="label">team:</span> {{ row.team_name or "-" }} / {{ row.team_id or "-" }}</div>
          <div class="row"><span class="label">reason:</span> {{ row.reason }}</div>
          <div class="row"><span class="label">message:</span> {{ row.message_text }}</div>
          <textarea name="message_text" placeholder="ここに手動返信文を入力">{{ row.team_name or "対象チーム" }} について確認してご案内します。少々お待ちください。</textarea>
          <button type="submit">この内容で送信</button>
        </form>
      {% endfor %}
    </div>
  {% else %}
    <div class="empty">未対応の手動返信はありません。</div>
  {% endif %}
</body>
</html>
        """,
        pending_rows=pending_rows,
    )


@app.route("/manual-replies/<request_id>/reply", methods=["POST"])
def send_manual_reply(request_id: str):
    _require_admin_access()
    payload = request.get_json(silent=True)
    if payload is None:
        payload = request.form.to_dict()
    message_text = str(payload.get("message_text", "")).strip()
    user_id = str(payload.get("user_id", "")).strip()

    if not message_text or not user_id:
        return jsonify({"error": "user_id and message_text are required"}), 400

    _push_manual_reply(user_id, message_text)
    updated = manual_reply_store.mark_replied(request_id, message_text)
    if not updated:
        return jsonify({"error": "request_id not found"}), 404
    if request.is_json:
        return jsonify(updated)
    return (
        render_template_string(
            """
<!doctype html>
<html lang="ja">
<head><meta charset="utf-8"><title>Reply Sent</title></head>
<body style="font-family: 'Yu Gothic UI', sans-serif; padding: 24px; background: #f5f1e8;">
  <h1>手動返信を送信しました</h1>
  <p>request_id: {{ row.request_id }}</p>
  <p><a href="/manual-replies/ui">一覧に戻る</a></p>
</body>
</html>
            """,
            row=updated,
        ),
        200,
    )


def handle_message(event):
    user_message = event.message.text
    user_id = getattr(getattr(event, "source", None), "user_id", "") or ""
    reply_token = event.reply_token

    try:
        decision = generate_reply_decision(user_message)
    except Exception as exc:
        logger.exception("Automatic reply failed")
        decision = type("FallbackDecision", (), {
            "reply_text": "確認してご案内します。少々お待ちください。",
            "team_id": None,
            "team_name": "",
            "template_id": "MANUAL-FALLBACK",
            "manual_required": True,
            "reason": f"exception:{type(exc).__name__}",
        })()

    if decision.manual_required and user_id and not manual_reply_store.has_pending(reply_token=reply_token):
        manual_reply_store.enqueue(
            PendingManualReply(
                request_id=str(uuid4()),
                user_id=user_id,
                message_text=user_message,
                reply_token=reply_token,
                team_id=decision.team_id,
                team_name=decision.team_name,
                template_id=decision.template_id,
                reason=decision.reason,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        )
        logger.info(
            "Queued manual reply: user_id=%s template_id=%s reason=%s",
            user_id,
            decision.template_id,
            decision.reason,
        )
    elif decision.manual_required and user_id:
        logger.info("Skipped duplicate manual reply queueing: reply_token=%s", reply_token)

    current_configuration, _ = _require_line_configuration()
    with ApiClient(current_configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=decision.reply_text)],
            )
        )


if handler:
    handler.add(MessageEvent, message=TextMessageContent)(handle_message)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

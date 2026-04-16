from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

from models import ReplyDecision
from sheets_client import (
    SheetsClientError,
    load_alias_rows,
    load_intent_keyword_rows,
    load_intent_routing_rows,
    load_intent_template_rows,
    load_price_table_item_rows,
    load_team_rows,
    load_template_rows,
)

logger = logging.getLogger(__name__)

TEAM_NOT_FOUND = "TMP-002"
NO_ITEMS = "TMP-004"
CONFIRM_REQUIRED = "TMP-003"
PRICE_LIST = "TMP-001"

INTENT_PRICE = "INT-PRICE"
INTENT_STOCK = "INT-STOCK"
INTENT_DELIVERY = "INT-DELIVERY"
INTENT_ORDER = "INT-ORDER"
INTENT_CHANGE = "INT-CHANGE"
INTENT_GREETING = "INT-GREETING"
INTENT_OTHER = "INT-OTHER"

TEAM_COLUMN_CANDIDATES: dict[str, tuple[str, ...]] = {
    "team_id": ("team_id", "チームID", "team id"),
    "team_name": ("team_name", "正式チーム名", "チーム名"),
    "status": ("status", "ステータス"),
    "price_table_id": ("price_table_id", "価格表ID", "price_table id"),
}

ALIAS_COLUMN_CANDIDATES: dict[str, tuple[str, ...]] = {
    "team_id": ("team_id", "チームID", "team id"),
    "alias_name": ("alias_name", "alias", "別名", "エイリアス名"),
}

ITEM_COLUMN_CANDIDATES: dict[str, tuple[str, ...]] = {
    "team_id": ("team_id", "チームID", "team id"),
    "reply_line": ("reply_line", "返信文言", "reply"),
    "auto_reply_target": ("自動応答対象", "auto_reply_target"),
    "confirm_status": ("確認ステータス", "confirm_status"),
}

TEMPLATE_COLUMN_CANDIDATES: dict[str, tuple[str, ...]] = {
    "template_id": ("template_id", "テンプレートID"),
    "template_text": ("template_text", "body_text", "本文", "テンプレ本文", "template"),
}

INTENT_KEYWORD_COLUMN_CANDIDATES: dict[str, tuple[str, ...]] = {
    "intent_id": ("intent_id", "intent id"),
    "keyword": ("keyword", "キーワード"),
    "priority": ("priority", "優先度"),
    "status": ("status", "ステータス"),
}

INTENT_TEMPLATE_COLUMN_CANDIDATES: dict[str, tuple[str, ...]] = {
    "intent_id": ("intent_id", "intent id"),
    "template_id": ("template_id", "テンプレートID"),
    "template_text": ("template_text", "本文", "template_text"),
    "status": ("status", "ステータス"),
}

INTENT_ROUTING_COLUMN_CANDIDATES: dict[str, tuple[str, ...]] = {
    "intent_id": ("intent_id", "intent id"),
    "auto_reply_enabled": ("auto_reply_enabled",),
    "queue_manual_reply": ("queue_manual_reply",),
    "requires_team_identification": ("requires_team_identification",),
    "status": ("status", "ステータス"),
}

INTENT_NAME_MAP: dict[str, str] = {
    INTENT_PRICE: "price_inquiry",
    INTENT_STOCK: "stock_inquiry",
    INTENT_DELIVERY: "delivery_inquiry",
    INTENT_ORDER: "order_request",
    INTENT_CHANGE: "change_request",
    INTENT_GREETING: "greeting",
    INTENT_OTHER: "other",
}

FALLBACK_INTENT_TEXT: dict[str, str] = {
    INTENT_STOCK: "【自動応答で返信しております。】在庫のお問い合わせありがとうございます。担当にて確認のうえご案内します。少々お待ちください。",
    INTENT_DELIVERY: "【自動応答で返信しております。】納期のお問い合わせありがとうございます。確認のうえ順次ご案内します。少々お待ちください。",
    INTENT_ORDER: "【自動応答で返信しております。】ご注文希望のご連絡ありがとうございます。内容を確認し、担当よりご案内します。少々お待ちください。",
    INTENT_CHANGE: "【自動応答で返信しております。】変更のご依頼ありがとうございます。内容を確認し、担当よりご案内します。少々お待ちください。",
    INTENT_GREETING: "お問い合わせありがとうございます。価格確認の場合はチーム名を添えてお送りください。その他のご用件も順次確認いたします。",
    INTENT_OTHER: "【自動応答で返信しております。】お問い合わせありがとうございます。内容を確認のうえ担当よりご案内します。少々お待ちください。",
}

PRICE_FALLBACK_KEYWORDS = (
    "tシャツ",
    "シャツ",
    "パーカー",
    "ジャージ",
    "ソックス",
)


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", str(text or ""))
    normalized = normalized.casefold()
    normalized = re.sub(r"\s+", "", normalized)
    return normalized.strip()


def _get_first_value(
    row: dict[str, Any],
    candidates: tuple[str, ...],
    *,
    required: bool = False,
    label: str,
) -> str:
    for candidate in candidates:
        for key, value in row.items():
            if normalize_text(key) == normalize_text(candidate):
                return str(value or "").strip()

    if required:
        available = ", ".join(row.keys()) if row else "(empty row)"
        raise ValueError(f"必要な列 '{label}' が見つかりません。利用可能な列: {available}")
    return ""


def _to_bool(value: str) -> bool:
    return normalize_text(value) in {"true", "1", "yes", "on", "有効", "対象"}


def find_team_id(message: str, aliases: list[dict[str, Any]]) -> str | None:
    normalized_message = normalize_text(message)
    matches: list[tuple[int, str]] = []

    for row in aliases:
        alias_name = _get_first_value(
            row,
            ALIAS_COLUMN_CANDIDATES["alias_name"],
            required=True,
            label="alias_name",
        )
        team_id = _get_first_value(
            row,
            ALIAS_COLUMN_CANDIDATES["team_id"],
            required=True,
            label="team_id",
        )
        normalized_alias = normalize_text(alias_name)
        if normalized_alias and normalized_alias in normalized_message:
            matches.append((len(normalized_alias), team_id))

    if not matches:
        return None

    matches.sort(key=lambda item: item[0], reverse=True)
    return matches[0][1]


def _find_team_id_from_text(text: str, teams: list[dict[str, Any]], aliases: list[dict[str, Any]]) -> str | None:
    normalized_text = normalize_text(text)
    if not normalized_text:
        return None
    return find_team_id(text, aliases) or _find_team_id_by_team_name(text, teams)


def _find_team_id_by_team_name(message: str, teams: list[dict[str, Any]]) -> str | None:
    normalized_message = normalize_text(message)
    matches: list[tuple[int, str]] = []

    for row in teams:
        team_id = _get_first_value(
            row,
            TEAM_COLUMN_CANDIDATES["team_id"],
            required=True,
            label="team_id",
        )
        team_name = _get_first_value(
            row,
            TEAM_COLUMN_CANDIDATES["team_name"],
            required=True,
            label="team_name",
        )
        normalized_team_name = normalize_text(team_name)
        if normalized_team_name and normalized_team_name in normalized_message:
            matches.append((len(normalized_team_name), team_id))

    if not matches:
        return None

    matches.sort(key=lambda item: item[0], reverse=True)
    return matches[0][1]


def get_team(team_id: str, teams: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in teams:
        current_team_id = _get_first_value(
            row,
            TEAM_COLUMN_CANDIDATES["team_id"],
            required=True,
            label="team_id",
        )
        if current_team_id == str(team_id).strip():
            return row
    return None


def get_price_items(team_id: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in items
        if _get_first_value(
            row,
            ITEM_COLUMN_CANDIDATES["team_id"],
            required=True,
            label="team_id",
        )
        == str(team_id).strip()
    ]


def choose_template_id(valid_items: list[dict[str, Any]], all_items: list[dict[str, Any]]) -> str:
    if not valid_items:
        return NO_ITEMS

    has_confirm_required = any(
        normalize_text(
            _get_first_value(
                row,
                ITEM_COLUMN_CANDIDATES["confirm_status"],
                label="confirm_status",
            )
        )
        == normalize_text("要確認")
        for row in all_items
    )
    if has_confirm_required:
        return CONFIRM_REQUIRED
    return PRICE_LIST


def render_reply(template_text: str, team_name: str, item_lines: str) -> str:
    return str(template_text or "").format(
        team_name=str(team_name or "").strip(),
        item_lines=str(item_lines or "").strip(),
    ).strip()


def _build_item_lines(valid_items: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for row in valid_items:
        raw_line = _get_first_value(
            row,
            ITEM_COLUMN_CANDIDATES["reply_line"],
            required=True,
            label="reply_line",
        )
        if not raw_line:
            continue
        lines.append(f"・{raw_line.lstrip('・').strip()}")
    return "\n".join(lines)


def _find_template_text(template_id: str, templates: list[dict[str, Any]]) -> str:
    for row in templates:
        current_template_id = _get_first_value(
            row,
            TEMPLATE_COLUMN_CANDIDATES["template_id"],
            required=True,
            label="template_id",
        )
        if current_template_id == template_id:
            return _get_first_value(
                row,
                TEMPLATE_COLUMN_CANDIDATES["template_text"],
                required=True,
                label="template_text",
            )
    raise ValueError(f"テンプレートID '{template_id}' が templates シートに見つかりません。")


def _get_team_name(team: dict[str, Any]) -> str:
    return _get_first_value(
        team,
        TEAM_COLUMN_CANDIDATES["team_name"],
        required=True,
        label="team_name",
    )


def _get_team_status(team: dict[str, Any]) -> str:
    return _get_first_value(
        team,
        TEAM_COLUMN_CANDIDATES["status"],
        required=True,
        label="status",
    )


def _is_active_team(team: dict[str, Any]) -> bool:
    return normalize_text(_get_team_status(team)) == normalize_text("有効")


def _build_valid_items(team_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        row
        for row in team_items
        if normalize_text(
            _get_first_value(
                row,
                ITEM_COLUMN_CANDIDATES["auto_reply_target"],
                label="auto_reply_target",
            )
        )
        == normalize_text("対象")
        and normalize_text(
            _get_first_value(
                row,
                ITEM_COLUMN_CANDIDATES["confirm_status"],
                label="confirm_status",
            )
        )
        == normalize_text("OK")
    ]


def detect_intent(message: str, intent_keywords: list[dict[str, Any]]) -> str:
    normalized_message = normalize_text(message)
    matched_rows: list[tuple[int, str]] = []

    for row in intent_keywords:
        status = _get_first_value(
            row,
            INTENT_KEYWORD_COLUMN_CANDIDATES["status"],
            label="status",
        )
        if status and normalize_text(status) != normalize_text("有効"):
            continue

        keyword = _get_first_value(
            row,
            INTENT_KEYWORD_COLUMN_CANDIDATES["keyword"],
            required=True,
            label="keyword",
        )
        normalized_keyword = normalize_text(keyword)
        if not normalized_keyword:
            continue
        if normalized_keyword in normalized_message:
            priority_text = _get_first_value(
                row,
                INTENT_KEYWORD_COLUMN_CANDIDATES["priority"],
                label="priority",
            )
            try:
                priority = int(priority_text or "0")
            except ValueError:
                priority = 0
            intent_id = _get_first_value(
                row,
                INTENT_KEYWORD_COLUMN_CANDIDATES["intent_id"],
                required=True,
                label="intent_id",
            )
            matched_rows.append((priority, intent_id))

    if matched_rows:
        matched_rows.sort(key=lambda item: item[0], reverse=True)
        return matched_rows[0][1]

    if any(token in normalized_message for token in PRICE_FALLBACK_KEYWORDS):
        return INTENT_PRICE

    return INTENT_OTHER


def get_intent_template(intent_id: str, templates: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in templates:
        status = _get_first_value(
            row,
            INTENT_TEMPLATE_COLUMN_CANDIDATES["status"],
            label="status",
        )
        if status and normalize_text(status) != normalize_text("有効"):
            continue
        current_intent_id = _get_first_value(
            row,
            INTENT_TEMPLATE_COLUMN_CANDIDATES["intent_id"],
            required=True,
            label="intent_id",
        )
        if current_intent_id == intent_id:
            return row
    return None


def get_intent_routing(intent_id: str, routings: list[dict[str, Any]]) -> dict[str, Any] | None:
    for row in routings:
        status = _get_first_value(
            row,
            INTENT_ROUTING_COLUMN_CANDIDATES["status"],
            label="status",
        )
        if status and normalize_text(status) != normalize_text("有効"):
            continue
        current_intent_id = _get_first_value(
            row,
            INTENT_ROUTING_COLUMN_CANDIDATES["intent_id"],
            required=True,
            label="intent_id",
        )
        if current_intent_id == intent_id:
            return row
    return None


def _build_non_price_reply_from_sheets(
    intent_id: str,
    team_name: str,
    intent_templates: list[dict[str, Any]],
) -> tuple[str, str]:
    template_row = get_intent_template(intent_id, intent_templates)
    if template_row:
        template_id = _get_first_value(
            template_row,
            INTENT_TEMPLATE_COLUMN_CANDIDATES["template_id"],
            required=True,
            label="template_id",
        )
        template_text = _get_first_value(
            template_row,
            INTENT_TEMPLATE_COLUMN_CANDIDATES["template_text"],
            required=True,
            label="template_text",
        )
        return render_reply(template_text, team_name, ""), template_id

    fallback_text = FALLBACK_INTENT_TEXT.get(intent_id, FALLBACK_INTENT_TEXT[INTENT_OTHER])
    logger.info("intent template not found. fallback to built-in template: %s", intent_id)
    return fallback_text, intent_id


def _resolve_team_context(
    message: str,
    teams: list[dict[str, Any]],
    aliases: list[dict[str, Any]],
    *,
    sender_name: str = "",
    sender_tag: str = "",
) -> tuple[str | None, dict[str, Any] | None]:
    candidate_texts = (
        sender_name,
        sender_tag,
        message,
    )
    team_id = None
    for text in candidate_texts:
        team_id = _find_team_id_from_text(text, teams, aliases)
        if team_id:
            break
    team = get_team(team_id, teams) if team_id else None
    return team_id, team


def generate_reply(
    message: str,
    *,
    sender_name: str = "",
    sender_tag: str = "",
) -> str:
    return generate_reply_decision(
        message,
        sender_name=sender_name,
        sender_tag=sender_tag,
    ).reply_text


def generate_reply_decision(
    message: str,
    *,
    sender_name: str = "",
    sender_tag: str = "",
) -> ReplyDecision:
    try:
        teams = load_team_rows()
        aliases = load_alias_rows()
        items = load_price_table_item_rows()
        templates = load_template_rows()
        intent_keywords = load_intent_keyword_rows()
        intent_templates = load_intent_template_rows()
        intent_routings = load_intent_routing_rows()

        intent_id = detect_intent(message, intent_keywords)
        team_id, team = _resolve_team_context(
            message,
            teams,
            aliases,
            sender_name=sender_name,
            sender_tag=sender_tag,
        )
        team_name = _get_team_name(team) if team else ""
        routing = get_intent_routing(intent_id, intent_routings)

        if intent_id != INTENT_PRICE:
            reply_text, template_id = _build_non_price_reply_from_sheets(
                intent_id,
                team_name,
                intent_templates,
            )
            manual_required = True
            if routing is not None:
                queue_manual_reply = _get_first_value(
                    routing,
                    INTENT_ROUTING_COLUMN_CANDIDATES["queue_manual_reply"],
                    label="queue_manual_reply",
                )
                manual_required = _to_bool(queue_manual_reply)
            return ReplyDecision(
                reply_text=reply_text,
                team_id=team_id,
                team_name=team_name,
                template_id=template_id,
                intent=INTENT_NAME_MAP.get(intent_id, "other"),
                manual_required=manual_required,
                reason=INTENT_NAME_MAP.get(intent_id, "other"),
            )

        if not team_id:
            return ReplyDecision(
                reply_text=render_reply(_find_template_text(TEAM_NOT_FOUND, templates), "", ""),
                team_id=None,
                team_name="",
                template_id=TEAM_NOT_FOUND,
                intent=INTENT_NAME_MAP[INTENT_PRICE],
                manual_required=True,
                reason="team_not_found",
            )

        if not team or not _is_active_team(team):
            logger.info("team_id=%s is not available", team_id)
            return ReplyDecision(
                reply_text=render_reply(_find_template_text(TEAM_NOT_FOUND, templates), "", ""),
                team_id=team_id,
                team_name=team_name,
                template_id=TEAM_NOT_FOUND,
                intent=INTENT_NAME_MAP[INTENT_PRICE],
                manual_required=True,
                reason="team_inactive",
            )

        team_items = get_price_items(team_id, items)
        valid_items = _build_valid_items(team_items)
        template_id = choose_template_id(valid_items, team_items)
        template_text = _find_template_text(template_id, templates)
        item_lines = _build_item_lines(valid_items)
        manual_required = template_id in {TEAM_NOT_FOUND, NO_ITEMS}
        reason = {
            PRICE_LIST: "auto_price_list",
            CONFIRM_REQUIRED: "confirm_required",
            NO_ITEMS: "no_items",
            TEAM_NOT_FOUND: "team_not_found",
        }.get(template_id, "unknown")

        return ReplyDecision(
            reply_text=render_reply(template_text, team_name, item_lines),
            team_id=team_id,
            team_name=team_name,
            template_id=template_id,
            intent=INTENT_NAME_MAP[INTENT_PRICE],
            manual_required=manual_required,
            reason=reason,
        )
    except SheetsClientError:
        raise
    except Exception as exc:
        logger.exception("Failed to generate reply")
        raise RuntimeError(f"返信文の生成に失敗しました: {exc}") from exc

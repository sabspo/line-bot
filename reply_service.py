from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

from models import ReplyDecision
from sheets_client import (
    SheetsClientError,
    load_alias_rows,
    load_price_table_item_rows,
    load_team_rows,
    load_template_rows,
)

logger = logging.getLogger(__name__)

TEAM_NOT_FOUND = "TMP-002"
NO_ITEMS = "TMP-004"
CONFIRM_REQUIRED = "TMP-003"
PRICE_LIST = "TMP-001"

TEAM_COLUMN_CANDIDATES: dict[str, tuple[str, ...]] = {
    "team_id": ("team_id", "チームid", "チームID"),
    "team_name": ("team_name", "正式チーム名", "チーム名"),
    "status": ("status", "ステータス"),
    "price_table_id": ("price_table_id", "価格表id", "価格表ID"),
}

ALIAS_COLUMN_CANDIDATES: dict[str, tuple[str, ...]] = {
    "team_id": ("team_id", "チームid", "チームID"),
    "alias_name": ("alias_name", "alias", "別名", "エイリアス名"),
}

ITEM_COLUMN_CANDIDATES: dict[str, tuple[str, ...]] = {
    "team_id": ("team_id", "チームid", "チームID"),
    "reply_line": ("reply_line", "返信文言", "reply", "商品返信文"),
    "auto_reply_target": ("自動応答対象", "auto_reply_target"),
    "confirm_status": ("確認ステータス", "confirm_status"),
}

TEMPLATE_COLUMN_CANDIDATES: dict[str, tuple[str, ...]] = {
    "template_id": ("template_id", "テンプレートid", "テンプレートID"),
    "template_text": ("template_text", "body_text", "本文", "テンプレ本文", "template"),
}


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
        raise ValueError(f"必要な列 '{label}' が見つかりません。利用可能列: {available}")
    return ""


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


def _find_team_id_by_team_name(message: str, teams: list[dict[str, Any]]) -> str | None:
    """aliases に正式名が未登録でも、team 名で拾えるようにする。"""
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
        _get_first_value(
            row,
            ITEM_COLUMN_CANDIDATES["confirm_status"],
            label="confirm_status",
        )
        == "要確認"
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


def generate_reply(message: str) -> str:
    return generate_reply_decision(message).reply_text


def generate_reply_decision(message: str) -> ReplyDecision:
    try:
        teams = load_team_rows()
        aliases = load_alias_rows()
        items = load_price_table_item_rows()
        templates = load_template_rows()

        team_id = find_team_id(message, aliases) or _find_team_id_by_team_name(message, teams)
        if not team_id:
            return ReplyDecision(
                reply_text=render_reply(_find_template_text(TEAM_NOT_FOUND, templates), "", ""),
                team_id=None,
                team_name="",
                template_id=TEAM_NOT_FOUND,
                manual_required=True,
                reason="team_not_found",
            )

        team = get_team(team_id, teams)
        if not team or not _is_active_team(team):
            logger.info("team_id=%s is not available", team_id)
            team_name = _get_team_name(team) if team else ""
            return ReplyDecision(
                reply_text=render_reply(_find_template_text(TEAM_NOT_FOUND, templates), "", ""),
                team_id=team_id,
                team_name=team_name,
                template_id=TEAM_NOT_FOUND,
                manual_required=True,
                reason="team_inactive",
            )

        team_items = get_price_items(team_id, items)
        valid_items = _build_valid_items(team_items)

        template_id = choose_template_id(valid_items, team_items)
        template_text = _find_template_text(template_id, templates)
        team_name = _get_team_name(team)
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
            manual_required=manual_required,
            reason=reason,
        )
    except SheetsClientError:
        raise
    except Exception as exc:
        logger.exception("Failed to generate reply")
        raise RuntimeError(f"返信文の生成に失敗しました: {exc}") from exc

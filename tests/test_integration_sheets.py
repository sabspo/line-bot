from __future__ import annotations

import os
from pathlib import Path

import pytest

import reply_service
from reply_service import (
    _build_valid_items,
    _find_team_id_by_team_name,
    find_team_id,
    generate_reply,
    get_price_items,
    get_team,
)
from sheets_client import SheetsClientError
from sheets_client import (
    load_alias_rows,
    load_intent_keyword_rows,
    load_intent_routing_rows,
    load_intent_template_rows,
    load_price_table_item_rows,
    load_team_rows,
    load_template_rows,
    load_test_case_rows,
)


def _service_account_is_configured() -> bool:
    configured_path = os.environ.get("SERVICE_ACCOUNT_FILE")
    if configured_path:
        return Path(configured_path).exists()
    return Path("service_account.json").exists()


pytestmark = pytest.mark.skipif(
    not _service_account_is_configured(),
    reason="SERVICE_ACCOUNT_FILE または service_account.json が未設定のため、実シート統合テストをスキップします。",
)


def _first_value(row: dict[str, str], *candidates: str) -> str:
    normalized = {str(key).strip().casefold(): str(value or "").strip() for key, value in row.items()}
    for candidate in candidates:
        if candidate.casefold() in normalized:
            return normalized[candidate.casefold()]
    return ""


def _collect_runnable_test_cases(rows: list[dict[str, str]]) -> list[tuple[str, str, str, str, str, str]]:
    cases: list[tuple[str, str, str, str, str, str]] = []
    for row in rows:
        case_id = _first_value(row, "test_id", "case_id", "test_case_id")
        status = _first_value(row, "status", "test_status")
        message = _first_value(row, "message", "input_message", "user_message", "メッセージ")
        expected_team_id = _first_value(row, "expected_team_id")
        expected_team_name = _first_value(row, "expected_team_name")
        expected_template_id = _first_value(row, "expected_template_id")
        expected_items_count = _first_value(row, "expected_items_count")

        if not message or not expected_template_id:
            continue
        if status.casefold() in {"pending", "draft", "todo", "保留", "未確認"}:
            continue

        cases.append(
            (
                case_id or message[:30],
                message,
                expected_team_id,
                expected_team_name,
                expected_template_id,
                expected_items_count,
            )
        )
    return cases


def _load_test_cases_or_skip() -> list[tuple[str, str, str, str, str, str]]:
    try:
        return _collect_runnable_test_cases(load_test_case_rows())
    except SheetsClientError as exc:
        pytest.skip(f"実シート test_cases を読み込めませんでした: {exc}")


def test_sheet_loading_smoke() -> None:
    try:
        teams = load_team_rows()
        aliases = load_alias_rows()
        items = load_price_table_item_rows()
        templates = load_template_rows()
        intent_keywords = load_intent_keyword_rows()
        intent_templates = load_intent_template_rows()
        intent_routing = load_intent_routing_rows()
    except SheetsClientError as exc:
        pytest.skip(f"実シートにアクセスできませんでした: {exc}")

    assert teams, "team シートが空です。"
    assert aliases is not None
    assert items is not None
    assert templates, "templates シートが空です。"
    assert intent_keywords, "intent_keywords シートが空です。"
    assert intent_templates, "intent_templates シートが空です。"
    assert intent_routing, "intent_routing シートが空です。"


def test_sheet_has_required_templates() -> None:
    try:
        templates = load_template_rows()
    except SheetsClientError as exc:
        pytest.skip(f"templates シートにアクセスできませんでした: {exc}")

    template_ids = {
        _first_value(row, "template_id", "テンプレートID")
        for row in templates
    }
    assert {"TMP-001", "TMP-002", "TMP-003", "TMP-004"}.issubset(template_ids)


def test_sheet_has_required_intent_templates() -> None:
    try:
        templates = load_intent_template_rows()
    except SheetsClientError as exc:
        pytest.skip(f"intent_templates シートにアクセスできませんでした: {exc}")

    intent_ids = {_first_value(row, "intent_id") for row in templates}
    assert {"INT-STOCK", "INT-DELIVERY", "INT-ORDER", "INT-CHANGE", "INT-GREETING", "INT-OTHER"}.issubset(intent_ids)


def test_generate_reply_against_test_cases() -> None:
    cases = _load_test_cases_or_skip()
    if not cases:
        pytest.skip("実行可能な test_cases 行がありません。status を確認してください。")

    teams = load_team_rows()
    aliases = load_alias_rows()
    items = load_price_table_item_rows()
    templates = load_template_rows()
    intent_keywords = load_intent_keyword_rows()
    intent_templates = load_intent_template_rows()
    intent_routing = load_intent_routing_rows()

    reply_service.load_team_rows = lambda: teams
    reply_service.load_alias_rows = lambda: aliases
    reply_service.load_price_table_item_rows = lambda: items
    reply_service.load_template_rows = lambda: templates
    reply_service.load_intent_keyword_rows = lambda: intent_keywords
    reply_service.load_intent_template_rows = lambda: intent_templates
    reply_service.load_intent_routing_rows = lambda: intent_routing

    for case_id, message, expected_team_id, expected_team_name, expected_template_id, expected_items_count in cases:
        decision = reply_service.generate_reply_decision(message)
        reply = generate_reply(message)
        team_id = find_team_id(message, aliases) or _find_team_id_by_team_name(message, teams)
        team = get_team(team_id, teams) if team_id else None
        team_items = get_price_items(team_id, items) if team_id else []
        valid_items = _build_valid_items(team_items)

        assert decision.template_id == expected_template_id, (
            f"{case_id}: template mismatch. expected={expected_template_id}, actual={decision.template_id}, reply={reply}"
        )
        if expected_team_id:
            assert (team_id or "") == expected_team_id, (
                f"{case_id}: team_id mismatch. expected={expected_team_id}, actual={team_id}"
            )
        if expected_team_name:
            assert expected_team_name in reply or (team and expected_team_name in str(team)), (
                f"{case_id}: expected team name not found in reply. reply={reply}"
            )
        if expected_items_count and decision.template_id in {reply_service.PRICE_LIST, reply_service.CONFIRM_REQUIRED}:
            assert len(valid_items) == int(expected_items_count), (
                f"{case_id}: item count mismatch. expected={expected_items_count}, actual={len(valid_items)}"
            )

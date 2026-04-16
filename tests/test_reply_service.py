from __future__ import annotations

import reply_service


def _templates() -> list[dict[str, str]]:
    return [
        {"template_id": "TMP-001", "template_text": "{team_name} の価格一覧です。\n{item_lines}"},
        {"template_id": "TMP-002", "template_text": "チーム名が確認できませんでした。別の言い方でもう一度チーム名を送ってください。"},
        {"template_id": "TMP-003", "template_text": "{team_name} の価格一覧です。要確認の商品を除いてご案内します。\n{item_lines}"},
        {"template_id": "TMP-004", "template_text": "{team_name} は現在ご案内できる商品がありません。"},
    ]


def _intent_templates() -> list[dict[str, str]]:
    return [
        {
            "template_id": "ITM-001",
            "intent_id": "INT-STOCK",
            "template_text": "【自動応答で返信しております。】在庫のお問い合わせありがとうございます。担当にて確認のうえご案内します。少々お待ちください。",
            "status": "有効",
        },
        {
            "template_id": "ITM-002",
            "intent_id": "INT-DELIVERY",
            "template_text": "【自動応答で返信しております。】納期のお問い合わせありがとうございます。確認のうえ順次ご案内します。少々お待ちください。",
            "status": "有効",
        },
        {
            "template_id": "ITM-003",
            "intent_id": "INT-ORDER",
            "template_text": "【自動応答で返信しております。】ご注文希望のご連絡ありがとうございます。内容を確認し、担当よりご案内します。少々お待ちください。",
            "status": "有効",
        },
        {
            "template_id": "ITM-004",
            "intent_id": "INT-CHANGE",
            "template_text": "【自動応答で返信しております。】変更のご依頼ありがとうございます。内容を確認し、担当よりご案内します。少々お待ちください。",
            "status": "有効",
        },
        {
            "template_id": "ITM-005",
            "intent_id": "INT-GREETING",
            "template_text": "お問い合わせありがとうございます。価格確認の場合はチーム名を添えてお送りください。",
            "status": "有効",
        },
        {
            "template_id": "ITM-006",
            "intent_id": "INT-OTHER",
            "template_text": "【自動応答で返信しております。】お問い合わせありがとうございます。内容を確認のうえ担当よりご案内します。少々お待ちください。",
            "status": "有効",
        },
    ]


def _intent_routing() -> list[dict[str, str]]:
    return [
        {"intent_id": "INT-PRICE", "queue_manual_reply": "FALSE", "status": "有効"},
        {"intent_id": "INT-STOCK", "queue_manual_reply": "TRUE", "status": "有効"},
        {"intent_id": "INT-DELIVERY", "queue_manual_reply": "TRUE", "status": "有効"},
        {"intent_id": "INT-ORDER", "queue_manual_reply": "TRUE", "status": "有効"},
        {"intent_id": "INT-CHANGE", "queue_manual_reply": "TRUE", "status": "有効"},
        {"intent_id": "INT-GREETING", "queue_manual_reply": "FALSE", "status": "有効"},
        {"intent_id": "INT-OTHER", "queue_manual_reply": "TRUE", "status": "有効"},
    ]


def _intent_keywords() -> list[dict[str, str]]:
    return [
        {"intent_id": "INT-PRICE", "keyword": "価格", "priority": "100", "status": "有効"},
        {"intent_id": "INT-PRICE", "keyword": "値段", "priority": "100", "status": "有効"},
        {"intent_id": "INT-PRICE", "keyword": "いくら", "priority": "100", "status": "有効"},
        {"intent_id": "INT-STOCK", "keyword": "在庫", "priority": "90", "status": "有効"},
        {"intent_id": "INT-DELIVERY", "keyword": "納期", "priority": "90", "status": "有効"},
        {"intent_id": "INT-DELIVERY", "keyword": "いつ届", "priority": "100", "status": "有効"},
        {"intent_id": "INT-ORDER", "keyword": "注文", "priority": "90", "status": "有効"},
        {"intent_id": "INT-CHANGE", "keyword": "変更", "priority": "90", "status": "有効"},
        {"intent_id": "INT-GREETING", "keyword": "こんにちは", "priority": "20", "status": "有効"},
    ]


def _teams() -> list[dict[str, str]]:
    return [
        {
            "team_id": "TEAM-001",
            "team_name": "つくしヤングラガーズ小学部",
            "status": "有効",
            "price_table_id": "PT-001",
        },
        {
            "team_id": "TEAM-002",
            "team_name": "みどりラグビークラブ",
            "status": "有効",
            "price_table_id": "PT-002",
        },
    ]


def _aliases() -> list[dict[str, str]]:
    return [
        {"team_id": "TEAM-001", "alias_name": "つくしヤングラガーズ小学部"},
        {"team_id": "TEAM-001", "alias_name": "つくしヤング"},
        {"team_id": "TEAM-002", "alias_name": "みどりラグビー"},
    ]


def _items() -> list[dict[str, str]]:
    return [
        {
            "team_id": "TEAM-001",
            "reply_line": "チームTシャツ：税込3,170円",
            "自動応答対象": "対象",
            "確認ステータス": "OK",
        },
        {
            "team_id": "TEAM-001",
            "reply_line": "チームソックス：税込1,470円",
            "自動応答対象": "対象",
            "確認ステータス": "OK",
        },
        {
            "team_id": "TEAM-001",
            "reply_line": "ラグビージャージ：税込10,000円",
            "自動応答対象": "対象",
            "確認ステータス": "要確認",
        },
    ]


def _patch_data(
    monkeypatch,
    *,
    teams: list[dict[str, str]] | None = None,
    aliases: list[dict[str, str]] | None = None,
    items: list[dict[str, str]] | None = None,
    templates: list[dict[str, str]] | None = None,
    intent_keywords: list[dict[str, str]] | None = None,
    intent_templates: list[dict[str, str]] | None = None,
    intent_routing: list[dict[str, str]] | None = None,
) -> None:
    monkeypatch.setattr(reply_service, "load_team_rows", lambda: teams if teams is not None else _teams())
    monkeypatch.setattr(reply_service, "load_alias_rows", lambda: aliases if aliases is not None else _aliases())
    monkeypatch.setattr(
        reply_service,
        "load_price_table_item_rows",
        lambda: items if items is not None else _items(),
    )
    monkeypatch.setattr(
        reply_service,
        "load_template_rows",
        lambda: templates if templates is not None else _templates(),
    )
    monkeypatch.setattr(
        reply_service,
        "load_intent_keyword_rows",
        lambda: intent_keywords if intent_keywords is not None else _intent_keywords(),
    )
    monkeypatch.setattr(
        reply_service,
        "load_intent_template_rows",
        lambda: intent_templates if intent_templates is not None else _intent_templates(),
    )
    monkeypatch.setattr(
        reply_service,
        "load_intent_routing_rows",
        lambda: intent_routing if intent_routing is not None else _intent_routing(),
    )


def test_generate_reply_returns_price_list_for_formal_team_name(monkeypatch) -> None:
    _patch_data(
        monkeypatch,
        items=[
            {
                "team_id": "TEAM-001",
                "reply_line": "チームTシャツ：税込3,170円",
                "自動応答対象": "対象",
                "確認ステータス": "OK",
            }
        ],
    )

    reply = reply_service.generate_reply("つくしヤングラガーズ小学部です。商品の価格を教えてください。")

    assert "つくしヤングラガーズ小学部 の価格一覧です。" in reply
    assert "・チームTシャツ：税込3,170円" in reply


def test_generate_reply_returns_price_list_for_alias(monkeypatch) -> None:
    _patch_data(
        monkeypatch,
        items=[
            {
                "team_id": "TEAM-001",
                "reply_line": "チームソックス：税込1,470円",
                "自動応答対象": "対象",
                "確認ステータス": "OK",
            }
        ],
    )

    reply = reply_service.generate_reply("つくしヤングです。価格を教えてください。")

    assert "つくしヤングラガーズ小学部" in reply
    assert "・チームソックス：税込1,470円" in reply


def test_generate_reply_returns_team_not_found(monkeypatch) -> None:
    _patch_data(monkeypatch)

    reply = reply_service.generate_reply("未登録チームです。価格を教えてください。")

    assert reply == "チーム名が確認できませんでした。別の言い方でもう一度チーム名を送ってください。"


def test_generate_reply_returns_confirm_required(monkeypatch) -> None:
    _patch_data(monkeypatch)

    reply = reply_service.generate_reply("つくしヤングラガーズ小学部の価格を知りたいです。")

    assert "要確認の商品を除いてご案内します。" in reply
    assert "・チームTシャツ：税込3,170円" in reply
    assert "・チームソックス：税込1,470円" in reply
    assert "ラグビージャージ" not in reply


def test_generate_reply_returns_no_items(monkeypatch) -> None:
    _patch_data(monkeypatch, items=[])

    reply = reply_service.generate_reply("つくしヤングラガーズ小学部の価格を教えてください。")

    assert reply == "つくしヤングラガーズ小学部 は現在ご案内できる商品がありません。"


def test_find_team_id_prefers_longest_alias(monkeypatch) -> None:
    _patch_data(
        monkeypatch,
        aliases=[
            {"team_id": "TEAM-001", "alias_name": "つくし"},
            {"team_id": "TEAM-002", "alias_name": "つくしヤング"},
        ],
        teams=[
            {"team_id": "TEAM-001", "team_name": "つくしクラブ", "status": "有効", "price_table_id": "PT-001"},
            {"team_id": "TEAM-002", "team_name": "つくしヤングラガーズ小学部", "status": "有効", "price_table_id": "PT-002"},
        ],
        items=[
            {
                "team_id": "TEAM-002",
                "reply_line": "チームパンツ：税込2,000円",
                "自動応答対象": "対象",
                "確認ステータス": "OK",
            }
        ],
    )

    reply = reply_service.generate_reply("つくしヤングの価格を教えてください。")

    assert "つくしヤングラガーズ小学部" in reply
    assert "・チームパンツ：税込2,000円" in reply


def test_generate_reply_normalizes_spaces_and_fullwidth_characters(monkeypatch) -> None:
    _patch_data(
        monkeypatch,
        aliases=[{"team_id": "TEAM-001", "alias_name": "つくしヤング"}],
        items=[
            {
                "team_id": "TEAM-001",
                "reply_line": "チームTシャツ：税込3,170円",
                "自動応答対象": "対象",
                "確認ステータス": "OK",
            }
        ],
    )

    reply = reply_service.generate_reply("  つ く し　ヤ ン グ です。 価格を教えて  ")

    assert reply.count("・") == 1
    assert "・チームTシャツ：税込3,170円" in reply


def test_generate_reply_returns_team_not_found_for_inactive_team(monkeypatch) -> None:
    _patch_data(
        monkeypatch,
        teams=[
            {
                "team_id": "TEAM-001",
                "team_name": "つくしヤングラガーズ小学部",
                "status": "無効",
                "price_table_id": "PT-001",
            }
        ],
    )

    reply = reply_service.generate_reply("つくしヤングラガーズ小学部の価格を教えてください。")

    assert reply == "チーム名が確認できませんでした。別の言い方でもう一度チーム名を送ってください。"


def test_generate_reply_ignores_non_target_items(monkeypatch) -> None:
    _patch_data(
        monkeypatch,
        items=[
            {
                "team_id": "TEAM-001",
                "reply_line": "チームTシャツ：税込3,170円",
                "自動応答対象": "対象",
                "確認ステータス": "OK",
            },
            {
                "team_id": "TEAM-001",
                "reply_line": "社内メモ商品：税込999円",
                "自動応答対象": "対象外",
                "確認ステータス": "OK",
            },
        ],
    )

    reply = reply_service.generate_reply("つくしヤングラガーズ小学部の価格を教えてください。")

    assert "・チームTシャツ：税込3,170円" in reply
    assert "社内メモ商品" not in reply


def test_generate_reply_falls_back_to_team_name_when_alias_is_missing(monkeypatch) -> None:
    _patch_data(
        monkeypatch,
        aliases=[],
        items=[
            {
                "team_id": "TEAM-001",
                "reply_line": "チームソックス：税込1,470円",
                "自動応答対象": "対象",
                "確認ステータス": "OK",
            }
        ],
    )

    reply = reply_service.generate_reply("つくしヤングラガーズ小学部です。価格を教えてください。")

    assert "つくしヤングラガーズ小学部 の価格一覧です。" in reply
    assert "・チームソックス：税込1,470円" in reply


def test_generate_reply_decision_marks_team_not_found_for_manual_reply(monkeypatch) -> None:
    _patch_data(monkeypatch)

    decision = reply_service.generate_reply_decision("未登録チームです。価格を教えてください。")

    assert decision.template_id == "TMP-002"
    assert decision.intent == "price_inquiry"
    assert decision.manual_required is True
    assert decision.reason == "team_not_found"


def test_generate_reply_decision_marks_no_items_for_manual_reply(monkeypatch) -> None:
    _patch_data(monkeypatch, items=[])

    decision = reply_service.generate_reply_decision("つくしヤングラガーズ小学部の価格を教えてください。")

    assert decision.template_id == "TMP-004"
    assert decision.intent == "price_inquiry"
    assert decision.manual_required is True
    assert decision.reason == "no_items"


def test_generate_reply_decision_keeps_confirm_required_as_auto_reply(monkeypatch) -> None:
    _patch_data(monkeypatch)

    decision = reply_service.generate_reply_decision("つくしヤングラガーズ小学部の価格を知りたいです。")

    assert decision.template_id == "TMP-003"
    assert decision.intent == "price_inquiry"
    assert decision.manual_required is False


def test_detect_intent_returns_stock_inquiry() -> None:
    assert reply_service.detect_intent("在庫はありますか？", _intent_keywords()) == "INT-STOCK"


def test_detect_intent_returns_delivery_inquiry() -> None:
    assert reply_service.detect_intent("納期はいつ頃ですか？", _intent_keywords()) == "INT-DELIVERY"


def test_detect_intent_returns_order_request() -> None:
    assert reply_service.detect_intent("注文したいです", _intent_keywords()) == "INT-ORDER"


def test_generate_reply_decision_for_non_price_inquiry_requires_manual_reply(monkeypatch) -> None:
    _patch_data(monkeypatch)

    decision = reply_service.generate_reply_decision("つくしヤングラガーズ小学部の在庫はありますか？")

    assert decision.intent == "stock_inquiry"
    assert decision.template_id == "ITM-001"
    assert decision.manual_required is True
    assert decision.reason == "stock_inquiry"
    assert "在庫のお問い合わせありがとうございます" in decision.reply_text


def test_generate_reply_decision_for_greeting_is_auto_reply(monkeypatch) -> None:
    _patch_data(monkeypatch)

    decision = reply_service.generate_reply_decision("こんにちは")

    assert decision.intent == "greeting"
    assert decision.template_id == "ITM-005"
    assert decision.manual_required is False
    assert "お問い合わせありがとうございます" in decision.reply_text


def test_generate_reply_decision_uses_fallback_when_intent_template_missing(monkeypatch) -> None:
    templates = [row for row in _intent_templates() if row["intent_id"] != "INT-STOCK"]
    _patch_data(monkeypatch, intent_templates=templates)

    decision = reply_service.generate_reply_decision("つくしヤングラガーズ小学部の在庫はありますか？")

    assert decision.intent == "stock_inquiry"
    assert decision.template_id == "INT-STOCK"
    assert "在庫のお問い合わせありがとうございます" in decision.reply_text

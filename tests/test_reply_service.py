from __future__ import annotations

import reply_service


def _templates() -> list[dict[str, str]]:
    return [
        {
            "template_id": "TMP-001",
            "template_text": "{team_name} の価格一覧です。\n{item_lines}",
        },
        {
            "template_id": "TMP-002",
            "template_text": "チームを特定できませんでした。チーム名をご確認ください。",
        },
        {
            "template_id": "TMP-003",
            "template_text": "{team_name} の価格一覧です。未確認の商品が含まれるため、確定分のみご案内します。\n{item_lines}",
        },
        {
            "template_id": "TMP-004",
            "template_text": "{team_name} は現在ご案内できる商品がありません。",
        },
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
            "reply_line": "追加ジャージ：税込10,000円",
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

    reply = reply_service.generate_reply("つくしヤングです。価格表をお願いします。")

    assert "つくしヤングラガーズ小学部" in reply
    assert "・チームソックス：税込1,470円" in reply


def test_generate_reply_returns_team_not_found(monkeypatch) -> None:
    _patch_data(monkeypatch)

    reply = reply_service.generate_reply("未登録チームです。価格を教えてください。")

    assert reply == "チームを特定できませんでした。チーム名をご確認ください。"


def test_generate_reply_returns_confirm_required(monkeypatch) -> None:
    _patch_data(monkeypatch)

    reply = reply_service.generate_reply("つくしヤングラガーズ小学部の価格を知りたいです。")

    assert "未確認の商品が含まれるため、確定分のみご案内します。" in reply
    assert "・チームTシャツ：税込3,170円" in reply
    assert "・チームソックス：税込1,470円" in reply
    assert "追加ジャージ" not in reply


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
                "reply_line": "・チームTシャツ：税込3,170円",
                "自動応答対象": "対象",
                "確認ステータス": "OK",
            }
        ],
    )

    reply = reply_service.generate_reply("  つ く し　ヤ ン グ です。  価格を教えて  ")

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

    assert reply == "チームを特定できませんでした。チーム名をご確認ください。"


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
                "reply_line": "裏メニュー商品：税込999円",
                "自動応答対象": "対象外",
                "確認ステータス": "OK",
            },
        ],
    )

    reply = reply_service.generate_reply("つくしヤングラガーズ小学部の価格を教えてください。")

    assert "・チームTシャツ：税込3,170円" in reply
    assert "裏メニュー商品" not in reply


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
    assert decision.manual_required is True
    assert decision.reason == "team_not_found"


def test_generate_reply_decision_marks_no_items_for_manual_reply(monkeypatch) -> None:
    _patch_data(monkeypatch, items=[])

    decision = reply_service.generate_reply_decision("つくしヤングラガーズ小学部の価格を教えてください。")

    assert decision.template_id == "TMP-004"
    assert decision.manual_required is True
    assert decision.reason == "no_items"


def test_generate_reply_decision_keeps_confirm_required_as_auto_reply(monkeypatch) -> None:
    _patch_data(monkeypatch)

    decision = reply_service.generate_reply_decision("つくしヤングラガーズ小学部の価格を知りたいです。")

    assert decision.template_id == "TMP-003"
    assert decision.manual_required is False

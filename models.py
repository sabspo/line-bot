from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Team:
    team_id: str
    team_name: str
    price_table_id: str
    status: str


@dataclass(slots=True)
class Alias:
    alias_name: str
    team_id: str


@dataclass(slots=True)
class PriceTableItem:
    team_id: str
    reply_line: str
    auto_reply_target: str
    confirm_status: str


@dataclass(slots=True)
class Template:
    template_id: str
    template_name: str
    template_text: str


@dataclass(slots=True)
class ReplyDecision:
    reply_text: str
    team_id: str | None
    team_name: str
    template_id: str
    manual_required: bool
    reason: str

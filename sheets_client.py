from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import gspread
from google.auth.exceptions import GoogleAuthError

from config import SERVICE_ACCOUNT_FILE, SERVICE_ACCOUNT_JSON, SHEET_NAMES, SPREADSHEET_URL

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


class SheetsClientError(RuntimeError):
    """Google Sheets 読み込み失敗を表す例外。"""


def _build_client(service_account_file: str = SERVICE_ACCOUNT_FILE) -> gspread.Client:
    try:
        if SERVICE_ACCOUNT_JSON:
            return gspread.service_account_from_dict(
                json.loads(SERVICE_ACCOUNT_JSON),
                scopes=SCOPES,
            )

        account_path = Path(service_account_file)
        if not account_path.exists():
            raise SheetsClientError(
                "サービスアカウントJSONが見つかりません。"
                f" SERVICE_ACCOUNT_FILE={account_path}"
            )

        return gspread.service_account(filename=str(account_path), scopes=SCOPES)
    except json.JSONDecodeError as exc:
        raise SheetsClientError("SERVICE_ACCOUNT_JSON の JSON 解析に失敗しました。") from exc
    except (OSError, GoogleAuthError, Exception) as exc:
        raise SheetsClientError(
            f"サービスアカウント認証に失敗しました: {exc}"
        ) from exc


def _open_worksheet(sheet_name: str) -> gspread.Worksheet:
    try:
        client = _build_client()
        spreadsheet = client.open_by_url(SPREADSHEET_URL)
        return spreadsheet.worksheet(sheet_name)
    except SheetsClientError:
        raise
    except gspread.WorksheetNotFound as exc:
        raise SheetsClientError(
            f"シート '{sheet_name}' が見つかりません。SHEET_NAMES を確認してください。"
        ) from exc
    except Exception as exc:
        raise SheetsClientError(
            f"スプレッドシートのオープンに失敗しました: {exc}"
        ) from exc


def _normalize_header(header: str) -> str:
    return str(header or "").strip()


def _clean_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        _normalize_header(key): str(value).strip()
        for key, value in row.items()
        if _normalize_header(key)
    }


def _load_sheet_rows(sheet_name: str) -> list[dict[str, str]]:
    worksheet = _open_worksheet(sheet_name)

    try:
        rows = worksheet.get_all_records(default_blank="")
    except Exception as exc:
        raise SheetsClientError(
            f"シート '{sheet_name}' の読み込みに失敗しました: {exc}"
        ) from exc

    cleaned_rows = [_clean_row(row) for row in rows]
    logger.info("Loaded %s rows from sheet '%s'", len(cleaned_rows), sheet_name)
    return cleaned_rows


def load_team_rows() -> list[dict[str, str]]:
    return _load_sheet_rows(SHEET_NAMES["teams"])


def load_alias_rows() -> list[dict[str, str]]:
    return _load_sheet_rows(SHEET_NAMES["aliases"])


def load_price_table_item_rows() -> list[dict[str, str]]:
    return _load_sheet_rows(SHEET_NAMES["price_table_items"])


def load_template_rows() -> list[dict[str, str]]:
    return _load_sheet_rows(SHEET_NAMES["templates"])


def load_test_case_rows() -> list[dict[str, str]]:
    return _load_sheet_rows(SHEET_NAMES["test_cases"])

from __future__ import annotations

import os
from pathlib import Path

SPREADSHEET_URL = os.environ.get(
    "SPREADSHEET_URL",
    "https://docs.google.com/spreadsheets/d/1-oLYHthSg4pawoW5F-UOqIY6hz4mkvM8gl39CXDgKoA/edit?usp=sharing",
)

SERVICE_ACCOUNT_JSON = os.environ.get("SERVICE_ACCOUNT_JSON", "")

SERVICE_ACCOUNT_FILE = os.environ.get(
    "SERVICE_ACCOUNT_FILE",
    str(Path(__file__).resolve().parent / "service_account.json"),
)

SHEET_NAMES: dict[str, str] = {
    "teams": "team",
    "aliases": "aliases",
    "price_table_items": "price_table_items",
    "templates": "templates",
    "test_cases": "test_cases",
}

MANUAL_REPLY_STORAGE_FILE = os.environ.get(
    "MANUAL_REPLY_STORAGE_FILE",
    str(Path(__file__).resolve().parent / "data" / "pending_manual_replies.db"),
)

MANUAL_REPLY_ADMIN_TOKEN = os.environ.get("MANUAL_REPLY_ADMIN_TOKEN", "")
MANUAL_REPLY_ADMIN_USERNAME = os.environ.get("MANUAL_REPLY_ADMIN_USERNAME", "")
MANUAL_REPLY_ADMIN_PASSWORD = os.environ.get("MANUAL_REPLY_ADMIN_PASSWORD", "")

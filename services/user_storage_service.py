from __future__ import annotations

import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
USER_DATA_ROOT = BASE_DIR / "database" / "users"


def safe_user_directory_name(user_id: str) -> str:
    value = str(user_id or "").strip()
    if not value:
        raise ValueError("사용자 ID는 비어 있을 수 없습니다.")
    return re.sub(r"[^a-zA-Z0-9._-]", "_", value)


def user_storage_directory(user_id: str) -> Path:
    return USER_DATA_ROOT / safe_user_directory_name(user_id)


def portfolio_database_path(user_id: str) -> Path:
    return user_storage_directory(user_id) / "portfolio.db"


def feedback_database_path(user_id: str) -> Path:
    return user_storage_directory(user_id) / "feedback.db"


def log_database_path(user_id: str) -> Path:
    return user_storage_directory(user_id) / "logs.db"

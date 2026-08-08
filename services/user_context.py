from __future__ import annotations

from contextvars import ContextVar


DEFAULT_USER_ID = "default_user"
_active_user_id: ContextVar[str] = ContextVar("assetos_user_id", default=DEFAULT_USER_ID)


def set_current_user_id(user_id: str) -> None:
    normalized = str(user_id or "").strip()
    if not normalized:
        raise ValueError("현재 사용자 ID는 비어 있을 수 없습니다.")
    _active_user_id.set(normalized)


def get_current_user_id() -> str:
    """Return the authenticated request scope, defaulting to legacy v1.0."""
    return _active_user_id.get()

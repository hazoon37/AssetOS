from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass

DEFAULT_USER_ID = "default_user"


@dataclass(frozen=True)
class CurrentUser:
    """Single authenticated-user context shared by repositories and services."""

    id: str
    name: str
    email: str
    photo: str = ""
    plan: str = "free"
    is_guest: bool = False
    is_authenticated: bool = False


_DEFAULT_USER = CurrentUser(DEFAULT_USER_ID, DEFAULT_USER_ID, "")
_active_user: ContextVar[CurrentUser] = ContextVar(
    "assetos_current_user", default=_DEFAULT_USER
)


def set_current_user(user: CurrentUser) -> None:
    if not str(user.id or "").strip():
        raise ValueError("현재 사용자 ID는 비어 있을 수 없습니다.")
    _active_user.set(user)


def current_user() -> CurrentUser:
    """Return the active profile, defaulting to the legacy local user."""
    return _active_user.get()


def set_current_user_id(user_id: str) -> None:
    """Backward-compatible ID-only context setter."""
    normalized = str(user_id or "").strip()
    if not normalized:
        raise ValueError("현재 사용자 ID는 비어 있을 수 없습니다.")
    set_current_user(CurrentUser(normalized, normalized, ""))


def get_current_user_id() -> str:
    """Return the authenticated request scope, defaulting to legacy v1.0."""
    return current_user().id

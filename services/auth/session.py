from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import asdict, dataclass
from typing import cast
from uuid import uuid4

import streamlit as st

AUTH_SESSION_KEY = "assetos_authenticated_user"
GUEST_USER_ID_KEY = "assetos_guest_user_id"
GUEST_FALLBACK_KEY = "assetos_guest_fallback"


@dataclass(frozen=True)
class AuthenticatedUser:
    """Provider-neutral user profile retained for the current app session."""

    subject: str
    email: str
    name: str
    avatar_url: str = ""
    provider: str = "google"
    plan: str = "free"


def _state(
    state: MutableMapping[str, object] | None = None,
) -> MutableMapping[str, object]:
    return state if state is not None else cast(MutableMapping[str, object], st.session_state)


def save_authenticated_user(
    user: AuthenticatedUser,
    state: MutableMapping[str, object] | None = None,
) -> None:
    _state(state)[AUTH_SESSION_KEY] = asdict(user)


def get_authenticated_user(
    state: MutableMapping[str, object] | None = None,
) -> AuthenticatedUser | None:
    value = _state(state).get(AUTH_SESSION_KEY)
    if not isinstance(value, dict):
        return None
    try:
        return AuthenticatedUser(
            subject=str(value["subject"]),
            email=str(value["email"]),
            name=str(value["name"]),
            avatar_url=str(value.get("avatar_url") or ""),
            provider=str(value.get("provider") or "google"),
            plan=str(value.get("plan") or "free"),
        )
    except KeyError:
        return None


def clear_authenticated_user(
    state: MutableMapping[str, object] | None = None,
) -> None:
    _state(state).pop(AUTH_SESSION_KEY, None)


def get_or_create_guest_user_id(
    state: MutableMapping[str, object] | None = None,
) -> str:
    """Return the stable guest ID retained for the current browser session."""
    session = _state(state)
    existing = str(session.get(GUEST_USER_ID_KEY) or "").strip()
    if existing:
        return existing
    guest_user_id = str(uuid4())
    session[GUEST_USER_ID_KEY] = guest_user_id
    return guest_user_id


def request_guest_fallback(
    message: str = "",
    state: MutableMapping[str, object] | None = None,
) -> None:
    _state(state)[GUEST_FALLBACK_KEY] = message or True


def consume_guest_fallback(
    state: MutableMapping[str, object] | None = None,
) -> str:
    value = _state(state).pop(GUEST_FALLBACK_KEY, "")
    return str(value) if value is not True else ""

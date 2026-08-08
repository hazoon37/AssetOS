from __future__ import annotations

from collections.abc import MutableMapping
from dataclasses import asdict, dataclass

import streamlit as st

AUTH_SESSION_KEY = "assetos_authenticated_user"


@dataclass(frozen=True)
class AuthenticatedUser:
    """Provider-neutral user profile retained for the current app session."""

    subject: str
    email: str
    name: str
    avatar_url: str = ""
    provider: str = "google"


def _state(
    state: MutableMapping[str, object] | None = None,
) -> MutableMapping[str, object]:
    return state if state is not None else st.session_state


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
        )
    except KeyError:
        return None


def clear_authenticated_user(
    state: MutableMapping[str, object] | None = None,
) -> None:
    _state(state).pop(AUTH_SESSION_KEY, None)

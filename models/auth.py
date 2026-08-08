from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AuthIdentity:
    """Provider-neutral identity returned by an authentication provider."""

    user_id: str
    email: str
    name: str
    provider: str


@dataclass(frozen=True)
class AuthContext:
    """Authenticated request context passed into user-scoped services."""

    user_id: str
    email: str
    name: str
    provider: str
    authenticated: bool

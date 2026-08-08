from __future__ import annotations

from hashlib import sha256
from typing import TYPE_CHECKING

from services.auth.session import AuthenticatedUser, get_or_create_guest_user_id

if TYPE_CHECKING:
    from services.auth.user_service import UserService


def google_user_id(email: str) -> str:
    """Return a stable pseudonymous ID from a normalized Google email."""
    normalized = str(email or "").strip().casefold()
    if not normalized:
        raise ValueError("Google 이메일이 필요합니다.")
    return sha256(normalized.encode("utf-8")).hexdigest()


def repository_user_id(user: AuthenticatedUser) -> str:
    provider = user.provider.lower()
    if provider == "google":
        return google_user_id(user.email)
    if provider == "local":
        return user.subject
    return f"{provider}:{user.subject}"


def login_as_developer(
    local_user_id: str,
    user_service: UserService | None = None,
) -> AuthenticatedUser:
    """Activate the existing browser-local SQLite user for offline work."""
    from services.auth.user_service import UserService

    return (user_service or UserService()).start_developer(local_user_id)


def login_as_guest(
    user_service: UserService | None = None,
) -> AuthenticatedUser:
    """Activate a session-isolated guest user with the sample portfolio."""
    from services.auth.user_service import UserService

    return (user_service or UserService()).start_guest(get_or_create_guest_user_id())

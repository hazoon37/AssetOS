from __future__ import annotations

from services.auth.session import AuthenticatedUser, get_or_create_guest_user_id
from services.auth.user_service import UserService


def login_as_developer(
    local_user_id: str,
    user_service: UserService | None = None,
) -> AuthenticatedUser:
    """Activate the existing browser-local SQLite user for offline work."""
    return (user_service or UserService()).start_developer(local_user_id)


def login_as_guest(
    user_service: UserService | None = None,
) -> AuthenticatedUser:
    """Activate a session-isolated guest user with the sample portfolio."""
    return (user_service or UserService()).start_guest(get_or_create_guest_user_id())

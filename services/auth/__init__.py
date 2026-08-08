"""Authentication providers and session-backed user profiles."""

from services.auth.google_auth import (
    current_google_user,
    google_auth_is_configured,
    login_with_google,
    logout_google,
)
from services.auth.session import AuthenticatedUser

__all__ = [
    "AuthenticatedUser",
    "current_google_user",
    "google_auth_is_configured",
    "login_with_google",
    "logout_google",
]

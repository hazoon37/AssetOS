from __future__ import annotations

from collections.abc import Mapping

import streamlit as st

from services.auth.session import AuthenticatedUser
from services.auth.user_service import UserService

GOOGLE_PROVIDER = "google"


def google_user_from_claims(
    claims: Mapping[str, object],
) -> AuthenticatedUser | None:
    """Build a validated provider-neutral profile from Google OIDC claims."""
    subject = str(claims.get("sub") or "").strip()
    email = str(claims.get("email") or "").strip()
    if not subject or not email:
        return None
    return AuthenticatedUser(
        subject=subject,
        email=email,
        name=str(claims.get("name") or email).strip(),
        avatar_url=str(claims.get("picture") or "").strip(),
        provider=GOOGLE_PROVIDER,
    )


def google_auth_is_configured() -> bool:
    """Return whether the named Google OIDC provider has required secrets."""
    try:
        auth = st.secrets.get("auth", {})
        google = auth.get(GOOGLE_PROVIDER, {})
        return all(
            str(value or "").strip()
            for value in (
                auth.get("redirect_uri"),
                auth.get("cookie_secret"),
                google.get("client_id"),
                google.get("client_secret"),
                google.get("server_metadata_url"),
            )
        )
    except (AttributeError, KeyError, TypeError):
        return False


def current_google_user(
    user_service: UserService | None = None,
) -> AuthenticatedUser | None:
    """Synchronize Streamlit's verified identity into the session profile."""
    service = user_service or UserService()
    if not bool(getattr(st.user, "is_logged_in", False)):
        current = service.current()
        if current is not None and current.provider == GOOGLE_PROVIDER:
            service.forget()
        return None
    user = google_user_from_claims(st.user.to_dict())
    return service.remember(user) if user is not None else None


def login_with_google() -> None:
    if not google_auth_is_configured():
        raise RuntimeError("Google OAuth 설정이 필요합니다.")
    st.login(GOOGLE_PROVIDER)


def logout_google(user_service: UserService | None = None) -> None:
    (user_service or UserService()).forget()
    if bool(getattr(st.user, "is_logged_in", False)):
        st.logout()
    else:
        st.rerun()

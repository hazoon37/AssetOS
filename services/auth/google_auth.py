from __future__ import annotations

from collections.abc import Mapping

import streamlit as st
from streamlit.errors import StreamlitAuthError, StreamlitSecretNotFoundError

from services.auth.session import AuthenticatedUser, request_guest_fallback
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
    except (AttributeError, KeyError, TypeError, StreamlitSecretNotFoundError):
        return False


def current_google_user(
    user_service: UserService | None = None,
) -> AuthenticatedUser | None:
    """Synchronize Streamlit's verified identity into the session profile."""
    service = user_service or UserService()
    try:
        if not bool(getattr(st.user, "is_logged_in", False)):
            current = service.current()
            if current is not None and current.provider == GOOGLE_PROVIDER:
                service.forget()
            return None
        user = google_user_from_claims(st.user.to_dict())
        if user is None:
            request_guest_fallback("Google 사용자 정보를 확인하지 못해 Guest로 시작합니다.")
            return None
        return service.transition_to_google(user)
    except (StreamlitAuthError, AttributeError, KeyError, TypeError, ValueError):
        service.forget()
        request_guest_fallback("Google 로그인 오류로 Guest Mode를 시작합니다.")
        return None


def login_with_google() -> None:
    if not google_auth_is_configured():
        raise RuntimeError("Google OAuth 설정이 필요합니다.")
    try:
        st.login(GOOGLE_PROVIDER)
    except StreamlitAuthError as error:
        raise RuntimeError(
            "Google 로그인을 시작하지 못해 Guest Mode로 전환합니다."
        ) from error


def logout_google(user_service: UserService | None = None) -> None:
    (user_service or UserService()).forget()
    request_guest_fallback("로그아웃되어 Guest Mode로 전환했습니다.")
    if bool(getattr(st.user, "is_logged_in", False)):
        st.logout()
    else:
        st.rerun()

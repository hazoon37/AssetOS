from __future__ import annotations

from abc import ABC, abstractmethod

from models.auth import AuthContext, AuthIdentity
from repositories import get_asset_repository
from repositories.asset_repository import AssetRepository
from repositories.sqlite_asset_repository import (
    DEFAULT_USER_EMAIL,
    DEFAULT_USER_ID,
)
from services.user_context import set_current_user_id

SUPPORTED_AUTH_PROVIDERS = ("local", "google", "apple", "github")


class AuthenticationProvider(ABC):
    """Provider-neutral authentication boundary for local and OAuth identities."""

    @abstractmethod
    def authenticate(self) -> AuthIdentity:
        """Return a verified identity or raise an authentication error."""


class DefaultUserAuthenticationProvider(AuthenticationProvider):
    """Current no-login provider preserving AssetOS v1.0 behavior."""

    def authenticate(self) -> AuthIdentity:
        return AuthIdentity(
            user_id=DEFAULT_USER_ID,
            email=DEFAULT_USER_EMAIL,
            name=DEFAULT_USER_ID,
            provider="local",
        )


class AuthenticationService:
    """Resolve an identity and provision its repository-owned user scope."""

    def __init__(
        self,
        provider: AuthenticationProvider | None = None,
        repository: AssetRepository | None = None,
    ) -> None:
        self.provider = provider or DefaultUserAuthenticationProvider()
        self.repository = repository or get_asset_repository()

    def get_context(self) -> AuthContext:
        identity = self.provider.authenticate()
        provider_name = identity.provider.lower()
        if provider_name not in SUPPORTED_AUTH_PROVIDERS:
            raise ValueError(f"지원하지 않는 인증 제공자입니다: {identity.provider}")
        repository_user_id = (
            identity.user_id
            if provider_name == "local"
            else f"{provider_name}:{identity.user_id}"
        )
        user = self.repository.ensure_user(
            repository_user_id,
            identity.email,
            identity.name,
        )
        set_current_user_id(user.id)
        return AuthContext(
            user_id=user.id,
            email=user.email,
            name=user.name,
            provider=provider_name,
            authenticated=True,
        )


def get_current_auth_context() -> AuthContext:
    """Return the current request identity; v1.0 resolves to default_user."""
    return AuthenticationService().get_context()

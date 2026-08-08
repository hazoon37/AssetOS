from __future__ import annotations

import tempfile
from pathlib import Path

from models.auth import AuthIdentity
from repositories.sqlite_asset_repository import SQLiteAssetRepository
from services.auth_service import AuthenticationProvider, AuthenticationService
from services.user_context import get_current_user_id, set_current_user_id


class TestProvider(AuthenticationProvider):
    def authenticate(self) -> AuthIdentity:
        return AuthIdentity("github_123", "user@example.com", "User", "github")


def test_authentication_provisions_user_and_sets_request_scope() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repository = SQLiteAssetRepository(Path(directory) / "assets.db")
        context = AuthenticationService(TestProvider(), repository).get_context()
        assert context.user_id == "github:github_123"
        assert context.provider == "github"
        assert context.authenticated is True
        assert get_current_user_id() == "github:github_123"
        assert repository.get_accounts("github:github_123")["account_name"].tolist() == ["My Portfolio"]
    set_current_user_id("default_user")

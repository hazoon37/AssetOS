from unittest.mock import Mock

from models.user import User
from services.auth.google_auth import google_user_from_claims
from services.auth.session import (
    AuthenticatedUser,
    clear_authenticated_user,
    get_authenticated_user,
    save_authenticated_user,
)
from services.auth.user_service import UserService
from services.user_context import get_current_user_id, set_current_user_id


def test_google_claims_create_profile_with_avatar() -> None:
    user = google_user_from_claims({
        "sub": "google-123",
        "email": "user@example.com",
        "name": "Asset User",
        "picture": "https://example.com/avatar.png",
    })
    assert user == AuthenticatedUser(
        subject="google-123",
        email="user@example.com",
        name="Asset User",
        avatar_url="https://example.com/avatar.png",
    )


def test_google_claims_require_subject_and_email() -> None:
    assert google_user_from_claims({"email": "user@example.com"}) is None
    assert google_user_from_claims({"sub": "google-123"}) is None


def test_authenticated_user_persists_in_session_mapping() -> None:
    state: dict[str, object] = {}
    user = AuthenticatedUser("google-123", "user@example.com", "Asset User")
    save_authenticated_user(user, state)
    assert get_authenticated_user(state) == user
    clear_authenticated_user(state)
    assert get_authenticated_user(state) is None


def test_authenticated_user_sets_sqlite_repository_scope() -> None:
    state: dict[str, object] = {}
    repository = Mock()
    repository.ensure_user.return_value = User(
        id="google:google-123",
        email="user@example.com",
        name="Asset User",
        created_at="2026-08-08 00:00:00",
    )
    service = UserService(
        store=type("Store", (), {
            "get": lambda self: get_authenticated_user(state),
            "save": lambda self, user: save_authenticated_user(user, state),
            "clear": lambda self: clear_authenticated_user(state),
        })(),
        repository=repository,
    )
    user = AuthenticatedUser("google-123", "user@example.com", "Asset User")

    assert service.remember(user) == user
    repository.ensure_user.assert_called_once_with(
        "google:google-123", "user@example.com", "Asset User"
    )
    assert get_current_user_id() == "google:google-123"
    assert get_authenticated_user(state) == user
    set_current_user_id("default_user")


def test_developer_login_reuses_existing_local_user_scope() -> None:
    repository = Mock()
    repository.ensure_user.return_value = User(
        id="local:123", email="developer@assetos.local", name="Developer",
        created_at="2026-08-08 00:00:00",
    )
    service = UserService(repository=repository)
    user = service.start_developer("local:123")
    assert user.provider == "local"
    repository.ensure_user.assert_called_once_with(
        "local:123", "developer@assetos.local", "Developer"
    )
    set_current_user_id("default_user")


def test_guest_mode_creates_isolated_sample_portfolio() -> None:
    repository = Mock()
    repository.ensure_user.side_effect = lambda user_id, email, name: User(
        id=user_id, email=email, name=name, created_at="2026-08-08 00:00:00"
    )
    repository.get_assets.return_value.empty = True
    service = UserService(repository=repository)
    user = service.start_guest()
    guest_user_id = f"guest:{user.subject}"
    assert user.provider == "guest"
    repository.get_assets.assert_called_once_with(guest_user_id)
    saved_rows = repository.save_assets.call_args.args[0]
    assert len(saved_rows) == 4
    assert repository.save_assets.call_args.kwargs["user_id"] == guest_user_id
    set_current_user_id("default_user")

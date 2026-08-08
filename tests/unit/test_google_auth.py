import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from models.user import User
from repositories.sqlite_asset_repository import SQLiteAssetRepository
from services.auth.google_auth import (
    current_google_user,
    google_user_from_claims,
    login_with_google,
    logout_google,
)
from services.auth.session import (
    AuthenticatedUser,
    clear_authenticated_user,
    get_authenticated_user,
    get_or_create_guest_user_id,
    save_authenticated_user,
)
from services.auth.user_service import GUEST_SAMPLE_ASSETS, UserService
from services.user_context import current_user, get_current_user_id, set_current_user_id


class _StateStore:
    def __init__(self, state: dict[str, object]) -> None:
        self.state = state

    def get(self) -> AuthenticatedUser | None:
        return get_authenticated_user(self.state)

    def save(self, user: AuthenticatedUser) -> None:
        save_authenticated_user(user, self.state)

    def clear(self) -> None:
        clear_authenticated_user(self.state)


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


def test_google_login_claims_activate_persistent_session_user() -> None:
    expected = AuthenticatedUser("google-123", "user@example.com", "Asset User")
    service = Mock()
    service.remember.return_value = expected
    streamlit_user = SimpleNamespace(
        is_logged_in=True,
        to_dict=lambda: {
            "sub": "google-123", "email": "user@example.com", "name": "Asset User"
        },
    )
    with patch("services.auth.google_auth.st.user", streamlit_user):
        assert current_google_user(service) == expected
    service.remember.assert_called_once_with(expected)


def test_google_login_uses_named_streamlit_provider() -> None:
    with patch(
        "services.auth.google_auth.google_auth_is_configured", return_value=True
    ), patch("services.auth.google_auth.st.login") as login:
        login_with_google()
    login.assert_called_once_with("google")


def test_logout_clears_local_session_without_google_redirect() -> None:
    service = Mock()
    streamlit_user = SimpleNamespace(is_logged_in=False)
    with patch("services.auth.google_auth.st.user", streamlit_user), patch(
        "services.auth.google_auth.st.rerun"
    ) as rerun:
        logout_google(service)
    service.forget.assert_called_once_with()
    rerun.assert_called_once_with()


def test_authenticated_user_persists_in_session_mapping() -> None:
    state: dict[str, object] = {}
    user = AuthenticatedUser("google-123", "user@example.com", "Asset User")
    save_authenticated_user(user, state)
    assert get_authenticated_user(state) == user
    clear_authenticated_user(state)
    assert get_authenticated_user(state) is None


def test_guest_user_id_is_stable_in_session_mapping() -> None:
    state: dict[str, object] = {}
    first = get_or_create_guest_user_id(state)
    second = get_or_create_guest_user_id(state)
    assert first == second
    assert first


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
        store=_StateStore(state),
        repository=repository,
    )
    user = AuthenticatedUser("google-123", "user@example.com", "Asset User")

    assert service.remember(user) == user
    repository.ensure_user.assert_called_once_with(
        "google:google-123", "user@example.com", "Asset User"
    )
    assert get_current_user_id() == "google:google-123"
    assert current_user().name == "Asset User"
    assert current_user().email == "user@example.com"
    assert current_user().photo == ""
    assert current_user().plan == "free"
    assert current_user().is_guest is False
    assert current_user().is_authenticated is True
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
    assert current_user().is_guest is False
    assert current_user().is_authenticated is True
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
    user = service.start_guest("stable-guest-id")
    guest_user_id = f"guest:{user.subject}"
    assert user.provider == "guest"
    assert current_user().is_guest is True
    assert current_user().is_authenticated is False
    repository.get_assets.assert_called_once_with(guest_user_id)
    saved_rows = repository.save_assets.call_args.args[0]
    assert len(saved_rows) == 4
    assert repository.save_assets.call_args.kwargs["user_id"] == guest_user_id
    set_current_user_id("default_user")


def test_google_users_get_persistent_isolated_sqlite_portfolios() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repository = SQLiteAssetRepository(Path(directory) / "assets.db")
        first_state: dict[str, object] = {}
        first_service = UserService(_StateStore(first_state), repository)
        google_user = AuthenticatedUser(
            "google-123", "user@example.com", "Asset User"
        )

        first_service.remember(google_user)
        assert repository.get_assets().empty
        repository.save_assets([dict(GUEST_SAMPLE_ASSETS[0])])

        returning_service = UserService(_StateStore(first_state), repository)
        assert returning_service.current() == google_user
        assert repository.get_assets()["symbol"].tolist() == ["AAPL"]

        second_user = AuthenticatedUser(
            "google-456", "second@example.com", "Second User"
        )
        UserService(_StateStore({}), repository).remember(second_user)
        assert repository.get_assets().empty
    set_current_user_id("default_user")

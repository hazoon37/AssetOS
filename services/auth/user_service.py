from __future__ import annotations

from typing import Protocol

from repositories import (
    activate_user_repository,
    get_asset_repository,
    get_legacy_asset_repository,
)
from repositories.asset_repository import AssetRepository
from services.auth.local_user import repository_user_id
from services.auth.session import (
    AuthenticatedUser,
    clear_authenticated_user,
    get_authenticated_user,
    get_or_create_guest_user_id,
    save_authenticated_user,
)
from services.user_context import CurrentUser, set_current_user

GUEST_SAMPLE_ASSETS: tuple[dict[str, object], ...] = (
    {
        "asset_type": "미국주식", "asset_name": "Apple", "symbol": "AAPL",
        "quantity": 10.0, "average_price": 180.0, "current_price": 210.0,
        "currency": "USD", "memo": "Guest sample",
    },
    {
        "asset_type": "미국ETF", "asset_name": "Invesco QQQ", "symbol": "QQQ",
        "quantity": 5.0, "average_price": 480.0, "current_price": 520.0,
        "currency": "USD", "memo": "Guest sample",
    },
    {
        "asset_type": "국내주식", "asset_name": "삼성전자", "symbol": "005930.KS",
        "quantity": 20.0, "average_price": 72000.0, "current_price": 78000.0,
        "currency": "KRW", "memo": "Guest sample",
    },
    {
        "asset_type": "현금", "asset_name": "생활예비자금", "symbol": "",
        "quantity": 1.0, "average_price": 5000000.0, "current_price": 5000000.0,
        "currency": "KRW", "memo": "Guest sample",
    },
)


class UserProfileStore(Protocol):
    """Persistence boundary that can later be implemented by Firestore."""

    def get(self) -> AuthenticatedUser | None: ...

    def save(self, user: AuthenticatedUser) -> None: ...

    def clear(self) -> None: ...


class SessionUserProfileStore:
    """Current profile store; it never writes authentication data to SQLite."""

    def get(self) -> AuthenticatedUser | None:
        return get_authenticated_user()

    def save(self, user: AuthenticatedUser) -> None:
        save_authenticated_user(user)

    def clear(self) -> None:
        clear_authenticated_user()


class UserService:
    def __init__(
        self,
        store: UserProfileStore | None = None,
        repository: AssetRepository | None = None,
    ) -> None:
        self.store = store or SessionUserProfileStore()
        self._uses_default_repository = repository is None
        self.repository = repository or get_asset_repository()

    @staticmethod
    def _repository_user_id(user: AuthenticatedUser) -> str:
        return repository_user_id(user)

    @staticmethod
    def _copy_user_scope(
        source: AssetRepository,
        source_user_id: str,
        target: AssetRepository,
        target_user_id: str,
    ) -> None:
        target_accounts = {
            str(row["account_name"]): int(row["id"])
            for _, row in target.get_accounts(target_user_id).iterrows()
        }
        for _, account in source.get_accounts(source_user_id).iterrows():
            account_name = str(account["account_name"])
            target_account_id = target_accounts.get(account_name)
            if target_account_id is None:
                created = target.create_account(
                    account_name,
                    str(account["account_type"]),
                    target_user_id,
                )
                target_account_id = created.id
                target_accounts[account_name] = target_account_id
            assets = source.get_assets(source_user_id, int(account["id"]))
            if not assets.empty:
                target.save_assets(
                    assets.to_dict("records"),
                    user_id=target_user_id,
                    account_id=target_account_id,
                )
        preferences = source.get_preferences(source_user_id)
        target.save_preferences(
            preferences.base_currency,
            preferences.theme,
            target_user_id,
        )

    def _select_repository(self, user: AuthenticatedUser, user_id: str) -> None:
        if not self._uses_default_repository:
            return
        source = get_legacy_asset_repository()
        legacy_user_id = (
            f"google:{user.subject}"
            if user.provider.lower() == "google"
            else user_id
        )
        target = activate_user_repository(user_id)
        target.ensure_user(user_id, user.email, user.name)
        if target.get_assets(user_id).empty and source.get_user(legacy_user_id) is not None:
            self._copy_user_scope(source, legacy_user_id, target, user_id)
        self.repository = target

    def _activate(self, user: AuthenticatedUser) -> None:
        repository_user_id = self._repository_user_id(user)
        self._select_repository(user, repository_user_id)
        persisted = self.repository.ensure_user(
            repository_user_id,
            user.email,
            user.name,
        )
        set_current_user(CurrentUser(
            id=persisted.id,
            name=persisted.name,
            email=persisted.email,
            photo=user.avatar_url,
            plan=user.plan,
            is_guest=user.provider.lower() == "guest",
            is_authenticated=user.provider.lower() != "guest",
        ))

    def current(self) -> AuthenticatedUser | None:
        user = self.store.get()
        if user is not None:
            self._activate(user)
        return user

    def remember(self, user: AuthenticatedUser) -> AuthenticatedUser:
        self._activate(user)
        self.store.save(user)
        return user

    def transition_to_google(self, user: AuthenticatedUser) -> AuthenticatedUser:
        """Migrate the active Guest scope before committing the Google session."""
        previous = self.store.get()
        self._activate(user)
        if previous is not None and previous.provider.lower() == "guest":
            guest_user_id = self._repository_user_id(previous)
            guest_repository = activate_user_repository(guest_user_id)
            if not guest_repository.get_assets(guest_user_id).empty:
                self._copy_user_scope(
                    guest_repository,
                    guest_user_id,
                    self.repository,
                    self._repository_user_id(user),
                )
                guest_repository.replace_all_assets([], user_id=guest_user_id)
        self.store.save(user)
        return user

    def start_guest(self, guest_user_id: str | None = None) -> AuthenticatedUser:
        """Create an isolated demo scope and seed it once with sample assets."""
        user = self.remember(AuthenticatedUser(
            subject=guest_user_id or get_or_create_guest_user_id(),
            email="guest@assetos.local",
            name="Guest",
            provider="guest",
        ))
        repository_user_id = self._repository_user_id(user)
        if self.repository.get_assets(repository_user_id).empty:
            self.repository.save_assets(GUEST_SAMPLE_ASSETS, user_id=repository_user_id)
        return user

    def start_developer(self, local_user_id: str) -> AuthenticatedUser:
        """Reuse the existing browser-local SQLite scope for offline work."""
        return self.remember(AuthenticatedUser(
            subject=local_user_id,
            email="developer@assetos.local",
            name="Developer",
            provider="local",
        ))

    def forget(self) -> None:
        self.store.clear()

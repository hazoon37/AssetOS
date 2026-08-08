from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from models.account import Account
from models.preferences import UserPreferences
from models.snapshot import PortfolioSnapshot
from models.user import User


class AssetRepository(ABC):
    """Persistence contract shared by SQLite and future remote backends."""

    @abstractmethod
    def initialize(self) -> None:
        """Prepare storage without changing the logical asset schema."""

    @abstractmethod
    def get_assets(
        self,
        user_id: str | None = None,
        account_id: int | None = None,
    ) -> pd.DataFrame:
        """Return one user's assets in stable repository order."""

    @abstractmethod
    def get_accounts(self, user_id: str | None = None) -> pd.DataFrame:
        """Return accounts owned by one user."""

    @abstractmethod
    def get_user(self, user_id: str | None = None) -> User | None:
        """Return one user model when it exists."""

    @abstractmethod
    def ensure_user(self, user_id: str, email: str, name: str) -> User:
        """Create or update a provider-authenticated user."""

    @abstractmethod
    def migrate_user_scope(self, source_user_id: str, target_user_id: str) -> bool:
        """Atomically transfer one local user scope for future identity linking."""

    @abstractmethod
    def create_account(
        self,
        account_name: str,
        account_type: str,
        user_id: str | None = None,
    ) -> Account:
        """Create and return a validated investment account."""

    @abstractmethod
    def get_preferences(self, user_id: str | None = None) -> UserPreferences:
        """Return persisted user preferences, creating defaults when absent."""

    @abstractmethod
    def save_preferences(
        self,
        base_currency: str,
        theme: str,
        user_id: str | None = None,
    ) -> UserPreferences:
        """Validate and persist user preferences."""

    @abstractmethod
    def save_assets(
        self,
        rows: Sequence[dict[str, Any]],
        user_id: str | None = None,
        account_id: int | None = None,
    ) -> None:
        """Append validated assets without removing existing rows."""

    @abstractmethod
    def replace_all_assets(
        self,
        rows: Sequence[dict[str, Any]],
        user_id: str | None = None,
        account_id: int | None = None,
    ) -> None:
        """Atomically replace all assets with validated rows."""

    @abstractmethod
    def backup(self) -> Path | None:
        """Create a recoverable backup when supported by the backend."""

    @abstractmethod
    def export_backup(self) -> bytes:
        """Return a consistent full-database backup."""

    @abstractmethod
    def restore_backup(self, backup: bytes) -> None:
        """Validate and atomically restore a full-database backup."""

    @abstractmethod
    def add_asset(
        self,
        *,
        asset_type: str,
        asset_name: str,
        symbol: str,
        quantity: float,
        average_price: float,
        current_price: float,
        currency: str,
        memo: str,
        metadata: dict[str, Any] | None = None,
        user_id: str | None = None,
        account_id: int | None = None,
    ) -> None:
        """Add one asset."""

    @abstractmethod
    def update_asset(
        self,
        *,
        asset_id: int,
        asset_type: str,
        asset_name: str,
        symbol: str,
        quantity: float,
        average_price: float,
        current_price: float,
        currency: str,
        memo: str,
        user_id: str | None = None,
    ) -> None:
        """Update one asset by repository identifier."""

    @abstractmethod
    def update_current_price(
        self,
        asset_id: int,
        current_price: float,
        user_id: str | None = None,
    ) -> None:
        """Update only the latest stored price."""

    @abstractmethod
    def delete_asset(self, asset_id: int, user_id: str | None = None) -> None:
        """Delete one asset by repository identifier."""

    @abstractmethod
    def delete_assets(
        self,
        asset_ids: Sequence[int],
        user_id: str | None = None,
    ) -> int:
        """Atomically delete user-owned assets and return the deleted count."""

    @abstractmethod
    def save_snapshot(
        self,
        snapshot_data: dict[str, Any],
        user_id: str | None = None,
        account_id: int | None = None,
    ) -> PortfolioSnapshot:
        """Persist a structured portfolio snapshot for one user."""

    @abstractmethod
    def get_snapshots(
        self,
        user_id: str | None = None,
        account_id: int | None = None,
        limit: int = 100,
    ) -> list[PortfolioSnapshot]:
        """Return only snapshots owned by the selected user."""

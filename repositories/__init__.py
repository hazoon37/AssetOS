from __future__ import annotations

from repositories.asset_repository import AssetRepository
from repositories.sqlite_asset_repository import SQLiteAssetRepository


_default_repository: AssetRepository = SQLiteAssetRepository()


def get_asset_repository() -> AssetRepository:
    """Return the application-wide default asset repository."""
    return _default_repository


def set_asset_repository(repository: AssetRepository) -> None:
    """Override the default repository for tests or a future backend."""
    global _default_repository
    _default_repository = repository

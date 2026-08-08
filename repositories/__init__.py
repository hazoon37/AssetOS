from __future__ import annotations

import threading

from repositories.asset_repository import AssetRepository
from repositories.sqlite_asset_repository import SQLiteAssetRepository
from services.user_context import DEFAULT_USER_ID, get_current_user_id
from services.user_storage_service import portfolio_database_path

_legacy_repository: AssetRepository = SQLiteAssetRepository()
_repository_override: AssetRepository | None = None
_user_repositories: dict[str, AssetRepository] = {}
_repository_lock = threading.Lock()


def get_asset_repository() -> AssetRepository:
    """Return the repository isolated to the active User Context."""
    if _repository_override is not None:
        return _repository_override
    user_id = get_current_user_id()
    if user_id == DEFAULT_USER_ID:
        return _legacy_repository
    with _repository_lock:
        repository = _user_repositories.get(user_id)
        if repository is None:
            repository = SQLiteAssetRepository(portfolio_database_path(user_id))
            _user_repositories[user_id] = repository
        return repository


def get_legacy_asset_repository() -> AssetRepository:
    """Return the pre-5D SQLite repository for one-time user data migration."""
    return _legacy_repository


def set_asset_repository(repository: AssetRepository) -> None:
    """Override the default repository for tests or a future backend."""
    global _repository_override
    _repository_override = repository


def activate_user_repository(user_id: str) -> AssetRepository:
    """Select the isolated SQLite database for the active user."""
    with _repository_lock:
        repository = _user_repositories.get(user_id)
        if repository is None:
            repository = SQLiteAssetRepository(portfolio_database_path(user_id))
            _user_repositories[user_id] = repository
    repository.initialize()
    return repository

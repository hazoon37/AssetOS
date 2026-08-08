from __future__ import annotations

import tempfile
from pathlib import Path

from repositories.sqlite_asset_repository import DEFAULT_USER_ID, SQLiteAssetRepository
from services.local_user_service import (
    generate_local_user_id,
    initialize_local_user,
    is_valid_local_user_id,
)
from services.user_context import set_current_user_id


def _asset() -> dict[str, object]:
    return {
        "asset_type": "미국주식", "asset_name": "Apple", "symbol": "AAPL",
        "quantity": 1, "average_price": 100, "current_price": 120,
        "currency": "USD", "memo": "legacy",
    }


def test_generate_and_validate_local_user_id() -> None:
    user_id = generate_local_user_id()
    assert user_id.startswith("local:")
    assert is_valid_local_user_id(user_id)
    assert not is_valid_local_user_id("local:not-a-uuid")
    assert not is_valid_local_user_id("default_user")


def test_initialize_local_user_claims_legacy_scope_once() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repository = SQLiteAssetRepository(Path(directory) / "assets.db")
        repository.save_assets([_asset()], user_id=DEFAULT_USER_ID)
        repository.save_preferences("USD", "Dark", user_id=DEFAULT_USER_ID)
        legacy_account = int(repository.get_accounts(DEFAULT_USER_ID).iloc[0]["id"])
        repository.save_snapshot(
            {"total": 120}, user_id=DEFAULT_USER_ID, account_id=legacy_account
        )

        local_user = generate_local_user_id()
        assert initialize_local_user(local_user, repository) == local_user
        assert repository.get_assets(DEFAULT_USER_ID).empty
        migrated = repository.get_assets(local_user)
        assert migrated["symbol"].tolist() == ["AAPL"]
        assert migrated["user_id"].tolist() == [local_user]
        assert repository.get_preferences(local_user).base_currency == "USD"
        assert repository.get_snapshots(local_user)[0].snapshot_data["total"] == 120
        assert repository.migrate_user_scope(DEFAULT_USER_ID, local_user) is False
    set_current_user_id(DEFAULT_USER_ID)

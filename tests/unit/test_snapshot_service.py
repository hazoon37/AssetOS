from __future__ import annotations

import tempfile
from pathlib import Path

from repositories.sqlite_asset_repository import SQLiteAssetRepository
from services.snapshot_service import get_portfolio_snapshots, save_portfolio_snapshot


def test_snapshots_are_isolated_by_user_and_account() -> None:
    with tempfile.TemporaryDirectory() as directory:
        repository = SQLiteAssetRepository(Path(directory) / "assets.db")
        repository.ensure_user("user_2", "user2@example.com", "User Two")
        default_account = int(repository.get_accounts().iloc[0]["id"])
        second_account = int(repository.get_accounts("user_2").iloc[0]["id"])

        save_portfolio_snapshot(
            {"summary": {"total": 100}},
            user_id="default_user",
            account_id=default_account,
            repository=repository,
        )
        save_portfolio_snapshot(
            {"summary": {"total": 200}},
            user_id="user_2",
            account_id=second_account,
            repository=repository,
        )

        first = get_portfolio_snapshots(user_id="default_user", repository=repository)
        second = get_portfolio_snapshots(user_id="user_2", repository=repository)
        assert len(first) == 1 and first[0].snapshot_data["summary"]["total"] == 100
        assert len(second) == 1 and second[0].snapshot_data["summary"]["total"] == 200

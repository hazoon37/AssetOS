import tempfile
from pathlib import Path
from unittest.mock import patch

from repositories import activate_user_repository
from repositories.sqlite_asset_repository import SQLiteAssetRepository
from services.user_storage_service import (
    feedback_database_path,
    log_database_path,
    portfolio_database_path,
)


def test_user_storage_files_share_one_isolated_directory() -> None:
    user_id = "a" * 64
    portfolio = portfolio_database_path(user_id)
    assert portfolio.name == "portfolio.db"
    assert feedback_database_path(user_id).parent == portfolio.parent
    assert feedback_database_path(user_id).name == "feedback.db"
    assert log_database_path(user_id).parent == portfolio.parent
    assert log_database_path(user_id).name == "logs.db"


def test_user_storage_sanitizes_non_google_ids() -> None:
    assert portfolio_database_path("guest:123").parent.name == "guest_123"


def test_activation_creates_an_isolated_portfolio_database() -> None:
    user_id = "isolated-user-for-test"
    with tempfile.TemporaryDirectory() as directory:
        database_path = Path(directory) / "portfolio.db"
        with patch("repositories.portfolio_database_path", return_value=database_path):
            repository = activate_user_repository(user_id)
        assert isinstance(repository, SQLiteAssetRepository)
        assert repository.db_path == database_path
        assert database_path.exists()

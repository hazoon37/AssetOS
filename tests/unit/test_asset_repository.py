from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import Mock

from models.account import ACCOUNT_TYPES
from repositories.asset_repository import AssetRepository
from repositories.sqlite_asset_repository import DEFAULT_USER_ID, SQLiteAssetRepository
from services.excel_asset_service import import_asset_rows


def _row(name: str = "Apple", symbol: str = "AAPL") -> dict[str, object]:
    return {
        "asset_type": "미국주식",
        "asset_name": name,
        "symbol": symbol,
        "quantity": 2.0,
        "average_price": 180.0,
        "current_price": 210.0,
        "currency": "USD",
        "memo": "test",
    }


class SQLiteAssetRepositoryTests(unittest.TestCase):
    def test_crud_replace_and_backup_preserve_existing_schema(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteAssetRepository(Path(directory) / "assets.db")
            repository.initialize()
            repository.save_assets([_row()])

            assets = repository.get_assets()
            self.assertEqual(len(assets), 1)
            self.assertEqual(assets.iloc[0]["symbol"], "AAPL")
            self.assertIn("asset_class", assets.columns)
            self.assertIn("updated_at", assets.columns)

            asset_id = int(assets.iloc[0]["id"])
            repository.update_current_price(asset_id, 220.0)
            self.assertEqual(float(repository.get_assets().iloc[0]["current_price"]), 220.0)

            repository.update_asset(
                asset_id=asset_id,
                asset_type="미국주식",
                asset_name="Apple Inc.",
                symbol="AAPL",
                quantity=3.0,
                average_price=185.0,
                current_price=225.0,
                currency="USD",
                memo="updated",
            )
            self.assertEqual(repository.get_assets().iloc[0]["asset_name"], "Apple Inc.")

            backup = repository.backup()
            self.assertIsNotNone(backup)
            assert backup is not None
            self.assertTrue(backup.exists())

            repository.replace_all_assets([_row("NVIDIA", "NVDA")])
            replaced = repository.get_assets()
            self.assertEqual(len(replaced), 1)
            self.assertEqual(replaced.iloc[0]["symbol"], "NVDA")

            repository.delete_asset(int(replaced.iloc[0]["id"]))
            self.assertTrue(repository.get_assets().empty)

            repository.save_assets([_row("Apple", "AAPL"), _row("NVIDIA", "NVDA")])
            deleted = repository.delete_assets(repository.get_assets()["id"].tolist())
            self.assertEqual(deleted, 2)
            self.assertTrue(repository.get_assets().empty)

    def test_excel_import_uses_injected_repository(self) -> None:
        repository = Mock(spec=AssetRepository)
        repository.backup.return_value = Path("backup.db")

        result = import_asset_rows([_row()], repository=repository)

        self.assertTrue(result["success"])
        self.assertEqual(result["backup_path"], "backup.db")
        repository.backup.assert_called_once_with()
        repository.replace_all_assets.assert_called_once_with(
            [_row()], user_id=DEFAULT_USER_ID
        )

    def test_legacy_database_migrates_to_default_user_without_data_loss(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "legacy.db"
            with closing(sqlite3.connect(database_path)) as connection, connection:
                connection.execute(
                    """
                    CREATE TABLE assets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        asset_type TEXT NOT NULL,
                        asset_name TEXT NOT NULL,
                        symbol TEXT,
                        quantity REAL NOT NULL DEFAULT 0,
                        average_price REAL NOT NULL DEFAULT 0,
                        current_price REAL NOT NULL DEFAULT 0,
                        currency TEXT NOT NULL DEFAULT 'KRW',
                        memo TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                connection.execute(
                    """
                    INSERT INTO assets (
                        asset_type, asset_name, symbol, quantity,
                        average_price, current_price, currency, memo
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    ("미국주식", "Apple", "AAPL", 2, 180, 210, "USD", "legacy"),
                )

            repository = SQLiteAssetRepository(database_path)
            repository.initialize()

            user = repository.get_user()
            self.assertIsNotNone(user)
            assert user is not None
            self.assertEqual(user.id, DEFAULT_USER_ID)
            accounts = repository.get_accounts()
            self.assertEqual(accounts["account_name"].tolist(), ["My Portfolio"])
            self.assertEqual(accounts["account_type"].tolist(), ["Other"])
            assets = repository.get_assets()
            self.assertEqual(len(assets), 1)
            self.assertEqual(assets.iloc[0]["asset_name"], "Apple")
            self.assertEqual(assets.iloc[0]["memo"], "legacy")
            self.assertEqual(int(assets.iloc[0]["account_id"]), int(accounts.iloc[0]["id"]))
            self.assertEqual(assets.iloc[0]["user_id"], DEFAULT_USER_ID)

    def test_user_scoped_repository_operations_are_isolated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "assets.db"
            repository = SQLiteAssetRepository(database_path)
            repository.initialize()
            with closing(sqlite3.connect(database_path)) as connection, connection:
                connection.execute(
                    "INSERT INTO users (id, email, name) VALUES (?, ?, ?)",
                    ("user_2", "user2@example.com", "User Two"),
                )

            self.assertEqual(
                repository.get_accounts("user_2")["account_name"].tolist(),
                ["My Portfolio"],
            )

            repository.save_assets([_row("Apple", "AAPL")])
            repository.save_assets([_row("NVIDIA", "NVDA")], user_id="user_2")

            self.assertEqual(repository.get_assets()["symbol"].tolist(), ["AAPL"])
            self.assertEqual(repository.get_assets("user_2")["symbol"].tolist(), ["NVDA"])
            self.assertEqual(repository.get_accounts("user_2")["user_id"].tolist(), ["user_2"])

            second_id = int(repository.get_assets("user_2").iloc[0]["id"])
            repository.update_current_price(second_id, 999, user_id=DEFAULT_USER_ID)
            self.assertEqual(float(repository.get_assets("user_2").iloc[0]["current_price"]), 210.0)

            repository.replace_all_assets([_row("Microsoft", "MSFT")])
            self.assertEqual(repository.get_assets()["symbol"].tolist(), ["MSFT"])
            self.assertEqual(repository.get_assets("user_2")["symbol"].tolist(), ["NVDA"])

    def test_account_types_and_account_scoped_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "assets.db"
            repository = SQLiteAssetRepository(database_path)
            repository.initialize()
            default_account = repository.get_accounts().iloc[0]
            repository.save_assets([_row("Apple", "AAPL")])

            created_accounts = []
            for index, account_type in enumerate(ACCOUNT_TYPES):
                account = repository.create_account(f"Account {index}", account_type)
                self.assertEqual(account.account_type, account_type)
                created_accounts.append(account)

            brokerage = created_accounts[0]
            repository.save_assets(
                [_row("NVIDIA", "NVDA")],
                account_id=brokerage.id,
            )
            self.assertEqual(
                repository.get_assets(account_id=int(default_account["id"]))["symbol"].tolist(),
                ["AAPL"],
            )
            self.assertEqual(
                repository.get_assets(account_id=brokerage.id)["symbol"].tolist(),
                ["NVDA"],
            )

            repository.replace_all_assets(
                [_row("Microsoft", "MSFT")],
                account_id=brokerage.id,
            )
            self.assertEqual(
                repository.get_assets(account_id=int(default_account["id"]))["symbol"].tolist(),
                ["AAPL"],
            )
            self.assertEqual(
                repository.get_assets(account_id=brokerage.id)["symbol"].tolist(),
                ["MSFT"],
            )

            with self.assertRaises(ValueError):
                repository.create_account("Invalid", "Unsupported")
            with (
                self.assertRaises(sqlite3.IntegrityError),
                closing(sqlite3.connect(database_path)) as connection,
                connection,
            ):
                connection.execute(
                    """
                    INSERT INTO assets (
                        asset_type, asset_name, quantity, average_price,
                        current_price, currency
                    ) VALUES ('기타', 'Unowned', 1, 1, 1, 'KRW')
                    """
                )

    def test_excel_import_can_target_one_account(self) -> None:
        repository = Mock(spec=AssetRepository)
        repository.backup.return_value = Path("backup.db")

        result = import_asset_rows([_row()], repository=repository, account_id=7)

        self.assertTrue(result["success"])
        repository.replace_all_assets.assert_called_once_with(
            [_row()], user_id=DEFAULT_USER_ID, account_id=7
        )

    def test_excel_import_uses_explicit_user_during_fragment_context_reset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteAssetRepository(Path(directory) / "user.db")
            user_id = "google-user"
            repository.ensure_user(user_id, "user@example.com", "Asset User")
            account_id = int(repository.get_accounts(user_id).iloc[0]["id"])
            repository.save_assets(
                [_row("Apple", "AAPL")],
                user_id=user_id,
                account_id=account_id,
            )

            result = import_asset_rows(
                [_row("NVIDIA", "NVDA")],
                repository=repository,
                account_id=account_id,
                user_id=user_id,
            )

            self.assertTrue(result["success"])
            self.assertEqual(
                repository.get_assets(user_id, account_id)["symbol"].tolist(),
                ["NVDA"],
            )
            self.assertTrue(repository.get_assets(DEFAULT_USER_ID).empty)

    def test_preferences_are_persisted_and_validated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteAssetRepository(Path(directory) / "assets.db")
            defaults = repository.get_preferences()
            self.assertEqual(defaults.base_currency, "KRW")
            self.assertEqual(defaults.theme, "System")

            updated = repository.save_preferences("usd", "dark")
            self.assertEqual(updated.base_currency, "USD")
            self.assertEqual(updated.theme, "Dark")
            self.assertEqual(repository.get_preferences(), updated)

            with self.assertRaises(ValueError):
                repository.save_preferences("INVALID", "Light")
            with self.assertRaises(ValueError):
                repository.save_preferences("KRW", "Unknown")

    def test_backup_restore_is_validated_and_preserves_current_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteAssetRepository(Path(directory) / "assets.db")
            repository.save_assets([_row("Apple", "AAPL")])
            backup = repository.export_backup()

            repository.replace_all_assets([_row("NVIDIA", "NVDA")])
            repository.restore_backup(backup)
            self.assertEqual(repository.get_assets()["symbol"].tolist(), ["AAPL"])

            with self.assertRaises(ValueError):
                repository.restore_backup(b"not a sqlite database")
            self.assertEqual(repository.get_assets()["symbol"].tolist(), ["AAPL"])


if __name__ == "__main__":
    unittest.main()

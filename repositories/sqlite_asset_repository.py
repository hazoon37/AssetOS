from __future__ import annotations

import sqlite3
import json
import shutil
import tempfile
import threading
from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Sequence

import pandas as pd

from models.account import ACCOUNT_TYPES, Account
from models.preferences import (
    SUPPORTED_BASE_CURRENCIES,
    SUPPORTED_THEMES,
    UserPreferences,
)
from models.snapshot import PortfolioSnapshot
from models.user import User
from repositories.asset_repository import AssetRepository
from services.asset_classification import classify_asset
from services.user_context import get_current_user_id


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "assets.db"
DEFAULT_USER_ID = "default_user"
DEFAULT_USER_EMAIL = "default_user@assetos.local"
DEFAULT_ACCOUNT_NAME = "My Portfolio"
DEFAULT_ACCOUNT_TYPE = "Other"

METADATA_COLUMNS: dict[str, str] = {
    "asset_class": "TEXT DEFAULT 'ALTERNATIVE'",
    "country": "TEXT DEFAULT 'OTHER'",
    "exchange": "TEXT DEFAULT ''",
    "sector": "TEXT DEFAULT 'Unclassified'",
    "industry": "TEXT DEFAULT ''",
    "is_cash": "INTEGER NOT NULL DEFAULT 0",
    "is_leverage": "INTEGER NOT NULL DEFAULT 0",
    "is_inverse": "INTEGER NOT NULL DEFAULT 0",
    "leverage_multiple": "REAL NOT NULL DEFAULT 1",
    "data_source": "TEXT DEFAULT ''",
    "tags": "TEXT DEFAULT ''",
    "updated_at": "TIMESTAMP DEFAULT ''",
}
OWNERSHIP_COLUMNS: dict[str, str] = {
    "account_id": "INTEGER REFERENCES accounts(id)",
    "user_id": "TEXT REFERENCES users(id)",
}


class SQLiteAssetRepository(AssetRepository):
    """SQLite implementation preserving the existing AssetOS schema and SQL."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self._initialized = False
        self._initialization_lock = threading.RLock()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _existing_columns(connection: sqlite3.Connection) -> set[str]:
        return {row[1] for row in connection.execute("PRAGMA table_info(assets)").fetchall()}

    def _migrate(self, connection: sqlite3.Connection) -> None:
        existing = self._existing_columns(connection)
        for name, definition in {**METADATA_COLUMNS, **OWNERSHIP_COLUMNS}.items():
            if name not in existing:
                connection.execute(f"ALTER TABLE assets ADD COLUMN {name} {definition}")
        connection.commit()

    @staticmethod
    def _ensure_default_identity(connection: sqlite3.Connection) -> int:
        connection.execute(
            """
            INSERT OR IGNORE INTO users (id, email, name)
            VALUES (?, ?, ?)
            """,
            (DEFAULT_USER_ID, DEFAULT_USER_EMAIL, DEFAULT_USER_ID),
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO accounts (user_id, account_name, account_type)
            VALUES (?, ?, ?)
            """,
            (DEFAULT_USER_ID, DEFAULT_ACCOUNT_NAME, DEFAULT_ACCOUNT_TYPE),
        )
        connection.execute(
            """
            UPDATE accounts SET account_type=?
            WHERE user_id=? AND account_name=? AND account_type='portfolio'
            """,
            (DEFAULT_ACCOUNT_TYPE, DEFAULT_USER_ID, DEFAULT_ACCOUNT_NAME),
        )
        row = connection.execute(
            "SELECT id FROM accounts WHERE user_id=? AND account_name=?",
            (DEFAULT_USER_ID, DEFAULT_ACCOUNT_NAME),
        ).fetchone()
        if row is None:
            raise RuntimeError("기본 계정을 생성하지 못했습니다.")
        return int(row["id"])

    @staticmethod
    def _backfill_ownership(connection: sqlite3.Connection, account_id: int) -> None:
        connection.execute(
            "UPDATE assets SET account_id=? WHERE account_id IS NULL",
            (account_id,),
        )
        connection.execute(
            """
            UPDATE assets SET user_id=(
                SELECT accounts.user_id FROM accounts WHERE accounts.id=assets.account_id
            ) WHERE user_id IS NULL OR user_id=''
            """
        )
        connection.commit()

    def _backfill_metadata(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute("SELECT * FROM assets").fetchall()
        for row in rows:
            classification = classify_asset(
                asset_type=row["asset_type"],
                symbol=row["symbol"],
                currency=row["currency"],
                exchange=row["exchange"] if "exchange" in row.keys() else "",
                sector=row["sector"] if "sector" in row.keys() else "",
                industry=row["industry"] if "industry" in row.keys() else "",
            )
            connection.execute(
                """
                UPDATE assets SET
                    asset_class = ?, country = ?, exchange = ?, sector = ?, industry = ?,
                    is_cash = ?, is_leverage = ?, is_inverse = ?, leverage_multiple = ?,
                    data_source = CASE WHEN COALESCE(data_source, '') = '' THEN ? ELSE data_source END,
                    tags = CASE WHEN COALESCE(tags, '') = '' THEN ? ELSE tags END
                WHERE id = ?
                """,
                (
                    classification["asset_class"], classification["country"],
                    row["exchange"] or classification["exchange"],
                    row["sector"] if row["sector"] not in (None, "", "Unclassified") else classification["sector"],
                    row["industry"] or classification["industry"],
                    classification["is_cash"], classification["is_leverage"],
                    classification["is_inverse"], classification["leverage_multiple"],
                    classification["data_source"], classification["tags"], row["id"],
                ),
            )
        connection.commit()

    def initialize(self) -> None:
        if self._initialized:
            return
        with self._initialization_lock:
            if self._initialized:
                return
            with self._connect() as connection:
                connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    name TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
                )
                connection.execute(
                """
                CREATE TABLE IF NOT EXISTS accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    account_name TEXT NOT NULL,
                    account_type TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE (user_id, account_name)
                )
                """
                )
                connection.execute(
                """
                CREATE TABLE IF NOT EXISTS user_preferences (
                        user_id TEXT PRIMARY KEY,
                        base_currency TEXT NOT NULL DEFAULT 'KRW',
                        theme TEXT NOT NULL DEFAULT 'System',
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                    """
                )
                connection.execute(
                """
                CREATE TABLE IF NOT EXISTS assets (
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
                CREATE TABLE IF NOT EXISTS snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    account_id INTEGER,
                    snapshot_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    FOREIGN KEY (account_id) REFERENCES accounts(id)
                )
                """
                )
                self._migrate(connection)
                default_account_id = self._ensure_default_identity(connection)
                self._backfill_ownership(connection, default_account_id)
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_assets_account_id ON assets(account_id)"
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_assets_user_id ON assets(user_id)"
                )
                connection.execute(
                    "CREATE INDEX IF NOT EXISTS idx_snapshots_user_created ON snapshots(user_id, created_at DESC)"
                )
                connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS assets_require_account_insert
                BEFORE INSERT ON assets
                WHEN NEW.account_id IS NULL
                BEGIN
                    SELECT RAISE(ABORT, 'assets.account_id is required');
                END
                """
                )
                connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS assets_require_user_insert
                BEFORE INSERT ON assets
                WHEN NEW.user_id IS NULL OR NEW.user_id='' OR NOT EXISTS (
                    SELECT 1 FROM accounts
                    WHERE accounts.id=NEW.account_id AND accounts.user_id=NEW.user_id
                )
                BEGIN
                    SELECT RAISE(ABORT, 'assets user/account ownership mismatch');
                END
                """
                )
                connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS assets_require_user_update
                BEFORE UPDATE OF user_id, account_id ON assets
                WHEN NEW.user_id IS NULL OR NEW.user_id='' OR NOT EXISTS (
                    SELECT 1 FROM accounts
                    WHERE accounts.id=NEW.account_id AND accounts.user_id=NEW.user_id
                )
                BEGIN
                    SELECT RAISE(ABORT, 'assets user/account ownership mismatch');
                END
                """
                )
                connection.execute(
                """
                CREATE TRIGGER IF NOT EXISTS assets_require_account_update
                BEFORE UPDATE OF account_id ON assets
                WHEN NEW.account_id IS NULL
                BEGIN
                    SELECT RAISE(ABORT, 'assets.account_id is required');
                END
                """
                )
                self._backfill_metadata(connection)
            self._initialized = True

    @staticmethod
    def _user_id(user_id: str | None) -> str:
        return str(user_id or get_current_user_id())

    @classmethod
    def _default_account_id(cls, connection: sqlite3.Connection, user_id: str | None) -> int:
        owner = cls._user_id(user_id)
        user = connection.execute("SELECT id FROM users WHERE id=?", (owner,)).fetchone()
        if user is None:
            raise ValueError(f"사용자를 찾을 수 없습니다: {owner}")
        connection.execute(
            """
            INSERT OR IGNORE INTO accounts (user_id, account_name, account_type)
            VALUES (?, ?, ?)
            """,
            (owner, DEFAULT_ACCOUNT_NAME, DEFAULT_ACCOUNT_TYPE),
        )
        account = connection.execute(
            "SELECT id FROM accounts WHERE user_id=? AND account_name=?",
            (owner, DEFAULT_ACCOUNT_NAME),
        ).fetchone()
        if account is None:
            raise RuntimeError("기본 계정을 찾을 수 없습니다.")
        return int(account["id"])

    @classmethod
    def _target_account_id(
        cls,
        connection: sqlite3.Connection,
        user_id: str | None,
        account_id: int | None,
    ) -> int:
        if account_id is None:
            return cls._default_account_id(connection, user_id)
        owner = cls._user_id(user_id)
        account = connection.execute(
            "SELECT id FROM accounts WHERE id=? AND user_id=?",
            (int(account_id), owner),
        ).fetchone()
        if account is None:
            raise ValueError("선택한 계정을 찾을 수 없습니다.")
        return int(account["id"])

    def get_user(self, user_id: str | None = None) -> User | None:
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, email, name, created_at FROM users WHERE id=?",
                (self._user_id(user_id),),
            ).fetchone()
        return User(**dict(row)) if row else None

    def ensure_user(self, user_id: str, email: str, name: str) -> User:
        self.initialize()
        identity = str(user_id or "").strip()
        normalized_email = str(email or "").strip().lower()
        display_name = str(name or "").strip()
        if not identity or not normalized_email or not display_name:
            raise ValueError("사용자 ID, 이메일과 이름은 필수입니다.")
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO users (id, email, name) VALUES (?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET email=excluded.email, name=excluded.name
                """,
                (identity, normalized_email, display_name),
            )
            self._default_account_id(connection, identity)
        user = self.get_user(identity)
        if user is None:
            raise RuntimeError("사용자를 저장하지 못했습니다.")
        return user

    def migrate_user_scope(self, source_user_id: str, target_user_id: str) -> bool:
        """Move legacy/local data to another existing user without data loss."""
        self.initialize()
        source = self._user_id(source_user_id)
        target = self._user_id(target_user_id)
        if source == target:
            return False
        with self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                source_exists = connection.execute(
                    "SELECT 1 FROM users WHERE id=?", (source,)
                ).fetchone()
                target_exists = connection.execute(
                    "SELECT 1 FROM users WHERE id=?", (target,)
                ).fetchone()
                source_assets = connection.execute(
                    "SELECT COUNT(*) FROM assets WHERE user_id=?", (source,)
                ).fetchone()[0]
                if not source_exists or not target_exists or not source_assets:
                    connection.rollback()
                    return False

                target_accounts = {
                    str(row["account_name"]): int(row["id"])
                    for row in connection.execute(
                        "SELECT id, account_name FROM accounts WHERE user_id=?", (target,)
                    ).fetchall()
                }
                source_accounts = connection.execute(
                    "SELECT id, account_name, account_type FROM accounts WHERE user_id=?",
                    (source,),
                ).fetchall()
                account_map: dict[int, int] = {}
                for account in source_accounts:
                    name = str(account["account_name"])
                    if name not in target_accounts:
                        cursor = connection.execute(
                            "INSERT INTO accounts (user_id, account_name, account_type) VALUES (?, ?, ?)",
                            (target, name, str(account["account_type"])),
                        )
                        target_accounts[name] = int(cursor.lastrowid)
                    account_map[int(account["id"])] = target_accounts[name]

                for source_account, target_account in account_map.items():
                    connection.execute(
                        "UPDATE assets SET user_id=?, account_id=? WHERE user_id=? AND account_id=?",
                        (target, target_account, source, source_account),
                    )
                    connection.execute(
                        "UPDATE snapshots SET user_id=?, account_id=? WHERE user_id=? AND account_id=?",
                        (target, target_account, source, source_account),
                    )
                connection.execute(
                    "UPDATE snapshots SET user_id=? WHERE user_id=? AND account_id IS NULL",
                    (target, source),
                )
                preference = connection.execute(
                    "SELECT base_currency, theme FROM user_preferences WHERE user_id=?",
                    (source,),
                ).fetchone()
                if preference is not None:
                    connection.execute(
                        """
                        INSERT INTO user_preferences (user_id, base_currency, theme)
                        VALUES (?, ?, ?)
                        ON CONFLICT(user_id) DO UPDATE SET
                            base_currency=excluded.base_currency,
                            theme=excluded.theme,
                            updated_at=CURRENT_TIMESTAMP
                        """,
                        (target, preference["base_currency"], preference["theme"]),
                    )
                connection.commit()
                return True
            except Exception:
                connection.rollback()
                raise

    def get_accounts(self, user_id: str | None = None) -> pd.DataFrame:
        self.initialize()
        with self._connect() as connection:
            self._default_account_id(connection, user_id)
            return pd.read_sql_query(
                """
                SELECT id, user_id, account_name, account_type
                FROM accounts WHERE user_id=? ORDER BY id ASC
                """,
                connection,
                params=(self._user_id(user_id),),
            )

    def create_account(
        self,
        account_name: str,
        account_type: str,
        user_id: str | None = None,
    ) -> Account:
        self.initialize()
        name = str(account_name or "").strip()
        kind = str(account_type or "").strip()
        if not name:
            raise ValueError("계정 이름은 비어 있을 수 없습니다.")
        if kind not in ACCOUNT_TYPES:
            raise ValueError(f"지원하지 않는 계정 유형입니다: {kind}")
        owner = self._user_id(user_id)
        with self._connect() as connection:
            user = connection.execute("SELECT id FROM users WHERE id=?", (owner,)).fetchone()
            if user is None:
                raise ValueError(f"사용자를 찾을 수 없습니다: {owner}")
            try:
                cursor = connection.execute(
                    """
                    INSERT INTO accounts (user_id, account_name, account_type)
                    VALUES (?, ?, ?)
                    """,
                    (owner, name, kind),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError(f"이미 존재하는 계정 이름입니다: {name}") from exc
            return Account(int(cursor.lastrowid), owner, name, kind)

    def get_preferences(self, user_id: str | None = None) -> UserPreferences:
        self.initialize()
        owner = self._user_id(user_id)
        with self._connect() as connection:
            user = connection.execute("SELECT id FROM users WHERE id=?", (owner,)).fetchone()
            if user is None:
                raise ValueError(f"사용자를 찾을 수 없습니다: {owner}")
            connection.execute(
                """
                INSERT OR IGNORE INTO user_preferences (user_id, base_currency, theme)
                VALUES (?, 'KRW', 'System')
                """,
                (owner,),
            )
            row = connection.execute(
                """
                SELECT user_id, base_currency, theme, updated_at
                FROM user_preferences WHERE user_id=?
                """,
                (owner,),
            ).fetchone()
        if row is None:
            raise RuntimeError("사용자 환경설정을 생성하지 못했습니다.")
        return UserPreferences(**dict(row))

    def save_preferences(
        self,
        base_currency: str,
        theme: str,
        user_id: str | None = None,
    ) -> UserPreferences:
        currency = str(base_currency or "").strip().upper()
        selected_theme = str(theme or "").strip().title()
        if currency not in SUPPORTED_BASE_CURRENCIES:
            raise ValueError(f"지원하지 않는 기준통화입니다: {currency}")
        if selected_theme not in SUPPORTED_THEMES:
            raise ValueError(f"지원하지 않는 테마입니다: {selected_theme}")
        owner = self._user_id(user_id)
        self.get_preferences(owner)
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE user_preferences
                SET base_currency=?, theme=?, updated_at=CURRENT_TIMESTAMP
                WHERE user_id=?
                """,
                (currency, selected_theme, owner),
            )
        return self.get_preferences(owner)

    def get_assets(
        self,
        user_id: str | None = None,
        account_id: int | None = None,
    ) -> pd.DataFrame:
        self.initialize()
        with self._connect() as connection:
            params: tuple[Any, ...] = (self._user_id(user_id),)
            account_filter = ""
            if account_id is not None:
                account_filter = " AND accounts.id=?"
                params += (int(account_id),)
            return pd.read_sql_query(
                f"""
                SELECT assets.* FROM assets
                JOIN accounts ON accounts.id = assets.account_id
                WHERE assets.user_id=? AND accounts.user_id=assets.user_id{account_filter}
                ORDER BY assets.id ASC
                """,
                connection,
                params=params,
            )

    @staticmethod
    def _merged_values(row: dict[str, Any]) -> dict[str, Any]:
        inferred = classify_asset(
            asset_type=str(row.get("asset_type") or ""),
            symbol=str(row.get("symbol") or ""),
            currency=str(row.get("currency") or "KRW"),
            exchange=str(row.get("exchange") or ""),
            sector=str(row.get("sector") or ""),
            industry=str(row.get("industry") or ""),
        )
        values = dict(inferred)
        for key in (
            "asset_class", "country", "exchange", "sector", "industry",
            "is_cash", "is_leverage", "is_inverse", "leverage_multiple",
            "data_source", "tags",
        ):
            value = row.get(key)
            if value is None or (isinstance(value, str) and not value.strip()):
                continue
            values[key] = value
        return values

    @classmethod
    def _insert_row(
        cls,
        connection: sqlite3.Connection,
        row: dict[str, Any],
        account_id: int,
        user_id: str,
    ) -> None:
        values = cls._merged_values(row)
        connection.execute(
            """
            INSERT INTO assets (
                asset_type, asset_name, symbol, quantity, average_price,
                current_price, currency, memo, account_id, user_id, asset_class, country,
                exchange, sector, industry, is_cash, is_leverage,
                is_inverse, leverage_multiple, data_source, tags, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                str(row.get("asset_type") or ""), str(row.get("asset_name") or ""),
                str(row.get("symbol") or "").upper(), float(row.get("quantity") or 0),
                float(row.get("average_price") or 0), float(row.get("current_price") or 0),
                str(row.get("currency") or "KRW").upper(), str(row.get("memo") or ""),
                account_id, user_id,
                str(values.get("asset_class") or "ALTERNATIVE"), str(values.get("country") or "OTHER"),
                str(values.get("exchange") or ""), str(values.get("sector") or "Unclassified"),
                str(values.get("industry") or ""), int(bool(values.get("is_cash"))),
                int(bool(values.get("is_leverage"))), int(bool(values.get("is_inverse"))),
                float(values.get("leverage_multiple") or 1),
                str(values.get("data_source") or "Excel Import"), str(values.get("tags") or ""),
            ),
        )

    def save_assets(
        self,
        rows: Sequence[dict[str, Any]],
        user_id: str | None = None,
        account_id: int | None = None,
    ) -> None:
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute("BEGIN")
                target_account_id = self._target_account_id(connection, user_id, account_id)
                owner = self._user_id(user_id)
                for row in rows:
                    self._insert_row(connection, dict(row), target_account_id, owner)
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def replace_all_assets(
        self,
        rows: Sequence[dict[str, Any]],
        user_id: str | None = None,
        account_id: int | None = None,
    ) -> None:
        self.initialize()
        with self._connect() as connection:
            try:
                connection.execute("BEGIN")
                owner = self._user_id(user_id)
                target_account_id = self._target_account_id(connection, owner, account_id)
                if account_id is None:
                    connection.execute("DELETE FROM assets WHERE user_id=?", (owner,))
                else:
                    connection.execute(
                        "DELETE FROM assets WHERE user_id=? AND account_id=?",
                        (owner, target_account_id),
                    )
                for row in rows:
                    self._insert_row(connection, dict(row), target_account_id, owner)
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def backup(self) -> Path | None:
        if not self.db_path.exists():
            return None
        backup_dir = self.db_path.parent / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = backup_dir / f"assetos_backup_{timestamp}.db"
        with self._connect() as source, closing(sqlite3.connect(backup_path)) as destination:
            source.backup(destination)
        return backup_path

    def export_backup(self) -> bytes:
        self.initialize()
        temporary = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        temporary_path = Path(temporary.name)
        temporary.close()
        try:
            with self._connect() as source, closing(sqlite3.connect(temporary_path)) as destination:
                source.backup(destination)
            return temporary_path.read_bytes()
        finally:
            temporary_path.unlink(missing_ok=True)

    @staticmethod
    def _validate_backup(path: Path) -> None:
        try:
            with closing(sqlite3.connect(path)) as connection:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    ).fetchall()
                }
        except sqlite3.DatabaseError as exc:
            raise ValueError("올바른 AssetOS SQLite 백업 파일이 아닙니다.") from exc
        if not integrity or integrity[0] != "ok" or "assets" not in tables:
            raise ValueError("손상되었거나 AssetOS 자산 테이블이 없는 백업입니다.")

    def restore_backup(self, backup: bytes) -> None:
        if not backup:
            raise ValueError("복원할 백업 파일이 비어 있습니다.")
        if len(backup) > 50 * 1024 * 1024:
            raise ValueError("백업 파일은 50MB 이하여야 합니다.")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._initialization_lock:
            temporary = tempfile.NamedTemporaryFile(
                suffix=".db",
                dir=self.db_path.parent,
                delete=False,
            )
            temporary_path = Path(temporary.name)
            try:
                temporary.write(backup)
                temporary.flush()
                temporary.close()
                self._validate_backup(temporary_path)
                safety_backup = self.backup()
                temporary_path.replace(self.db_path)
                self._initialized = False
                try:
                    self.initialize()
                except Exception:
                    if safety_backup is not None:
                        shutil.copy2(safety_backup, self.db_path)
                        self._initialized = False
                        self.initialize()
                    raise
            finally:
                if not temporary.closed:
                    temporary.close()
                temporary_path.unlink(missing_ok=True)

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
        row = {
            "asset_type": asset_type, "asset_name": asset_name, "symbol": symbol,
            "quantity": quantity, "average_price": average_price,
            "current_price": current_price, "currency": currency, "memo": memo,
            **(metadata or {}),
        }
        self.save_assets([row], user_id=user_id, account_id=account_id)

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
        self.initialize()
        inferred = classify_asset(asset_type=asset_type, symbol=symbol, currency=currency)
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE assets SET
                    asset_type=?, asset_name=?, symbol=?, quantity=?, average_price=?, current_price=?,
                    currency=?, memo=?, asset_class=?, country=?, is_cash=?, is_leverage=?, is_inverse=?,
                    leverage_multiple=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND user_id=?
                """,
                (
                    asset_type, asset_name, symbol, float(quantity), float(average_price),
                    float(current_price), currency, memo, inferred["asset_class"], inferred["country"],
                    inferred["is_cash"], inferred["is_leverage"], inferred["is_inverse"],
                    inferred["leverage_multiple"], int(asset_id), self._user_id(user_id),
                ),
            )

    def update_current_price(
        self,
        asset_id: int,
        current_price: float,
        user_id: str | None = None,
    ) -> None:
        self.initialize()
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE assets SET current_price=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND user_id=?
                """,
                (float(current_price), int(asset_id), self._user_id(user_id)),
            )

    def delete_asset(self, asset_id: int, user_id: str | None = None) -> None:
        self.initialize()
        with self._connect() as connection:
            connection.execute(
                """
                DELETE FROM assets WHERE id=? AND user_id=?
                """,
                (int(asset_id), self._user_id(user_id)),
            )

    def delete_assets(
        self,
        asset_ids: Sequence[int],
        user_id: str | None = None,
    ) -> int:
        self.initialize()
        identifiers = sorted({int(asset_id) for asset_id in asset_ids})
        if not identifiers:
            return 0
        placeholders = ",".join("?" for _ in identifiers)
        with self._connect() as connection:
            cursor = connection.execute(
                f"""
                DELETE FROM assets
                WHERE id IN ({placeholders}) AND user_id=?
                """,
                (*identifiers, self._user_id(user_id)),
            )
        return int(cursor.rowcount)

    def save_snapshot(
        self,
        snapshot_data: dict[str, Any],
        user_id: str | None = None,
        account_id: int | None = None,
    ) -> PortfolioSnapshot:
        self.initialize()
        owner = self._user_id(user_id)
        serialized = json.dumps(snapshot_data, ensure_ascii=False, separators=(",", ":"))
        with self._connect() as connection:
            target_account = (
                self._target_account_id(connection, owner, account_id)
                if account_id is not None else None
            )
            cursor = connection.execute(
                "INSERT INTO snapshots (user_id, account_id, snapshot_data) VALUES (?, ?, ?)",
                (owner, target_account, serialized),
            )
            row = connection.execute(
                """
                SELECT id, user_id, account_id, snapshot_data, created_at
                FROM snapshots WHERE id=? AND user_id=?
                """,
                (int(cursor.lastrowid), owner),
            ).fetchone()
        if row is None:
            raise RuntimeError("포트폴리오 스냅샷을 저장하지 못했습니다.")
        values = dict(row)
        values["snapshot_data"] = json.loads(values["snapshot_data"])
        return PortfolioSnapshot(**values)

    def get_snapshots(
        self,
        user_id: str | None = None,
        account_id: int | None = None,
        limit: int = 100,
    ) -> list[PortfolioSnapshot]:
        self.initialize()
        owner = self._user_id(user_id)
        bounded_limit = max(1, min(int(limit), 1000))
        params: list[Any] = [owner]
        account_filter = ""
        if account_id is not None:
            account_filter = " AND account_id=?"
            params.append(int(account_id))
        params.append(bounded_limit)
        with self._connect() as connection:
            rows = connection.execute(
                f"""
                SELECT id, user_id, account_id, snapshot_data, created_at
                FROM snapshots
                WHERE user_id=?{account_filter}
                ORDER BY created_at DESC, id DESC LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [
            PortfolioSnapshot(**{**dict(row), "snapshot_data": json.loads(row["snapshot_data"])})
            for row in rows
        ]

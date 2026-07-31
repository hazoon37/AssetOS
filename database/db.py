from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

from services.asset_classification import classify_asset

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "assets.db"

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


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    return connection


def _existing_columns(connection: sqlite3.Connection) -> set[str]:
    return {row[1] for row in connection.execute("PRAGMA table_info(assets)").fetchall()}


def _migrate_assets_table(connection: sqlite3.Connection) -> None:
    existing = _existing_columns(connection)
    for name, definition in METADATA_COLUMNS.items():
        if name not in existing:
            connection.execute(f"ALTER TABLE assets ADD COLUMN {name} {definition}")
    connection.commit()


def _backfill_metadata(connection: sqlite3.Connection) -> None:
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


def create_tables() -> None:
    with get_connection() as connection:
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
        _migrate_assets_table(connection)
        _backfill_metadata(connection)


def add_asset(
    asset_type: str,
    asset_name: str,
    symbol: str,
    quantity: float,
    average_price: float,
    current_price: float,
    currency: str,
    memo: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    create_tables()
    metadata = metadata or {}
    inferred = classify_asset(
        asset_type=asset_type,
        symbol=symbol,
        currency=currency,
        exchange=str(metadata.get("exchange") or ""),
        sector=str(metadata.get("sector") or ""),
        industry=str(metadata.get("industry") or ""),
    )
    values = dict(inferred)
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        values[key] = value
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO assets (
                asset_type, asset_name, symbol, quantity, average_price, current_price,
                currency, memo, asset_class, country, exchange, sector, industry,
                is_cash, is_leverage, is_inverse, leverage_multiple, data_source, tags, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (
                asset_type, asset_name, symbol, float(quantity), float(average_price),
                float(current_price), currency, memo, values["asset_class"], values["country"],
                values["exchange"], values["sector"], values["industry"], int(values["is_cash"]),
                int(values["is_leverage"]), int(values["is_inverse"]), float(values["leverage_multiple"]),
                str(values.get("data_source") or ""), str(values.get("tags") or ""),
            ),
        )


def get_assets() -> pd.DataFrame:
    create_tables()
    with get_connection() as connection:
        return pd.read_sql_query("SELECT * FROM assets ORDER BY id ASC", connection)


def update_asset(
    asset_id: int,
    asset_type: str,
    asset_name: str,
    symbol: str,
    quantity: float,
    average_price: float,
    current_price: float,
    currency: str,
    memo: str,
) -> None:
    create_tables()
    inferred = classify_asset(asset_type=asset_type, symbol=symbol, currency=currency)
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE assets SET
                asset_type=?, asset_name=?, symbol=?, quantity=?, average_price=?, current_price=?,
                currency=?, memo=?, asset_class=?, country=?, is_cash=?, is_leverage=?, is_inverse=?,
                leverage_multiple=?, updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                asset_type, asset_name, symbol, float(quantity), float(average_price),
                float(current_price), currency, memo, inferred["asset_class"], inferred["country"],
                inferred["is_cash"], inferred["is_leverage"], inferred["is_inverse"],
                inferred["leverage_multiple"], int(asset_id),
            ),
        )


def update_asset_current_price(asset_id: int, current_price: float) -> None:
    with get_connection() as connection:
        connection.execute(
            "UPDATE assets SET current_price=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (float(current_price), int(asset_id)),
        )


def delete_asset(asset_id: int) -> None:
    with get_connection() as connection:
        connection.execute("DELETE FROM assets WHERE id=?", (int(asset_id),))


def replace_all_assets(rows: list[dict[str, Any]]) -> None:
    """Excel 마스터 데이터로 자산 테이블 전체를 원자적으로 교체합니다."""
    create_tables()

    with get_connection() as connection:
        try:
            connection.execute("BEGIN")
            connection.execute("DELETE FROM assets")

            for row in rows:
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
                    if value is None:
                        continue
                    if isinstance(value, str) and not value.strip():
                        continue
                    values[key] = value

                connection.execute(
                    """
                    INSERT INTO assets (
                        asset_type, asset_name, symbol, quantity, average_price,
                        current_price, currency, memo, asset_class, country,
                        exchange, sector, industry, is_cash, is_leverage,
                        is_inverse, leverage_multiple, data_source, tags, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (
                        str(row.get("asset_type") or ""),
                        str(row.get("asset_name") or ""),
                        str(row.get("symbol") or "").upper(),
                        float(row.get("quantity") or 0),
                        float(row.get("average_price") or 0),
                        float(row.get("current_price") or 0),
                        str(row.get("currency") or "KRW").upper(),
                        str(row.get("memo") or ""),
                        str(values.get("asset_class") or "ALTERNATIVE"),
                        str(values.get("country") or "OTHER"),
                        str(values.get("exchange") or ""),
                        str(values.get("sector") or "Unclassified"),
                        str(values.get("industry") or ""),
                        int(bool(values.get("is_cash"))),
                        int(bool(values.get("is_leverage"))),
                        int(bool(values.get("is_inverse"))),
                        float(values.get("leverage_multiple") or 1),
                        str(values.get("data_source") or "Excel Import"),
                        str(values.get("tags") or ""),
                    ),
                )

            connection.execute("DELETE FROM sqlite_sequence WHERE name='assets'")
            connection.commit()
        except Exception:
            connection.rollback()
            raise

from __future__ import annotations

from typing import Any

import pandas as pd

from models.account import Account
from repositories import get_asset_repository
from repositories.sqlite_asset_repository import DEFAULT_DB_PATH


# Backward-compatible path constant for callers outside the repository layer.
DB_PATH = DEFAULT_DB_PATH


def create_tables() -> None:
    get_asset_repository().initialize()


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
    account_id: int | None = None,
) -> None:
    get_asset_repository().add_asset(
        asset_type=asset_type,
        asset_name=asset_name,
        symbol=symbol,
        quantity=quantity,
        average_price=average_price,
        current_price=current_price,
        currency=currency,
        memo=memo,
        metadata=metadata,
        account_id=account_id,
    )


def get_assets(
    user_id: str | None = None,
    account_id: int | None = None,
) -> pd.DataFrame:
    return get_asset_repository().get_assets(user_id, account_id)


def get_accounts(user_id: str | None = None) -> pd.DataFrame:
    return get_asset_repository().get_accounts(user_id)


def create_account(
    account_name: str,
    account_type: str,
    user_id: str | None = None,
) -> Account:
    return get_asset_repository().create_account(account_name, account_type, user_id)


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
    get_asset_repository().update_asset(
        asset_id=asset_id,
        asset_type=asset_type,
        asset_name=asset_name,
        symbol=symbol,
        quantity=quantity,
        average_price=average_price,
        current_price=current_price,
        currency=currency,
        memo=memo,
    )


def update_asset_current_price(asset_id: int, current_price: float) -> None:
    get_asset_repository().update_current_price(asset_id, current_price)


def delete_asset(asset_id: int) -> None:
    get_asset_repository().delete_asset(asset_id)


def delete_assets(asset_ids: list[int]) -> int:
    return get_asset_repository().delete_assets(asset_ids)


def replace_all_assets(
    rows: list[dict[str, Any]],
    account_id: int | None = None,
) -> None:
    get_asset_repository().replace_all_assets(rows, account_id=account_id)

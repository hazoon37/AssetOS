from __future__ import annotations

from models.account import Account
from models.preferences import UserPreferences
from repositories import get_asset_repository


def get_user_preferences() -> UserPreferences:
    return get_asset_repository().get_preferences()


def update_user_preferences(base_currency: str, theme: str) -> UserPreferences:
    return get_asset_repository().save_preferences(base_currency, theme)


def create_investment_account(account_name: str, account_type: str) -> Account:
    return get_asset_repository().create_account(account_name, account_type)


def export_database_backup() -> bytes:
    return get_asset_repository().export_backup()


def restore_database_backup(backup: bytes) -> None:
    get_asset_repository().restore_backup(backup)

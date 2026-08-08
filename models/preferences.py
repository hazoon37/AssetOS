from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_BASE_CURRENCIES = ("KRW", "USD", "JPY", "EUR", "GBP", "HKD")
SUPPORTED_THEMES = ("System", "Light", "Dark")


@dataclass(frozen=True)
class UserPreferences:
    user_id: str
    base_currency: str = "KRW"
    theme: str = "System"
    updated_at: str = ""

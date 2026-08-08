from __future__ import annotations

from dataclasses import dataclass


ACCOUNT_TYPES = (
    "Brokerage",
    "ISA",
    "Pension",
    "Crypto",
    "Bank",
    "Cash",
    "Real Estate",
    "Insurance",
    "Other",
)


@dataclass(frozen=True)
class Account:
    id: int
    user_id: str
    account_name: str
    account_type: str

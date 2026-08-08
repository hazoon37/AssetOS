from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Immutable user-owned portfolio state captured at one point in time."""

    id: int
    user_id: str
    account_id: int | None
    snapshot_data: dict[str, Any]
    created_at: datetime | str

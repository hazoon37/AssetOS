from __future__ import annotations

from typing import Any

from models.snapshot import PortfolioSnapshot
from repositories import get_asset_repository
from repositories.asset_repository import AssetRepository
from services.user_context import get_current_user_id


def save_portfolio_snapshot(
    portfolio: dict[str, Any],
    *,
    user_id: str | None = None,
    account_id: int | None = None,
    repository: AssetRepository | None = None,
) -> PortfolioSnapshot:
    """Persist structured analysis without coupling callers to SQLite."""
    owner = str(user_id or get_current_user_id())
    return (repository or get_asset_repository()).save_snapshot(
        portfolio,
        user_id=owner,
        account_id=account_id,
    )


def get_portfolio_snapshots(
    *,
    user_id: str | None = None,
    account_id: int | None = None,
    limit: int = 100,
    repository: AssetRepository | None = None,
) -> list[PortfolioSnapshot]:
    """Read snapshots within the authenticated user's repository scope."""
    owner = str(user_id or get_current_user_id())
    return (repository or get_asset_repository()).get_snapshots(
        user_id=owner,
        account_id=account_id,
        limit=limit,
    )

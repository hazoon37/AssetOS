from __future__ import annotations

from database.db import delete_asset, delete_assets, update_asset


def _clear_portfolio_cache() -> None:
    """Streamlit 실행 환경에서 포트폴리오 분석 캐시를 초기화합니다."""
    from services.portfolio_service import clear_portfolio_analysis_cache

    clear_portfolio_analysis_cache()


def save_asset_changes(
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
) -> None:
    update_asset(
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
    _clear_portfolio_cache()


def remove_asset(asset_id: int) -> None:
    delete_asset(asset_id)
    _clear_portfolio_cache()


def remove_assets(asset_ids: list[int]) -> int:
    """Delete a user-confirmed collection in one repository transaction."""
    deleted = delete_assets(asset_ids)
    _clear_portfolio_cache()
    return deleted

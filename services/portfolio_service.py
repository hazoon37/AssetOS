from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from repositories import get_asset_repository
from repositories.asset_repository import AssetRepository
from services.asset_resolver import (
    enrich_asset_with_resolver,
    is_resolvable_asset_type,
    resolve_asset,
)
from services.market_price_service import get_market_price
from services.exchange_rate_service import get_exchange_rates_to_krw
from services.portfolio_analyzer import analyze_portfolio
from services.user_context import get_current_user_id


def _float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return default if pd.isna(number) else number
    except (TypeError, ValueError):
        return default


def is_valid_current_price(value: Any) -> bool:
    """Return whether a price is finite and strictly positive."""
    try:
        number = float(value)
        return not pd.isna(number) and number > 0
    except (TypeError, ValueError):
        return False


def has_extreme_price_ratio(row: dict[str, Any]) -> bool:
    """Flag likely quote-unit/currency corruption without rejecting real losses."""
    average = _float(row.get("average_price"))
    current = _float(row.get("current_price"))
    if average <= 0 or current <= 0:
        return False
    ratio = current / average
    return ratio < 0.01 or ratio > 100.0


def reconcile_asset_identity(row: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Correct a stored ticker only when its asset name has one exact local match."""
    reconciled = dict(row)
    asset_type = str(reconciled.get("asset_type") or "").strip()
    if not is_resolvable_asset_type(asset_type):
        return reconciled, False
    asset_name = str(reconciled.get("asset_name") or reconciled.get("name") or "").strip()
    if not asset_name:
        return reconciled, False
    resolution = resolve_asset(
        asset_name, asset_type=asset_type, include_external=False
    )
    if resolution.status != "exact" or resolution.asset is None:
        return reconciled, False
    resolved = resolution.asset
    current_ticker = str(reconciled.get("symbol") or "").strip().upper()
    ticker_changed = bool(current_ticker) and current_ticker != resolved.ticker.upper()
    stored_currency = str(reconciled.get("currency") or "").strip().upper()
    currency_changed = (
        resolved.asset_type != "코인"
        and bool(resolved.currency)
        and stored_currency != resolved.currency.upper()
    )
    if not current_ticker or not (ticker_changed or currency_changed):
        return reconciled, False
    reconciled.update({
        "symbol": resolved.ticker,
        "asset_type": resolved.asset_type or reconciled.get("asset_type"),
        "currency": (
            reconciled.get("currency") or resolved.currency
            if resolved.asset_type == "코인"
            else resolved.currency or reconciled.get("currency")
        ),
        "country": resolved.country,
        "exchange": resolved.exchange,
        "sector": resolved.sector,
        "industry": resolved.industry,
    })
    return reconciled, True


def refresh_invalid_price(
    row: dict[str, Any], *, force: bool = False
) -> tuple[dict[str, Any], str | None]:
    """Re-fetch an invalid market price before portfolio calculations."""
    refreshed = dict(row)
    if not force and is_valid_current_price(refreshed.get("current_price")):
        return refreshed, None
    symbol = str(refreshed.get("symbol") or "").strip()
    asset_type = str(refreshed.get("asset_type") or "").strip()
    currency = str(refreshed.get("currency") or "KRW").upper()
    if not is_resolvable_asset_type(asset_type):
        return refreshed, None
    if not symbol:
        return refreshed, "Price Invalid: ticker 또는 자산 유형이 없어 재조회하지 못했습니다."
    result = get_market_price(asset_type=asset_type, symbol=symbol, currency=currency)
    if result.get("success") and is_valid_current_price(result.get("price")):
        refreshed["current_price"] = float(result["price"])
        return refreshed, None
    return refreshed, f"Price Invalid: {result.get('message') or '시세를 재조회하지 못했습니다.'}"


def calculate_asset_values(
    quantity: Any,
    average_price: Any,
    current_price: Any,
    currency: str,
    rates: dict[str, float],
) -> dict[str, float] | None:
    """Calculate one holding consistently for Dashboard, AI, and reports."""
    normalized_currency = str(currency or "KRW").upper()
    rate = 1.0 if normalized_currency == "KRW" else rates.get(normalized_currency)
    if rate is None:
        return None
    units = _float(quantity)
    average = _float(average_price)
    current = _float(current_price)
    cost = units * average * float(rate)
    value = units * current * float(rate)
    profit = value - cost
    return {
        "quantity": units,
        "average_price": average,
        "current_price": current,
        "exchange_rate": float(rate),
        "cost_value_krw": cost,
        "value_krw": value,
        "profit_loss_krw": profit,
        "return_rate_percent": profit / cost * 100 if cost > 0 else 0.0,
    }


def _convert_row(row: pd.Series, rates: dict[str, float]) -> tuple[dict[str, Any] | None, str | None]:
    currency = str(row.get("currency") or "KRW").upper()
    name = str(row.get("asset_name") or row.get("symbol") or f"자산 {row.get('id')}")
    values = calculate_asset_values(
        row.get("quantity"), row.get("average_price"), row.get("current_price"), currency, rates
    )
    if values is None:
        return None, f"{name}: {currency}/KRW 환율을 가져오지 못해 분석에서 제외했습니다."
    if values["value_krw"] <= 0:
        return None, f"{name}: 평가금액이 0 이하라 분석에서 제외했습니다."
    return {
        "id": int(_float(row.get("id"))),
        "account_id": int(_float(row.get("account_id"))),
        "account_name": str(row.get("account_name") or "Unclassified"),
        "name": name,
        "symbol": str(row.get("symbol") or "").upper(),
        "asset_type": str(row.get("asset_type") or ""),
        "asset_class": str(row.get("asset_class") or "ALTERNATIVE"),
        "country": str(row.get("country") or "OTHER"),
        "currency": currency,
        "exchange": str(row.get("exchange") or ""),
        "sector": str(row.get("sector") or "Unclassified"),
        "industry": str(row.get("industry") or ""),
        "quantity": values["quantity"],
        "average_price": values["average_price"],
        "current_price": values["current_price"],
        "exchange_rate": values["exchange_rate"],
        "cost_value_krw": values["cost_value_krw"],
        "value_krw": values["value_krw"],
        "profit_loss_krw": values["profit_loss_krw"],
        "is_cash": bool(row.get("is_cash")),
        "is_leverage": bool(row.get("is_leverage")),
        "is_inverse": bool(row.get("is_inverse")),
        "leverage_multiple": _float(row.get("leverage_multiple"), 1.0),
        "tags": str(row.get("tags") or ""),
        "provider": str(row.get("provider") or ""),
        "theme": str(row.get("theme") or ""),
        "is_dividend": bool(row.get("is_dividend")),
        "is_leveraged": bool(row.get("is_leveraged") or row.get("is_leverage")),
    }, None


def _build_portfolio_analysis(
    repository: AssetRepository,
    exclude_real_estate: bool,
    user_id: str,
    account_id: int | None = None,
) -> dict[str, Any]:
    assets_df = repository.get_assets(user_id, account_id)
    accounts = repository.get_accounts(user_id)
    account_names = (
        accounts.set_index("id")["account_name"].to_dict()
        if isinstance(accounts, pd.DataFrame) and not accounts.empty
        else {}
    )
    exchange = get_exchange_rates_to_krw()
    rates = exchange.get("rates") or {"KRW": 1.0}
    records = assets_df.to_dict(orient="records")
    for record in records:
        record["account_name"] = account_names.get(
            int(record.get("account_id") or 0), "Unclassified"
        )
        enriched = enrich_asset_with_resolver(record)
        reconciled, ticker_changed = reconcile_asset_identity(enriched)
        price_suspect = has_extreme_price_ratio(reconciled)
        refreshed, price_warning = refresh_invalid_price(
            reconciled, force=ticker_changed or price_suspect
        )
        if (
            is_valid_current_price(refreshed.get("current_price"))
            and (
                ticker_changed or price_suspect
                or not is_valid_current_price(record.get("current_price"))
            )
        ):
            if ticker_changed:
                repository.update_asset(
                    asset_id=int(record.get("id") or 0),
                    asset_type=str(refreshed.get("asset_type") or ""),
                    asset_name=str(record.get("asset_name") or ""),
                    symbol=str(refreshed.get("symbol") or ""),
                    quantity=_float(record.get("quantity")),
                    average_price=_float(record.get("average_price")),
                    current_price=float(refreshed["current_price"]),
                    currency=str(refreshed.get("currency") or "KRW"),
                    memo=str(record.get("memo") or ""),
                    user_id=user_id,
                )
            else:
                repository.update_current_price(
                    int(record.get("id") or 0), float(refreshed["current_price"]), user_id
                )
        record.update(refreshed)
        if price_warning:
            record["_price_warning"] = price_warning
    result = analyze_asset_rows(records, rates, exclude_real_estate=exclude_real_estate)
    conversion_warnings = list(result.pop("conversion_warnings", []))
    result.update({
        "exchange_rate_date": exchange.get("date"),
        "exchange_rate_success": bool(exchange.get("success")),
        "source_asset_count": int(len(assets_df)),
        "exclude_real_estate": bool(exclude_real_estate),
        "user_id": user_id,
        "account_id": account_id,
    })
    result["warnings"] = list(dict.fromkeys(conversion_warnings + result.get("warnings", [])))
    if exchange.get("message"):
        result["warnings"].insert(0, str(exchange["message"]))
    return result


def analyze_asset_rows(
    rows: list[dict[str, Any]],
    exchange_rates: dict[str, float],
    *,
    exclude_real_estate: bool = False,
) -> dict[str, Any]:
    """Analyze in-memory asset rows without reading or mutating a repository."""
    assets: list[dict[str, Any]] = []
    conversion_warnings: list[str] = []
    for index, source in enumerate(rows, start=1):
        normalized = dict(source)
        normalized.setdefault("id", index)
        normalized.setdefault("account_name", "Quick Analysis")
        normalized = enrich_asset_with_resolver(normalized)
        normalized, ticker_changed = reconcile_asset_identity(normalized)
        existing_price_warning = str(normalized.pop("_price_warning", ""))
        normalized, price_warning = refresh_invalid_price(
            normalized, force=ticker_changed or has_extreme_price_ratio(normalized)
        )
        price_warning = price_warning or existing_price_warning or None
        row = pd.Series(normalized)
        if exclude_real_estate:
            asset_type = str(row.get("asset_type") or "")
            asset_class = str(row.get("asset_class") or "")
            if asset_type == "부동산" or asset_class == "REAL_ESTATE":
                continue

        asset, warning = _convert_row(row, exchange_rates)
        if asset:
            assets.append(asset)
        if warning:
            conversion_warnings.append(warning)
        if price_warning:
            conversion_warnings.append(
                f"{row.get('asset_name') or row.get('symbol')}: {price_warning}"
            )
    result = analyze_portfolio(assets)
    result.update({
        "source_asset_count": len(rows),
        "analyzed_asset_count": len(assets),
        "exclude_real_estate": bool(exclude_real_estate),
        "conversion_warnings": conversion_warnings,
    })
    return result


def _get_cached_portfolio_analysis(
    user_id: str,
    exclude_real_estate: bool = False,
    account_id: int | None = None,
) -> dict[str, Any]:
    return _build_portfolio_analysis(
        get_asset_repository(), exclude_real_estate, user_id, account_id
    )


def get_portfolio_analysis(
    exclude_real_estate: bool = False,
    repository: AssetRepository | None = None,
    user_id: str | None = None,
    account_id: int | None = None,
) -> dict[str, Any]:
    """Analyze assets from an injected repository or the cached default."""
    owner = str(user_id or get_current_user_id())
    if repository is not None:
        return _build_portfolio_analysis(repository, exclude_real_estate, owner, account_id)
    return _get_cached_portfolio_analysis(owner, exclude_real_estate, account_id)


def clear_portfolio_analysis_cache() -> None:
    clear = getattr(_get_cached_portfolio_analysis, "clear", None)
    if clear is not None:
        clear()

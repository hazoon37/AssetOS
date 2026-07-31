from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from database.db import create_tables, get_assets
from services.exchange_rate_service import get_exchange_rates_to_krw
from services.portfolio_analyzer import analyze_portfolio


def _float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return default if pd.isna(number) else number
    except (TypeError, ValueError):
        return default


def _convert_row(row: pd.Series, rates: dict[str, float]) -> tuple[dict[str, Any] | None, str | None]:
    currency = str(row.get("currency") or "KRW").upper()
    rate = 1.0 if currency == "KRW" else rates.get(currency)
    name = str(row.get("asset_name") or row.get("symbol") or f"자산 {row.get('id')}")
    if rate is None:
        return None, f"{name}: {currency}/KRW 환율을 가져오지 못해 분석에서 제외했습니다."
    quantity = _float(row.get("quantity"))
    average = _float(row.get("average_price"))
    current = _float(row.get("current_price"))
    value = quantity * current * rate
    cost = quantity * average * rate
    if value <= 0:
        return None, f"{name}: 평가금액이 0 이하라 분석에서 제외했습니다."
    return {
        "id": int(_float(row.get("id"))),
        "name": name,
        "symbol": str(row.get("symbol") or "").upper(),
        "asset_type": str(row.get("asset_type") or ""),
        "asset_class": str(row.get("asset_class") or "ALTERNATIVE"),
        "country": str(row.get("country") or "OTHER"),
        "currency": currency,
        "exchange": str(row.get("exchange") or ""),
        "sector": str(row.get("sector") or "Unclassified"),
        "industry": str(row.get("industry") or ""),
        "quantity": quantity,
        "average_price": average,
        "current_price": current,
        "exchange_rate": float(rate),
        "cost_value_krw": cost,
        "value_krw": value,
        "profit_loss_krw": value - cost,
        "is_cash": bool(row.get("is_cash")),
        "is_leverage": bool(row.get("is_leverage")),
        "is_inverse": bool(row.get("is_inverse")),
        "leverage_multiple": _float(row.get("leverage_multiple"), 1.0),
        "tags": str(row.get("tags") or ""),
    }, None


@st.cache_data(ttl=300, show_spinner=False)
def get_portfolio_analysis(exclude_real_estate: bool = False) -> dict[str, Any]:
    create_tables()
    assets_df = get_assets()
    exchange = get_exchange_rates_to_krw()
    rates = exchange.get("rates") or {"KRW": 1.0}
    assets: list[dict[str, Any]] = []
    conversion_warnings: list[str] = []
    for _, row in assets_df.iterrows():
        if exclude_real_estate:
            asset_type = str(row.get("asset_type") or "")
            asset_class = str(row.get("asset_class") or "")
            if asset_type == "부동산" or asset_class == "REAL_ESTATE":
                continue

        asset, warning = _convert_row(row, rates)
        if asset:
            assets.append(asset)
        if warning:
            conversion_warnings.append(warning)
    result = analyze_portfolio(assets)
    result.update({
        "exchange_rate_date": exchange.get("date"),
        "exchange_rate_success": bool(exchange.get("success")),
        "source_asset_count": int(len(assets_df)),
        "analyzed_asset_count": len(assets),
        "exclude_real_estate": bool(exclude_real_estate),
    })
    result["warnings"] = list(dict.fromkeys(conversion_warnings + result.get("warnings", [])))
    if exchange.get("message"):
        result["warnings"].insert(0, str(exchange["message"]))
    return result


def clear_portfolio_analysis_cache() -> None:
    get_portfolio_analysis.clear()

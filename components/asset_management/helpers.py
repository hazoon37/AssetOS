from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from ui.common.formatters import format_currency


def get_default_currency(asset_type: str) -> str:
    return "USD" if asset_type in ["미국주식", "미국ETF", "미국채권"] else "KRW"


def get_quantity_format(asset_type: str) -> str:
    if asset_type == "코인":
        return "%.8f"
    if asset_type in ["미국주식", "미국ETF"]:
        return "%.4f"
    return "%.0f"


def get_quantity_step(asset_type: str) -> float:
    if asset_type == "코인":
        return 0.00000001
    if asset_type in ["미국주식", "미국ETF"]:
        return 0.0001
    return 1.0


def get_symbol_placeholder(asset_type: str) -> str:
    return {
        "국내주식": "예: 005930",
        "미국주식": "예: NVDA, AAPL",
        "국내ETF": "예: 360750",
        "미국ETF": "예: SGOV, TLT, QLD",
        "코인": "예: BTC, ETH, XRP",
    }.get(asset_type, "종목코드 또는 구분명")


def format_currency_value(value: float, currency: str) -> str:
    return format_currency(value, currency)


def format_quantity_value(value: float, asset_type: str) -> str:
    if asset_type == "코인":
        return f"{float(value):,.8f}"
    if asset_type in ["미국주식", "미국ETF"]:
        return f"{float(value):,.4f}"
    return f"{float(value):,.0f}"


def safe_text(value: object) -> str:
    if value is None:
        return ""
    missing = pd.isna(value)
    if isinstance(missing, (bool, np.bool_)) and bool(missing):
        return ""
    return str(value)


def prepare_assets_dataframe(assets_df: pd.DataFrame) -> pd.DataFrame:
    """DB ID는 유지하고 화면 표시번호만 1부터 다시 생성합니다."""
    if assets_df.empty:
        return assets_df.copy()
    result = assets_df.sort_values("id", ascending=True).reset_index(drop=True).copy()
    result["표시번호"] = result.index + 1
    return result


def clear_add_lookup_state() -> None:
    for key in [
        "add_lookup_success", "add_lookup_price", "add_lookup_symbol",
        "add_lookup_currency", "add_market_symbol", "add_market_current_price",
    ]:
        st.session_state.pop(key, None)

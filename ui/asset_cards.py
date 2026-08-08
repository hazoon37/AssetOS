from __future__ import annotations

import streamlit as st

from ui.common.formatters import format_currency, format_percent


def render_portfolio_summary(summary: dict[str, float], exchange_rate_date: str) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 매입금액", format_currency(summary["purchase"]))
    c2.metric("총 평가금액", format_currency(summary["value"]))
    c3.metric("총 평가손익", format_currency(summary["profit"]))
    c4.metric("통합 수익률", format_percent(summary["return_rate"], signed=True))
    st.caption(f"환율 기준일: {exchange_rate_date}")

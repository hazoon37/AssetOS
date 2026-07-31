from __future__ import annotations

import streamlit as st


def render_portfolio_summary(summary: dict[str, float], exchange_rate_date: str) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 매입금액", f"₩ {summary['purchase']:,.0f}")
    c2.metric("총 평가금액", f"₩ {summary['value']:,.0f}")
    c3.metric("총 평가손익", f"₩ {summary['profit']:+,.0f}")
    c4.metric("통합 수익률", f"{summary['return_rate']:+,.2f}%")
    st.caption(f"환율 기준일: {exchange_rate_date}")

from __future__ import annotations

import streamlit as st

from services.exchange_rate_service import get_exchange_rates_to_krw
from ui.common.formatters import format_currency


def render_page_header() -> None:
    st.title("💰 AssetOS 자산관리")
    st.write(
        "자산을 등록하고 보유자산 목록에서 바로 수정·삭제할 수 있습니다. "
        "외화 자산은 현재 환율로 원화 환산합니다."
    )


def render_exchange_panel(exchange_data: dict) -> None:
    exchange_rates = exchange_data["rates"]
    with st.expander("💱 적용 환율 보기", expanded=False):
        st.caption(f"환율 기준일: {exchange_data['date']}")
        currencies = ["USD", "JPY", "HKD", "EUR", "GBP"]
        columns = st.columns(len(currencies))
        for column, code in zip(columns, currencies):
            with column:
                rate = exchange_rates.get(code)
                st.metric(f"1 {code}", format_currency(rate) if rate is not None else "조회 실패")
        if not exchange_data["success"]:
            st.warning(exchange_data["message"])
        if st.button("환율 새로고침", width="stretch"):
            get_exchange_rates_to_krw.clear()
            st.rerun()

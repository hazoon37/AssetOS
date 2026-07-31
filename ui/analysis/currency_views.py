from __future__ import annotations

from typing import Any

import streamlit as st

from ui.common.formatters import (
    format_currency,
    format_krw,
    format_large_currency,
    safe_float,
)


def get_exchange_rate(
    currency: str,
    exchange_data: dict[str, Any],
) -> float | None:
    """환율 조회 결과에서 해당 통화의 원화 환율을 가져옵니다."""

    normalized_currency = (
        str(currency or "")
        .strip()
        .upper()
    )

    if normalized_currency == "KRW":
        return 1.0

    rates = exchange_data.get(
        "rates",
        {},
    )

    if not isinstance(rates, dict):
        return None

    return safe_float(
        rates.get(
            normalized_currency
        )
    )


def calculate_krw_amount(
    foreign_amount: float | None,
    exchange_rate: float | None,
) -> float | None:
    """외화 금액을 원화로 환산합니다."""

    if (
        foreign_amount is None
        or exchange_rate is None
    ):
        return None

    return (
        foreign_amount
        * exchange_rate
    )


def render_krw_conversion(
    metadata_result: dict[str, Any],
    exchange_data: dict[str, Any],
) -> None:
    """
    외화 자산의 현재가와 시가총액을
    원화 환산 보조정보로 표시합니다.
    """

    if not metadata_result.get(
        "success"
    ):
        return

    currency = str(
        metadata_result.get(
            "currency"
        )
        or ""
    ).strip().upper()

    # 원화 자산은 이미 KRW로 표시되므로
    # 별도의 환산 영역을 만들지 않습니다.
    if (
        not currency
        or currency == "KRW"
    ):
        return

    exchange_rate = get_exchange_rate(
        currency=currency,
        exchange_data=exchange_data,
    )

    if exchange_rate is None:

        st.warning(
            f"{currency} 환율을 가져오지 못해 "
            "원화 환산값을 표시할 수 없습니다."
        )

        return

    current_price = safe_float(
        metadata_result.get(
            "price"
        )
    )

    market_cap = safe_float(
        metadata_result.get(
            "market_cap"
        )
    )

    current_price_krw = (
        calculate_krw_amount(
            foreign_amount=current_price,
            exchange_rate=exchange_rate,
        )
    )

    market_cap_krw = (
        calculate_krw_amount(
            foreign_amount=market_cap,
            exchange_rate=exchange_rate,
        )
    )

    st.subheader(
        "원화 환산 참고"
    )

    price_col, market_cap_col, rate_col = (
        st.columns(3)
    )

    price_col.metric(
        "현재가 원화 환산",
        format_krw(
            current_price_krw
        ),
        help=(
            f"{format_currency(current_price, currency)} "
            f"× 환율 {exchange_rate:,.2f}"
        ),
    )

    market_cap_col.metric(
        "시가총액 원화 환산",
        format_large_currency(
            market_cap_krw,
            "KRW",
        ),
    )

    rate_col.metric(
        f"{currency}/KRW 환율",
        format_krw(
            exchange_rate
        ),
    )

    exchange_date = exchange_data.get(
        "date"
    )

    caption_parts = [
        "원화 환산값은 참고용이며 "
        "실제 증권사·거래소 체결환율과 다를 수 있습니다."
    ]

    if exchange_date:
        caption_parts.insert(
            0,
            f"환율 기준일: {exchange_date}",
        )

    st.caption(
        " · ".join(
            caption_parts
        )
    )
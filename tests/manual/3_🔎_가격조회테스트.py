from __future__ import annotations

import streamlit as st

from services.exchange_rate_service import (
    convert_to_krw,
    get_exchange_rates_to_krw,
)
from services.market_price_service import (
    get_market_price,
)

st.set_page_config(
    page_title="가격 조회 테스트",
    page_icon="🔎",
    layout="wide",
)


ASSET_TYPES = [
    "미국주식",
    "미국ETF",
    "국내주식",
    "국내ETF",
    "코인",
]


def format_price(
    price: float,
    currency: str,
) -> str:
    """조회 가격을 보기 좋게 표시합니다."""

    if currency == "KRW":
        return f"₩ {price:,.0f}"

    return f"$ {price:,.2f}"


st.title("🔎 시장가격 자동조회 테스트")

st.write(
    """
    자산관리 화면에 기능을 합치기 전에
    주식·ETF·코인 가격 조회가 정상적으로 작동하는지 확인합니다.
    """
)

st.divider()


asset_type = st.selectbox(
    "자산 종류",
    ASSET_TYPES,
)


if asset_type in [
    "미국주식",
    "미국ETF",
]:
    currency = "USD"

elif asset_type in [
    "국내주식",
    "국내ETF",
]:
    currency = "KRW"

else:
    currency = st.selectbox(
        "코인 가격 통화",
        ["KRW", "USD"],
    )


placeholder_map = {
    "미국주식": "예: NVDA, AAPL",
    "미국ETF": "예: SGOV, TLT, QLD",
    "국내주식": "예: 005930",
    "국내ETF": "예: 360750",
    "코인": "예: BTC, ETH, XRP",
}


symbol = st.text_input(
    "종목코드 또는 티커",
    placeholder=placeholder_map[
        asset_type
    ],
)


lookup_button = st.button(
    "현재가 조회",
    type="primary",
    width="stretch",
)


if lookup_button:

    if not symbol.strip():

        st.warning(
            "종목코드 또는 티커를 입력해 주세요."
        )

    else:

        with st.spinner(
            "시장가격을 조회하고 있습니다..."
        ):

            result = get_market_price(
                asset_type=asset_type,
                symbol=symbol,
                currency=currency,
            )

        if not result["success"]:

            st.error(
                result["message"]
            )

        else:

            price = float(
                result["price"]
            )

            result_currency = str(
                result.get(
                    "currency",
                    currency,
                )
            )

            resolved_symbol = result.get(
                "ticker",
                result.get(
                    "symbol",
                    symbol.upper(),
                ),
            )

            st.success(
                "가격 조회에 성공했습니다."
            )

            col1, col2, col3 = (
                st.columns(3)
            )

            col1.metric(
                "조회 종목",
                resolved_symbol,
            )

            col2.metric(
                "현재가",
                format_price(
                    price,
                    result_currency,
                ),
            )

            col3.metric(
                "거래 통화",
                result_currency,
            )

            exchange_data = (
                get_exchange_rates_to_krw()
            )

            exchange_rates = exchange_data[
                "rates"
            ]

            price_krw = convert_to_krw(
                amount=price,
                currency=result_currency,
                rates=exchange_rates,
            )

            if price_krw is not None:

                st.info(
                    "원화 환산가격: "
                    f"₩ {price_krw:,.0f}"
                )

                st.caption(
                    "환율 기준일: "
                    f"{exchange_data['date']}"
                )

            else:

                st.warning(
                    "환율을 불러오지 못해 "
                    "원화 환산가격을 계산하지 못했습니다."
                )

            if asset_type == "코인":

                last_updated_at = result.get(
                    "last_updated_at"
                )

                if last_updated_at:

                    st.caption(
                        "CoinGecko 마지막 갱신 시각값: "
                        f"{last_updated_at}"
                    )


st.divider()

st.subheader("테스트 권장값")

st.code(
    """
미국ETF  : SGOV
미국주식 : NVDA
국내주식 : 005930
국내ETF  : 360750
코인     : BTC
    """.strip()
)
from __future__ import annotations

import streamlit as st

from services.company_service import (
    DEFAULT_CURRENCIES,
    analyze_company,
)
from ui.analysis.analysis_views import (
    render_korean_stock_analysis,
    render_metadata_result,
)
from ui.analysis.currency_views import (
    render_krw_conversion,
)


st.set_page_config(
    page_title="AssetOS 종목 분석",
    page_icon="🔍",
    layout="wide",
)


ASSET_TYPES = [
    "국내주식",
    "미국주식",
    "국내ETF",
    "미국ETF",
    "코인",
]


PLACEHOLDERS = {
    "국내주식": "예: 005930",
    "미국주식": "예: AAPL",
    "국내ETF": "예: 069500",
    "미국ETF": "예: SPY",
    "코인": "예: BTC",
}


SESSION_RESULT_KEY = (
    "company_analysis_result"
)


# ==================================================
# 페이지 제목
# ==================================================

st.title(
    "🔍 종목 분석"
)

st.write(
    """
    종목코드 또는 티커를 입력하면 주식·ETF·코인의
    기본정보와 시장정보를 조회합니다.

    외화 자산은 원래 거래통화와 원화 환산값을 함께 표시합니다.
    국내주식은 OpenDART 공식 재무정보를 결합해 PER, PBR,
    ROE와 주요 재무비율을 AssetOS가 직접 계산합니다.
    """
)

st.divider()


# ==================================================
# 입력 영역
# ==================================================

input_col1, input_col2 = st.columns(
    [1, 2]
)

with input_col1:

    asset_type = st.selectbox(
        "자산 종류",
        options=ASSET_TYPES,
        key="company_analysis_asset_type",
    )

with input_col2:

    symbol = st.text_input(
        "종목코드 또는 티커",
        placeholder=PLACEHOLDERS[
            asset_type
        ],
        key="company_analysis_symbol",
    )


button_col1, button_col2 = st.columns(
    [3, 1]
)

with button_col1:

    analyze_clicked = st.button(
        "종목 분석",
        type="primary",
        use_container_width=True,
    )

with button_col2:

    clear_clicked = st.button(
        "결과 초기화",
        use_container_width=True,
    )


# ==================================================
# 초기화
# ==================================================

if clear_clicked:

    st.session_state.pop(
        SESSION_RESULT_KEY,
        None,
    )

    st.rerun()


# ==================================================
# 단일 서비스 호출
# ==================================================

if analyze_clicked:

    normalized_symbol = (
        symbol.strip().upper()
    )

    with st.spinner(
        "종목정보와 환율을 조회하고 분석하고 있습니다..."
    ):

        result = analyze_company(
            asset_type=asset_type,
            symbol=normalized_symbol,
            currency=DEFAULT_CURRENCIES[
                asset_type
            ],
        )

    st.session_state[
        SESSION_RESULT_KEY
    ] = result


# ==================================================
# 결과 불러오기
# ==================================================

result = st.session_state.get(
    SESSION_RESULT_KEY
)


# ==================================================
# 결과 표시
# ==================================================

if result:

    st.divider()

    result_success = result.get(
        "success",
        False,
    )

    metadata_result = result.get(
        "metadata"
    ) or {}

    exchange_result = result.get(
        "exchange"
    ) or {}

    valuation_result = result.get(
        "valuation"
    )

    saved_asset_type = result.get(
        "asset_type",
        asset_type,
    )


    # ==============================================
    # 전체 실패
    # ==============================================

    if not result_success:

        st.error(
            result.get(
                "message",
                "종목분석에 실패했습니다.",
            )
        )

        warnings = result.get(
            "warnings",
            [],
        )

        if warnings:

            with st.expander(
                "오류 세부정보",
                expanded=True,
            ):

                for warning in warnings:
                    st.warning(warning)


    # ==============================================
    # 조회 성공
    # ==============================================

    else:

        if saved_asset_type == "국내주식":

            basic_tab, analysis_tab = (
                st.tabs(
                    [
                        "기본정보",
                        "가치평가·재무분석",
                    ]
                )
            )

            with basic_tab:

                render_metadata_result(
                    result=metadata_result,
                    asset_type=(
                        saved_asset_type
                    ),
                )

            with analysis_tab:

                if (
                    valuation_result
                    and valuation_result.get(
                        "success",
                        False,
                    )
                ):

                    render_korean_stock_analysis(
                        valuation_result
                    )

                else:

                    st.warning(
                        result.get(
                            "message",
                            "가치평가 결과를 "
                            "불러오지 못했습니다.",
                        )
                    )

        else:

            render_metadata_result(
                result=metadata_result,
                asset_type=saved_asset_type,
            )

            render_krw_conversion(
                metadata_result=(
                    metadata_result
                ),
                exchange_data=(
                    exchange_result
                ),
            )


        # ==========================================
        # 통합 분석 상태
        # ==========================================

        status = result.get(
            "status",
            {},
        )

        sources = result.get(
            "sources",
            {},
        )

        with st.expander(
            "데이터 조회 상태",
            expanded=False,
        ):

            status_col1, status_col2, status_col3 = (
                st.columns(3)
            )

            status_col1.metric(
                "종목정보",
                (
                    "정상"
                    if status.get(
                        "metadata_success"
                    )
                    else "실패"
                ),
            )

            status_col2.metric(
                "환율정보",
                (
                    "정상"
                    if status.get(
                        "exchange_success"
                    )
                    else "확인 필요"
                ),
            )

            valuation_required = (
                saved_asset_type
                == "국내주식"
            )

            status_col3.metric(
                "가치평가",
                (
                    "정상"
                    if status.get(
                        "valuation_success"
                    )
                    else (
                        "확인 필요"
                        if valuation_required
                        else "해당 없음"
                    )
                ),
            )

            st.write(
                "종목정보 출처:",
                sources.get(
                    "metadata"
                )
                or "정보 없음",
            )

            st.write(
                "환율 출처:",
                sources.get(
                    "exchange"
                )
                or "정보 없음",
            )

            if valuation_required:

                st.write(
                    "가치평가 출처:",
                    sources.get(
                        "valuation"
                    )
                    or "정보 없음",
                )


        # ==========================================
        # 통합 경고
        # ==========================================

        combined_warnings = result.get(
            "warnings",
            [],
        )

        if combined_warnings:

            with st.expander(
                "통합 조회 주의사항",
                expanded=False,
            ):

                for warning in combined_warnings:
                    st.warning(warning)


        # ==========================================
        # 통합 원본 결과
        # ==========================================

        with st.expander(
            "통합 분석 원본 보기",
            expanded=False,
        ):

            st.json(result)


else:

    st.caption(
        "자산 종류와 종목코드를 입력한 뒤 "
        "'종목 분석' 버튼을 누르세요."
    )


# ==================================================
# 입력 예시
# ==================================================

st.divider()

st.subheader(
    "입력 예시"
)

st.code(
    """
국내주식  005930
미국주식  AAPL
국내ETF   069500
미국ETF   SPY
코인      BTC
    """.strip()
)

st.caption(
    "외화 자산의 원화 환산값은 참고용이며, "
    "실제 증권사·거래소의 체결환율과 다를 수 있습니다."
)
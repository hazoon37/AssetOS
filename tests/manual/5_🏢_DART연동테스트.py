from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from services.dart_service import (
    download_corporation_codes,
    get_dart_api_key,
    get_dart_company_data,
)


st.set_page_config(
    page_title="DART 연동 테스트",
    page_icon="🏢",
    layout="wide",
)


def format_krw(
    value: float | None,
) -> str:
    """원화 금액을 표시합니다."""

    if value is None:
        return "정보 없음"

    return f"₩ {value:,.0f}"


def calculate_growth_rate(
    current_value: float | None,
    previous_value: float | None,
) -> float | None:
    """전기 대비 증감률을 계산합니다."""

    if (
        current_value is None
        or previous_value is None
        or previous_value == 0
    ):
        return None

    return (
        (
            current_value
            - previous_value
        )
        / abs(previous_value)
        * 100
    )


def display_financial_metric(
    label: str,
    account_data: dict[str, Any] | None,
) -> None:
    """재무계정 카드를 표시합니다."""

    if not account_data:

        st.metric(
            label,
            "정보 없음",
        )

        return

    current_amount = account_data.get(
        "current_amount"
    )

    previous_amount = account_data.get(
        "previous_amount"
    )

    growth_rate = calculate_growth_rate(
        current_value=current_amount,
        previous_value=previous_amount,
    )

    st.metric(
        label,
        format_krw(
            current_amount
        ),
        delta=(
            f"{growth_rate:+.2f}%"
            if growth_rate is not None
            else None
        ),
        help=(
            f"DART 계정명: "
            f"{account_data.get('account_name', '-')}"
        ),
    )


st.title("🏢 OpenDART 연동 테스트")

st.write(
    """
    국내주식 종목코드를 입력하면 금융감독원 OpenDART에서
    기업개황과 최근 사업보고서의 주요 재무계정을 조회합니다.

    이 페이지는 기존 주식분석 화면에 DART 기능을 통합하기 전
    API 연결과 데이터 구조를 확인하기 위한 테스트 페이지입니다.
    """
)


api_key = get_dart_api_key()

if not api_key:

    st.error(
        "DART_API_KEY가 설정되지 않았습니다. "
        ".streamlit/secrets.toml 파일을 확인해 주세요."
    )

    st.code(
        'DART_API_KEY = "발급받은_40자리_인증키"'
    )

    st.stop()


st.success(
    "OpenDART 인증키가 설정되어 있습니다."
)


with st.expander(
    "DART 고유번호 캐시 관리",
    expanded=False,
):

    st.caption(
        "종목코드와 DART 고유번호 매핑은 "
        "24시간 동안 캐시됩니다."
    )

    if st.button(
        "DART 고유번호 목록 새로고침",
        use_container_width=True,
    ):

        download_corporation_codes.clear()

        st.success(
            "DART 고유번호 캐시를 초기화했습니다."
        )

        st.rerun()


st.divider()


input_column1, input_column2 = (
    st.columns([3, 1])
)

with input_column1:

    stock_code = st.text_input(
        "국내주식 종목코드",
        placeholder="예: 005930",
        max_chars=6,
    )

with input_column2:

    st.write("")

    lookup_clicked = st.button(
        "DART 정보 조회",
        type="primary",
        use_container_width=True,
    )


if lookup_clicked:

    if not stock_code.strip():

        st.warning(
            "6자리 종목코드를 입력해 주세요."
        )

    else:

        with st.spinner(
            "OpenDART 기업·재무정보를 조회하고 있습니다..."
        ):

            result = get_dart_company_data(
                stock_code=stock_code,
            )

        st.session_state[
            "dart_test_result"
        ] = result


result = st.session_state.get(
    "dart_test_result"
)


if result:

    st.divider()

    if not result.get("success"):

        st.error(
            result.get(
                "message",
                "DART 조회에 실패했습니다.",
            )
        )

    else:

        corporation = result.get(
            "corporation",
            {},
        )

        overview = result.get(
            "overview"
        ) or {}

        financials = result.get(
            "financials",
            {},
        )

        st.subheader(
            corporation.get(
                "corp_name",
                "기업명 정보 없음",
            )
        )

        st.caption(
            f"종목코드: "
            f"{corporation.get('stock_code', '-')} · "
            f"DART 고유번호: "
            f"{corporation.get('corp_code', '-')}"
        )


        # ==========================================
        # 기업개황
        # ==========================================

        st.subheader("기업개황")

        overview_col1, overview_col2 = (
            st.columns(2)
        )

        with overview_col1:

            st.markdown(
                f"""
                **정식 회사명**  
                {overview.get("corp_name") or "정보 없음"}

                **영문 회사명**  
                {overview.get("corp_name_eng") or "정보 없음"}

                **대표자**  
                {overview.get("ceo_nm") or "정보 없음"}

                **법인 구분**  
                {overview.get("corp_cls") or "정보 없음"}
                """
            )

        with overview_col2:

            st.markdown(
                f"""
                **설립일**  
                {overview.get("est_dt") or "정보 없음"}

                **결산월**  
                {overview.get("acc_mt") or "정보 없음"}

                **업종 코드**  
                {overview.get("induty_code") or "정보 없음"}

                **홈페이지**  
                {overview.get("hm_url") or "정보 없음"}
                """
            )

        if result.get(
            "overview_error"
        ):

            st.warning(
                result["overview_error"]
            )


        # ==========================================
        # 재무정보
        # ==========================================

        st.divider()

        if not financials.get(
            "success"
        ):

            st.error(
                financials.get(
                    "message",
                    "재무정보 조회에 실패했습니다.",
                )
            )

        else:

            business_year = financials.get(
                "business_year"
            )

            summary = financials.get(
                "summary",
                {},
            )

            st.subheader(
                f"{business_year}년 사업보고서 주요 재무정보"
            )

            st.caption(
                "연결재무제표가 존재하면 연결 기준을 우선하며, "
                "없으면 별도재무제표를 사용합니다."
            )

            income_col1, income_col2, income_col3 = (
                st.columns(3)
            )

            with income_col1:
                display_financial_metric(
                    "매출액",
                    summary.get(
                        "매출액"
                    ),
                )

            with income_col2:
                display_financial_metric(
                    "영업이익",
                    summary.get(
                        "영업이익"
                    ),
                )

            with income_col3:
                display_financial_metric(
                    "당기순이익",
                    summary.get(
                        "당기순이익"
                    ),
                )


            balance_col1, balance_col2, balance_col3 = (
                st.columns(3)
            )

            with balance_col1:
                display_financial_metric(
                    "자산총계",
                    summary.get(
                        "자산총계"
                    ),
                )

            with balance_col2:
                display_financial_metric(
                    "부채총계",
                    summary.get(
                        "부채총계"
                    ),
                )

            with balance_col3:
                display_financial_metric(
                    "자본총계",
                    summary.get(
                        "자본총계"
                    ),
                )


            # ======================================
            # 자동 계산 지표
            # ======================================

            st.subheader(
                "DART 기반 자동 계산"
            )

            total_assets = (
                summary.get(
                    "자산총계"
                )
                or {}
            ).get(
                "current_amount"
            )

            total_liabilities = (
                summary.get(
                    "부채총계"
                )
                or {}
            ).get(
                "current_amount"
            )

            total_equity = (
                summary.get(
                    "자본총계"
                )
                or {}
            ).get(
                "current_amount"
            )

            operating_income = (
                summary.get(
                    "영업이익"
                )
                or {}
            ).get(
                "current_amount"
            )

            revenue = (
                summary.get(
                    "매출액"
                )
                or {}
            ).get(
                "current_amount"
            )

            net_income = (
                summary.get(
                    "당기순이익"
                )
                or {}
            ).get(
                "current_amount"
            )

            debt_ratio = None

            if (
                total_liabilities is not None
                and total_equity not in (
                    None,
                    0,
                )
            ):

                debt_ratio = (
                    total_liabilities
                    / total_equity
                    * 100
                )

            operating_margin = None

            if (
                operating_income is not None
                and revenue not in (
                    None,
                    0,
                )
            ):

                operating_margin = (
                    operating_income
                    / revenue
                    * 100
                )

            net_margin = None

            if (
                net_income is not None
                and revenue not in (
                    None,
                    0,
                )
            ):

                net_margin = (
                    net_income
                    / revenue
                    * 100
                )

            roe = None

            if (
                net_income is not None
                and total_equity not in (
                    None,
                    0,
                )
            ):

                roe = (
                    net_income
                    / total_equity
                    * 100
                )

            ratio_col1, ratio_col2, ratio_col3, ratio_col4 = (
                st.columns(4)
            )

            ratio_col1.metric(
                "부채비율",
                (
                    f"{debt_ratio:,.2f}%"
                    if debt_ratio is not None
                    else "정보 없음"
                ),
            )

            ratio_col2.metric(
                "영업이익률",
                (
                    f"{operating_margin:,.2f}%"
                    if operating_margin is not None
                    else "정보 없음"
                ),
            )

            ratio_col3.metric(
                "순이익률",
                (
                    f"{net_margin:,.2f}%"
                    if net_margin is not None
                    else "정보 없음"
                ),
            )

            ratio_col4.metric(
                "단순 ROE",
                (
                    f"{roe:,.2f}%"
                    if roe is not None
                    else "정보 없음"
                ),
                help=(
                    "당기순이익 ÷ 당기말 자본총계로 계산한 "
                    "간이 ROE입니다. 평균자본을 사용하는 정식 ROE와 "
                    "차이가 날 수 있습니다."
                ),
            )


            # ======================================
            # 재무계정 상세표
            # ======================================

            with st.expander(
                "DART 재무계정 원본 보기",
                expanded=False,
            ):

                accounts_df = pd.DataFrame(
                    financials.get(
                        "accounts",
                        [],
                    )
                )

                if accounts_df.empty:

                    st.info(
                        "표시할 원본 재무계정이 없습니다."
                    )

                else:

                    preferred_columns = [
                        "fs_nm",
                        "sj_nm",
                        "account_nm",
                        "thstrm_nm",
                        "thstrm_amount",
                        "frmtrm_nm",
                        "frmtrm_amount",
                        "currency",
                    ]

                    available_columns = [
                        column
                        for column in preferred_columns
                        if column
                        in accounts_df.columns
                    ]

                    st.dataframe(
                        accounts_df[
                            available_columns
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )


st.divider()

st.subheader("권장 테스트 종목")

st.code(
    """
삼성전자   005930
SK하이닉스 000660
NAVER      035420
현대차     005380
KB금융     105560
    """.strip()
)

st.caption(
    "은행·보험·증권사는 일반 제조기업과 계정과목 구조가 달라 "
    "매출액이나 영업이익 항목이 다르게 표시될 수 있습니다."
)
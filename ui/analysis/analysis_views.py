from __future__ import annotations

from typing import Any

import streamlit as st

from ui.common.formatters import (
    format_currency,
    format_decimal_percentage,
    format_large_currency,
    format_multiple,
    format_number,
    format_percentage_value,
)
from ui.valuation.metric_views import (
    render_growth_metrics,
    render_metric_status_table,
    render_profitability_metrics,
    render_valuation_metrics,
)


def calculate_price_position_text(
    current_price: float | None,
    low_price: float | None,
    high_price: float | None,
) -> str:
    """52주 최저·최고가 사이 현재 가격 위치를 표시합니다."""

    if (
        current_price is None
        or low_price is None
        or high_price is None
        or high_price <= low_price
    ):
        return "정보 없음"

    position = (
        (current_price - low_price)
        / (high_price - low_price)
        * 100
    )

    return f"{position:,.1f}%"


def render_source_caption(
    market_source: str,
    financial_source: str | None = None,
    calculation_source: str | None = None,
) -> None:
    """시장·재무·계산 데이터 출처를 표시합니다."""

    source_parts = [
        f"시장정보: {market_source}",
    ]

    if financial_source:
        source_parts.append(
            f"재무정보: {financial_source}"
        )

    if calculation_source:
        source_parts.append(
            f"계산: {calculation_source}"
        )

    st.caption(
        " · ".join(source_parts)
    )


def render_basic_metadata(
    result: dict[str, Any],
) -> None:
    """종목 기본정보와 주요 시장정보를 표시합니다."""

    currency = result.get(
        "currency"
    )

    display_name = (
        result.get("name")
        or result.get("resolved_symbol")
        or result.get("symbol")
        or "종목명 정보 없음"
    )

    st.subheader(display_name)

    st.caption(
        f"입력 티커: "
        f"{result.get('symbol') or '-'} · "
        f"조회 티커: "
        f"{result.get('resolved_symbol') or '-'} · "
        f"거래소: "
        f"{result.get('exchange') or '-'} · "
        f"통화: {currency or '-'}"
    )

    col1, col2, col3, col4 = (
        st.columns(4)
    )

    col1.metric(
        "현재가",
        format_currency(
            result.get("price"),
            currency,
        ),
    )

    col2.metric(
        "시가총액",
        format_large_currency(
            result.get("market_cap"),
            currency,
        ),
    )

    col3.metric(
        "배당수익률",
        format_decimal_percentage(
            result.get(
                "dividend_yield"
            )
        ),
    )

    col4.metric(
        "52주 가격 위치",
        calculate_price_position_text(
            current_price=result.get(
                "price"
            ),
            low_price=result.get(
                "fifty_two_week_low"
            ),
            high_price=result.get(
                "fifty_two_week_high"
            ),
        ),
    )


def render_company_profile(
    result: dict[str, Any],
) -> None:
    """주식형 자산의 기업 기본정보를 표시합니다."""

    st.subheader(
        "기업 기본정보"
    )

    col1, col2 = st.columns(2)

    with col1:

        st.markdown(
            f"""
            **섹터**  
            {result.get("sector") or "정보 없음"}

            **산업**  
            {result.get("industry") or "정보 없음"}
            """
        )

    with col2:

        st.markdown(
            f"""
            **거래소**  
            {result.get("exchange") or "정보 없음"}

            **종목 유형**  
            {result.get("quote_type") or "정보 없음"}
            """
        )

    description = result.get(
        "description"
    )

    if description:

        with st.expander(
            "기업 설명 보기",
            expanded=False,
        ):

            st.write(description)


def render_external_stock_metrics(
    result: dict[str, Any],
) -> None:
    """외부 데이터에서 조회한 주식 지표를 표시합니다."""

    st.subheader(
        "가치평가"
    )

    col1, col2, col3, col4 = (
        st.columns(4)
    )

    col1.metric(
        "PER",
        format_multiple(
            result.get("trailing_pe")
        ),
    )

    col2.metric(
        "Forward PER",
        format_multiple(
            result.get("forward_pe")
        ),
    )

    col3.metric(
        "PBR",
        format_multiple(
            result.get("price_to_book")
        ),
    )

    col4.metric(
        "PSR",
        format_multiple(
            result.get("price_to_sales")
        ),
    )

    st.subheader(
        "수익성·성장성"
    )

    profit1, profit2, profit3, profit4 = (
        st.columns(4)
    )

    profit1.metric(
        "ROE",
        format_decimal_percentage(
            result.get(
                "return_on_equity"
            )
        ),
    )

    profit2.metric(
        "영업이익률",
        format_decimal_percentage(
            result.get(
                "operating_margin"
            )
        ),
    )

    profit3.metric(
        "순이익률",
        format_decimal_percentage(
            result.get(
                "profit_margin"
            )
        ),
    )

    profit4.metric(
        "매출 성장률",
        format_decimal_percentage(
            result.get(
                "revenue_growth"
            )
        ),
    )

    market1, market2, market3, market4 = (
        st.columns(4)
    )

    beta = result.get(
        "beta"
    )

    market1.metric(
        "베타",
        (
            f"{beta:,.2f}"
            if beta is not None
            else "정보 없음"
        ),
    )

    market2.metric(
        "52주 최고가",
        format_currency(
            result.get(
                "fifty_two_week_high"
            ),
            result.get("currency"),
        ),
    )

    market3.metric(
        "52주 최저가",
        format_currency(
            result.get(
                "fifty_two_week_low"
            ),
            result.get("currency"),
        ),
    )

    market4.metric(
        "애널리스트 목표가",
        format_currency(
            result.get(
                "target_mean_price"
            ),
            result.get("currency"),
        ),
    )


def render_etf_information(
    result: dict[str, Any],
) -> None:
    """ETF 전용 기본정보를 표시합니다."""

    st.subheader(
        "ETF 정보"
    )

    col1, col2, col3 = (
        st.columns(3)
    )

    col1.metric(
        "운용사",
        result.get(
            "fund_family"
        )
        or "정보 없음",
    )

    col2.metric(
        "카테고리",
        result.get(
            "category"
        )
        or "정보 없음",
    )

    col3.metric(
        "보유 종목 수",
        format_number(
            result.get(
                "holdings_count"
            ),
            suffix="개",
        ),
    )

    st.info(
        "ETF의 운용보수, 상위 보유 종목, "
        "섹터 비중과 중복 노출 분석은 "
        "향후 ETF 전용 분석 단계에서 추가합니다."
    )


def render_coin_information(
    result: dict[str, Any],
) -> None:
    """코인 전용 시장정보를 표시합니다."""

    st.subheader(
        "코인 시장정보"
    )

    col1, col2, col3 = (
        st.columns(3)
    )

    col1.metric(
        "현재가",
        format_currency(
            result.get("price"),
            result.get("currency"),
        ),
    )

    col2.metric(
        "24시간 변동률",
        format_percentage_value(
            result.get(
                "change_24h"
            )
        ),
    )

    col3.metric(
        "시가총액",
        format_large_currency(
            result.get("market_cap"),
            result.get("currency"),
        ),
    )

    st.info(
        "코인은 일반 기업의 순이익과 장부가치가 없으므로 "
        "PER·PBR을 적용하지 않습니다."
    )


def render_missing_fields(
    result: dict[str, Any],
) -> None:
    """원본 데이터에서 조회되지 않은 항목을 표시합니다."""

    missing_fields = result.get(
        "missing_fields",
        [],
    )

    if not missing_fields:
        return

    with st.expander(
        "조회되지 않은 정보",
        expanded=False,
    ):

        st.write(
            ", ".join(
                str(field)
                for field in missing_fields
            )
        )

        st.caption(
            "원본 데이터 제공처에 값이 없으면 "
            "정보 없음으로 표시될 수 있습니다."
        )


def render_metadata_result(
    result: dict[str, Any],
    asset_type: str,
) -> None:
    """주식·ETF·코인의 자동조회 결과를 표시합니다."""

    if not result.get(
        "success"
    ):

        st.error(
            result.get(
                "message",
                "종목정보 조회에 실패했습니다.",
            )
        )

        return

    render_basic_metadata(result)

    render_source_caption(
        market_source="Yahoo Finance",
    )

    if asset_type in {
        "국내주식",
        "미국주식",
    }:

        render_company_profile(result)

        render_external_stock_metrics(
            result
        )

    elif asset_type in {
        "국내ETF",
        "미국ETF",
    }:

        render_etf_information(result)

    elif asset_type == "코인":

        render_coin_information(result)

    render_missing_fields(result)

    with st.expander(
        "자동조회 원본 보기",
        expanded=False,
    ):

        st.json(result)


def render_korean_stock_analysis(
    result: dict[str, Any],
) -> None:
    """국내주식 가치평가 엔진 결과를 표시합니다."""

    if not result.get(
        "success"
    ):

        st.error(
            result.get(
                "message",
                "국내주식 분석에 실패했습니다.",
            )
        )

        return

    company_name = result.get(
        "company_name",
        "기업명 정보 없음",
    )

    market = result.get(
        "market",
        {},
    )

    financials = result.get(
        "financials",
        {},
    )

    calculated = result.get(
        "calculated",
        {},
    )

    metric_details = result.get(
        "metric_details",
        {},
    )

    reference = result.get(
        "reference",
        {},
    )

    sources = result.get(
        "sources",
        {},
    )

    st.subheader(company_name)

    st.caption(
        f"종목코드: "
        f"{result.get('stock_code') or '-'} · "
        f"재무 기준연도: "
        f"{result.get('business_year') or '-'}"
    )

    render_source_caption(
        market_source=sources.get(
            "market",
            "Yahoo Finance",
        ),
        financial_source=sources.get(
            "financials",
            "OpenDART",
        ),
        calculation_source=sources.get(
            "calculation",
            "AssetOS",
        ),
    )

    st.subheader(
        "시장정보"
    )

    col1, col2, col3 = (
        st.columns(3)
    )

    col1.metric(
        "현재가",
        format_currency(
            market.get(
                "current_price"
            ),
            market.get(
                "currency",
                "KRW",
            ),
        ),
    )

    col2.metric(
        "시가총액",
        format_large_currency(
            market.get(
                "market_cap"
            ),
            "KRW",
        ),
    )

    col3.metric(
        "추정 상장주식 수",
        format_number(
            market.get(
                "shares_outstanding"
            ),
            suffix="주",
        ),
    )

    render_valuation_metrics(
        metric_details
    )

    st.subheader(
        "직접 계산 주당지표"
    )

    share1, share2, share3, share4 = (
        st.columns(4)
    )

    share1.metric(
        "EPS",
        format_currency(
            calculated.get("eps"),
            "KRW",
        ),
    )

    share2.metric(
        "BPS",
        format_currency(
            calculated.get("bps"),
            "KRW",
        ),
    )

    share3.metric(
        "현재가 ÷ EPS",
        format_multiple(
            calculated.get(
                "price_based_per"
            )
        ),
    )

    share4.metric(
        "현재가 ÷ BPS",
        format_multiple(
            calculated.get(
                "price_based_pbr"
            )
        ),
    )

    render_profitability_metrics(
        metric_details
    )

    render_growth_metrics(
        metric_details
    )

    render_metric_status_table(
        metric_details
    )

    render_dart_financials(
        financials
    )

    render_yahoo_reference(
        reference
    )

    render_analysis_warnings(
        result.get(
            "warnings",
            [],
        )
    )

    with st.expander(
        "국내주식 분석 원본 보기",
        expanded=False,
    ):

        st.json(result)


def render_dart_financials(
    financials: dict[str, Any],
) -> None:
    """OpenDART 핵심 재무정보를 표시합니다."""

    with st.expander(
        "OpenDART 핵심 재무정보",
        expanded=False,
    ):

        col1, col2 = st.columns(2)

        with col1:

            st.markdown(
                "#### 손익계산서"
            )

            st.write(
                "매출액:",
                format_currency(
                    financials.get(
                        "revenue"
                    ),
                    "KRW",
                ),
            )

            st.write(
                "영업이익:",
                format_currency(
                    financials.get(
                        "operating_income"
                    ),
                    "KRW",
                ),
            )

            st.write(
                "당기순이익:",
                format_currency(
                    financials.get(
                        "net_income"
                    ),
                    "KRW",
                ),
            )

        with col2:

            st.markdown(
                "#### 재무상태표"
            )

            st.write(
                "자산총계:",
                format_currency(
                    financials.get(
                        "total_assets"
                    ),
                    "KRW",
                ),
            )

            st.write(
                "부채총계:",
                format_currency(
                    financials.get(
                        "total_liabilities"
                    ),
                    "KRW",
                ),
            )

            st.write(
                "자본총계:",
                format_currency(
                    financials.get(
                        "total_equity"
                    ),
                    "KRW",
                ),
            )


def render_yahoo_reference(
    reference: dict[str, Any],
) -> None:
    """Yahoo Finance 참고 지표를 표시합니다."""

    with st.expander(
        "외부 참고 지표 비교",
        expanded=False,
    ):

        col1, col2, col3 = (
            st.columns(3)
        )

        col1.metric(
            "Yahoo PER",
            format_multiple(
                reference.get(
                    "yahoo_per"
                )
            ),
        )

        col2.metric(
            "Yahoo PBR",
            format_multiple(
                reference.get(
                    "yahoo_pbr"
                )
            ),
        )

        col3.metric(
            "Yahoo Forward PER",
            format_multiple(
                reference.get(
                    "yahoo_forward_per"
                )
            ),
        )

        st.caption(
            "기준 기간, 순이익 정의, 주식 수와 갱신 시점 차이로 "
            "AssetOS 직접 계산값과 다를 수 있습니다."
        )


def render_analysis_warnings(
    warnings: list[str],
) -> None:
    """국내주식 분석 경고를 표시합니다."""

    if not warnings:
        return

    with st.expander(
        "데이터 품질 및 계산 주의사항",
        expanded=True,
    ):

        for warning in warnings:
            st.warning(warning)
from __future__ import annotations

from typing import Any

import streamlit as st

from database.db import add_asset
from services.asset_autofill_service import (
    build_asset_autofill,
)
from services.exchange_rate_service import (
    convert_to_krw,
)
from services.portfolio_service import (
    clear_portfolio_analysis_cache,
)

from .constants import (
    ACCOUNT_ASSET_TYPES,
    ASSET_TYPES,
    AUTO_PRICE_ASSET_TYPES,
    CURRENCY_NAMES,
    MARKET_ASSET_TYPES,
    SUPPORTED_CURRENCIES,
)
from .helpers import (
    clear_add_lookup_state,
    format_currency_value,
    format_quantity_value,
    get_default_currency,
    get_quantity_format,
    get_quantity_step,
    get_symbol_placeholder,
    safe_text,
)


# ==================================================
# 자동입력 전용 상태 키
# ==================================================

AUTOFILL_STATE_KEYS = [
    "add_lookup_success",
    "add_lookup_name",
    "add_lookup_price",
    "add_lookup_symbol",
    "add_lookup_currency",
    "add_lookup_exchange",
    "add_lookup_sector",
    "add_lookup_industry",
    "add_lookup_warnings",
    "add_lookup_country",
    "add_lookup_asset_class",
    "add_lookup_is_cash",
    "add_lookup_is_leverage",
    "add_lookup_is_inverse",
    "add_lookup_leverage_multiple",
    "add_lookup_tags",
    "add_market_name",
    "add_market_symbol",
    "add_market_current_price",
]


def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """숫자 변환에 실패하면 기본값을 반환합니다."""

    if value is None:
        return default

    try:
        return float(value)

    except (TypeError, ValueError):
        return default


def _clear_autofill_state() -> None:
    """기존 조회 상태와 자동입력 상태를 함께 초기화합니다."""

    clear_add_lookup_state()

    for key in AUTOFILL_STATE_KEYS:
        st.session_state.pop(
            key,
            None,
        )


def _resolve_currency(
    asset_type: str,
) -> str:
    """자산 종류에 따라 등록 통화를 결정합니다."""

    if asset_type in [
        "국내주식",
        "국내ETF",
        "부동산",
    ]:
        st.info(
            "이 자산은 원화 기준으로 등록합니다."
        )

        return "KRW"

    if asset_type in [
        "미국주식",
        "미국ETF",
        "미국채권",
    ]:
        st.info(
            "이 자산은 미국 달러 기준으로 등록합니다."
        )

        return "USD"

    default_currency = get_default_currency(
        asset_type
    )

    autofill_currency = safe_text(
        st.session_state.get(
            "add_lookup_currency",
            "",
        )
    ).upper()

    selected_currency = (
        autofill_currency
        if autofill_currency
        in SUPPORTED_CURRENCIES
        else default_currency
    )

    currency_key = (
        f"add_currency_{asset_type}"
    )

    # 위젯 생성 전에 자동조회 통화를 반영합니다.
    if (
        autofill_currency
        in SUPPORTED_CURRENCIES
        and currency_key
        not in st.session_state
    ):
        st.session_state[
            currency_key
        ] = autofill_currency

    return st.selectbox(
        "기준 통화",
        SUPPORTED_CURRENCIES,
        index=SUPPORTED_CURRENCIES.index(
            selected_currency
        ),
        format_func=lambda code: (
            f"{code} · "
            f"{CURRENCY_NAMES[code]}"
        ),
        key=currency_key,
    )


def _get_price_step(
    asset_type: str,
    currency: str,
) -> float:
    """자산별 가격 입력 증감 단위를 반환합니다."""

    if asset_type == "코인":
        return 0.00000001

    if currency in {
        "KRW",
        "JPY",
    }:
        return 1.0

    return 0.01


def _get_price_format(
    asset_type: str,
    currency: str,
) -> str:
    """자산별 가격 입력 형식을 반환합니다."""

    if asset_type == "코인":
        return "%.8f"

    if currency in {
        "KRW",
        "JPY",
    }:
        return "%.0f"

    return "%.2f"


def _store_autofill_result(
    result: dict[str, Any],
) -> None:
    """자동조회 결과를 자산등록 폼 상태에 반영합니다."""

    current_price = _safe_float(
        result.get(
            "current_price"
        )
    )

    resolved_symbol = safe_text(
        result.get(
            "resolved_symbol"
        )
        or result.get(
            "symbol"
        )
    ).upper()

    asset_name = safe_text(
        result.get(
            "asset_name"
        )
    )

    currency = safe_text(
        result.get(
            "currency"
        )
    ).upper()

    st.session_state.update(
        {
            "add_lookup_success": True,
            "add_lookup_name": asset_name,
            "add_lookup_price": current_price,
            "add_lookup_symbol": resolved_symbol,
            "add_lookup_currency": currency,
            "add_lookup_exchange": safe_text(
                result.get(
                    "exchange"
                )
            ),
            "add_lookup_sector": safe_text(
                result.get(
                    "sector"
                )
            ),
            "add_lookup_industry": safe_text(
                result.get(
                    "industry"
                )
            ),
            "add_lookup_warnings": result.get(
                "warnings",
                [],
            ),
            "add_lookup_country": result.get("country", ""),
            "add_lookup_asset_class": result.get("asset_class", ""),
            "add_lookup_is_cash": result.get("is_cash", 0),
            "add_lookup_is_leverage": result.get("is_leverage", 0),
            "add_lookup_is_inverse": result.get("is_inverse", 0),
            "add_lookup_leverage_multiple": result.get("leverage_multiple", 1.0),
            "add_lookup_tags": result.get("tags", ""),
            "add_market_name": asset_name,
            "add_market_symbol": resolved_symbol,
            "add_market_current_price": (
                current_price
            ),
        }
    )


def _render_autofill_result(
    exchange_rates: dict[str, float],
    fallback_currency: str,
) -> None:
    """조회된 종목정보를 미리보기 형태로 표시합니다."""

    if not st.session_state.get(
        "add_lookup_success",
        False,
    ):
        return

    asset_name = safe_text(
        st.session_state.get(
            "add_lookup_name"
        )
    )

    symbol = safe_text(
        st.session_state.get(
            "add_lookup_symbol"
        )
    )

    price = _safe_float(
        st.session_state.get(
            "add_lookup_price"
        )
    )

    result_currency = safe_text(
        st.session_state.get(
            "add_lookup_currency"
        )
        or fallback_currency
    ).upper()

    exchange = safe_text(
        st.session_state.get(
            "add_lookup_exchange"
        )
    )

    sector = safe_text(
        st.session_state.get(
            "add_lookup_sector"
        )
    )

    industry = safe_text(
        st.session_state.get(
            "add_lookup_industry"
        )
    )

    price_krw = convert_to_krw(
        price,
        result_currency,
        exchange_rates,
    )

    st.success(
        "종목정보 자동조회에 성공했습니다. "
        "아래 정보가 자산등록 폼에 반영되었습니다."
    )

    col1, col2, col3, col4 = (
        st.columns(4)
    )

    col1.metric(
        "자산명",
        asset_name or "정보 없음",
    )

    col2.metric(
        "티커",
        symbol or "정보 없음",
    )

    col3.metric(
        "현재가",
        format_currency_value(
            price,
            result_currency,
        ),
    )

    col4.metric(
        "원화 환산가격",
        (
            f"₩ {price_krw:,.0f}"
            if price_krw is not None
            else "환율 조회 실패"
        ),
    )

    detail_parts: list[str] = []

    if exchange:
        detail_parts.append(
            f"거래소: {exchange}"
        )

    if sector:
        detail_parts.append(
            f"섹터: {sector}"
        )

    if industry:
        detail_parts.append(
            f"산업: {industry}"
        )

    if result_currency:
        detail_parts.append(
            f"통화: {result_currency}"
        )

    if detail_parts:
        st.caption(
            " · ".join(
                detail_parts
            )
        )

    warnings = st.session_state.get(
        "add_lookup_warnings",
    "add_lookup_country",
    "add_lookup_asset_class",
    "add_lookup_is_cash",
    "add_lookup_is_leverage",
    "add_lookup_is_inverse",
    "add_lookup_leverage_multiple",
    "add_lookup_tags",
        [],
    )

    if isinstance(
        warnings,
        list,
    ):

        for warning in warnings:
            if warning:
                st.warning(
                    str(warning)
                )


def _render_asset_autofill(
    asset_type: str,
    currency: str,
    exchange_rates: dict[str, float],
) -> None:
    """티커 기반 자산정보 자동입력 영역을 표시합니다."""

    if asset_type not in AUTO_PRICE_ASSET_TYPES:
        return

    st.markdown(
        "#### 🔎 종목정보 자동입력"
    )

    st.caption(
        "종목코드 또는 티커를 입력하면 "
        "자산명, 현재가, 통화와 거래소 정보를 자동으로 채웁니다."
    )

    lookup_col, button_col = st.columns(
        [3, 1]
    )

    with lookup_col:

        lookup_input = st.text_input(
            "종목코드 또는 티커",
            placeholder=get_symbol_placeholder(
                asset_type
            ),
            key=(
                f"add_lookup_input_"
                f"{asset_type}"
            ),
        )

    with button_col:

        st.write("")

        clicked = st.button(
            "종목정보 조회",
            type="primary",
            use_container_width=True,
            key=(
                f"add_lookup_button_"
                f"{asset_type}"
            ),
        )

    if clicked:

        normalized_symbol = (
            lookup_input
            .strip()
            .upper()
        )

        if not normalized_symbol:

            st.warning(
                "종목코드 또는 티커를 입력해 주세요."
            )

        else:

            with st.spinner(
                "종목명과 현재가를 조회하고 있습니다..."
            ):

                result = build_asset_autofill(
                    asset_type=asset_type,
                    symbol=normalized_symbol,
                )

            if result.get(
                "success",
                False,
            ):

                _store_autofill_result(
                    result
                )

            else:

                _clear_autofill_state()

                st.error(
                    result.get(
                        "message",
                        "종목정보 조회에 실패했습니다.",
                    )
                )

    _render_autofill_result(
        exchange_rates=exchange_rates,
        fallback_currency=currency,
    )


def render_add_asset_tab(
    exchange_rates: dict[str, float],
) -> None:
    """새 자산 등록 화면을 표시합니다."""

    st.subheader(
        "새 자산 등록"
    )

    asset_type = st.selectbox(
        "자산 종류",
        ASSET_TYPES,
        key="add_asset_type",
    )

    previous_type = st.session_state.get(
        "previous_add_type"
    )

    if (
        previous_type is not None
        and previous_type != asset_type
    ):
        _clear_autofill_state()

    st.session_state[
        "previous_add_type"
    ] = asset_type

    currency = _resolve_currency(
        asset_type
    )

    if currency != "KRW":

        rate = exchange_rates.get(
            currency
        )

        if rate is not None:

            st.caption(
                f"1 {currency} = "
                f"₩ {rate:,.2f}"
            )

        else:

            st.warning(
                f"{currency}/KRW 환율을 "
                "불러오지 못했습니다."
            )

    _render_asset_autofill(
        asset_type=asset_type,
        currency=currency,
        exchange_rates=exchange_rates,
    )

    price_step = _get_price_step(
        asset_type,
        currency,
    )

    price_format = _get_price_format(
        asset_type,
        currency,
    )

    with st.form(
        "add_asset_form",
        clear_on_submit=True,
    ):

        name = ""
        symbol = ""
        memo = ""

        quantity = 1.0
        average_price = 0.0
        current_price = 0.0

        left, right = st.columns(2)

        # ==========================================
        # 시장성 자산
        # ==========================================

        if asset_type in MARKET_ASSET_TYPES:

            with left:

                name = st.text_input(
                    "자산명",
                    value=safe_text(
                        st.session_state.get(
                            "add_market_name",
                            "",
                        )
                    ),
                    placeholder=(
                        "예: 비트코인"
                        if asset_type == "코인"
                        else (
                            "예: 삼성전자, "
                            "SGOV, NVIDIA"
                        )
                    ),
                )

                symbol = st.text_input(
                    "종목코드 또는 티커",
                    value=safe_text(
                        st.session_state.get(
                            "add_market_symbol",
                            "",
                        )
                    ),
                    placeholder=(
                        get_symbol_placeholder(
                            asset_type
                        )
                    ),
                )

                quantity = st.number_input(
                    "보유수량",
                    min_value=0.0,
                    value=0.0,
                    step=get_quantity_step(
                        asset_type
                    ),
                    format=get_quantity_format(
                        asset_type
                    ),
                )

                st.caption(
                    "입력 수량: "
                    f"{format_quantity_value(quantity, asset_type)}"
                )

            with right:

                average_price = st.number_input(
                    f"평균 매입단가 ({currency})",
                    min_value=0.0,
                    value=0.0,
                    step=price_step,
                    format=price_format,
                )

                current_price = st.number_input(
                    f"현재 가격 ({currency})",
                    min_value=0.0,
                    value=_safe_float(
                        st.session_state.get(
                            "add_market_current_price",
                            0.0,
                        )
                    ),
                    step=price_step,
                    format=price_format,
                )

                purchase_krw = convert_to_krw(
                    quantity * average_price,
                    currency,
                    exchange_rates,
                )

                value_krw = convert_to_krw(
                    quantity * current_price,
                    currency,
                    exchange_rates,
                )

                if (
                    purchase_krw is not None
                    and value_krw is not None
                ):

                    st.info(
                        "예상 매입금액: "
                        f"₩ {purchase_krw:,.0f}"
                        "\n\n"
                        "예상 평가금액: "
                        f"₩ {value_krw:,.0f}"
                    )

                memo = st.text_area(
                    "투자 메모"
                )

        # ==========================================
        # 현금·예금·계좌 자산
        # ==========================================

        elif asset_type in ACCOUNT_ASSET_TYPES:

            with left:

                name = st.text_input(
                    "은행·금융회사·계좌명",
                    placeholder=(
                        "예: 신한은행 외화예금"
                    ),
                )

                symbol = st.text_input(
                    "계좌번호 또는 구분명",
                    placeholder="선택 입력",
                )

            with right:

                balance = st.number_input(
                    f"현재 잔액 ({currency})",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    format="%.0f",
                )

                balance_krw = convert_to_krw(
                    balance,
                    currency,
                    exchange_rates,
                )

                if balance_krw is not None:

                    st.success(
                        "원화 환산금액: "
                        f"₩ {balance_krw:,.0f}"
                    )

                quantity = 1.0
                average_price = balance
                current_price = balance

                memo = st.text_area(
                    "메모"
                )

        # ==========================================
        # 부동산
        # ==========================================

        elif asset_type == "부동산":

            currency = "KRW"

            with left:

                name = st.text_input(
                    "부동산명"
                )

                symbol = st.text_input(
                    "동·호수 또는 구분명"
                )

                purchase_price = st.number_input(
                    "매입가격",
                    min_value=0.0,
                    value=0.0,
                    step=1_000_000.0,
                    format="%.0f",
                )

            with right:

                market_price = st.number_input(
                    "현재 추정 시세",
                    min_value=0.0,
                    value=0.0,
                    step=1_000_000.0,
                    format="%.0f",
                )

                loan_amount = st.number_input(
                    "대출금 또는 반환예정 보증금",
                    min_value=0.0,
                    value=0.0,
                    step=1_000_000.0,
                    format="%.0f",
                )

                st.info(
                    "부채 차감 후 추정 순가치: "
                    f"₩ {market_price - loan_amount:,.0f}"
                )

                note = st.text_area(
                    "부동산 메모"
                )

                quantity = 1.0
                average_price = purchase_price
                current_price = market_price

                memo = (
                    "대출금 또는 반환예정 보증금: "
                    f"{loan_amount:,.0f}원\n"
                    f"{note.strip()}"
                ).strip()

        # ==========================================
        # 기타 자산
        # ==========================================

        else:

            with left:

                name = st.text_input(
                    "자산명"
                )

                symbol = st.text_input(
                    "자산 구분"
                )

                quantity = st.number_input(
                    "수량",
                    min_value=0.0,
                    value=1.0,
                    step=1.0,
                    format="%.0f",
                )

            with right:

                average_price = st.number_input(
                    f"취득단가 ({currency})",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    format="%.0f",
                )

                current_price = st.number_input(
                    f"현재 평가단가 ({currency})",
                    min_value=0.0,
                    value=0.0,
                    step=1.0,
                    format="%.0f",
                )

                memo = st.text_area(
                    "메모"
                )

        submitted = st.form_submit_button(
            "자산 저장",
            type="primary",
            use_container_width=True,
        )

        if submitted:

            if not name.strip():

                st.error(
                    "자산명 또는 계좌명을 입력해 주세요."
                )

            elif quantity <= 0:

                st.error(
                    "수량은 0보다 커야 합니다."
                )

            elif (
                average_price < 0
                or current_price < 0
            ):

                st.error(
                    "가격은 음수가 될 수 없습니다."
                )

            else:

                metadata = {
                    "exchange": safe_text(st.session_state.get("add_lookup_exchange", "")),
                    "sector": safe_text(st.session_state.get("add_lookup_sector", "")),
                    "industry": safe_text(st.session_state.get("add_lookup_industry", "")),
                    "country": safe_text(st.session_state.get("add_lookup_country", "")),
                    "asset_class": safe_text(st.session_state.get("add_lookup_asset_class", "")),
                    "is_cash": int(st.session_state.get("add_lookup_is_cash", 0) or 0),
                    "is_leverage": int(st.session_state.get("add_lookup_is_leverage", 0) or 0),
                    "is_inverse": int(st.session_state.get("add_lookup_is_inverse", 0) or 0),
                    "leverage_multiple": float(st.session_state.get("add_lookup_leverage_multiple", 1.0) or 1.0),
                    "data_source": "Yahoo Finance / AssetOS",
                    "tags": safe_text(st.session_state.get("add_lookup_tags", "")),
                }

                add_asset(
                    asset_type,
                    name.strip(),
                    symbol.strip().upper(),
                    float(quantity),
                    float(average_price),
                    float(current_price),
                    currency,
                    memo.strip(),
                    metadata=metadata,
                )

                saved_name = name.strip()

                clear_portfolio_analysis_cache()
                _clear_autofill_state()

                st.success(
                    f"{saved_name} 자산이 저장되었습니다."
                )

                st.rerun()
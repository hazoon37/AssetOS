from __future__ import annotations

from typing import Any

import streamlit as st

from services.asset_metadata_service import (
    get_asset_metadata,
)
from services.dart_service import (
    get_dart_company_data,
)

from services.financial_metrics import (
    calculate_debt_ratio,
    calculate_growth,
    calculate_margin,
    calculate_pbr,
    calculate_per,
    calculate_psr,
    calculate_roa,
    calculate_roe,
)

def safe_float(
    value: Any,
) -> float | None:
    """숫자로 변환할 수 없으면 None을 반환합니다."""

    if value is None:
        return None

    try:
        return float(value)

    except (TypeError, ValueError):
        return None


def get_account_amount(
    summary: dict[str, Any],
    account_name: str,
    amount_key: str = "current_amount",
) -> float | None:
    """DART 재무요약에서 특정 계정 금액을 꺼냅니다."""

    account = summary.get(
        account_name
    )

    if not isinstance(
        account,
        dict,
    ):
        return None

    return safe_float(
        account.get(
            amount_key
        )
    )


def make_failure_result(
    message: str,
    stock_code: str,
) -> dict[str, Any]:
    """실패 시 반환할 공통 구조입니다."""

    return {
        "success": False,
        "message": message,
        "stock_code": stock_code,
        "company_name": None,
        "business_year": None,
        "market": {},
        "financials": {},
        "calculated": {},
        "reference": {},
        "warnings": [],
    }


@st.cache_data(
    ttl=600,
    show_spinner=False,
)
def analyze_korean_stock(
    stock_code: str,
) -> dict[str, Any]:
    """
    Yahoo 시장정보와 OpenDART 재무정보를 결합하여
    국내주식 가치·수익성·안정성 지표를 계산합니다.
    """

    normalized_code = (
        stock_code.strip()
        .upper()
        .replace(".KS", "")
        .replace(".KQ", "")
    )

    if not (
        normalized_code.isdigit()
        and len(normalized_code) == 6
    ):

        return make_failure_result(
            message=(
                "국내주식 종목코드는 "
                "6자리 숫자로 입력해 주세요."
            ),
            stock_code=normalized_code,
        )

    # ==============================================
    # 1. Yahoo Finance 시장정보
    # ==============================================

    market_result = get_asset_metadata(
        asset_type="국내주식",
        symbol=normalized_code,
        currency="KRW",
    )

    # ==============================================
    # 2. OpenDART 공식 재무정보
    # ==============================================

    dart_result = get_dart_company_data(
        stock_code=normalized_code,
    )

    if not dart_result.get(
        "success"
    ):

        return make_failure_result(
            message=(
                "OpenDART 재무정보 조회에 실패했습니다. "
                f"{dart_result.get('message', '')}"
            ),
            stock_code=normalized_code,
        )

    corporation = dart_result.get(
        "corporation",
        {},
    )

    financial_result = dart_result.get(
        "financials",
        {},
    )

    if not financial_result.get(
        "success"
    ):

        return make_failure_result(
            message=financial_result.get(
                "message",
                "DART 재무정보를 찾지 못했습니다.",
            ),
            stock_code=normalized_code,
        )

    summary = financial_result.get(
        "summary",
        {},
    )

    # ==============================================
    # 3. DART 재무계정 추출
    # ==============================================

    revenue = get_account_amount(
        summary,
        "매출액",
    )

    previous_revenue = get_account_amount(
        summary,
        "매출액",
        "previous_amount",
    )

    operating_income = get_account_amount(
        summary,
        "영업이익",
    )

    previous_operating_income = get_account_amount(
        summary,
        "영업이익",
        "previous_amount",
    )

    net_income = get_account_amount(
        summary,
        "당기순이익",
    )

    previous_net_income = get_account_amount(
        summary,
        "당기순이익",
        "previous_amount",
    )

    total_assets = get_account_amount(
        summary,
        "자산총계",
    )

    total_liabilities = get_account_amount(
        summary,
        "부채총계",
    )

    total_equity = get_account_amount(
        summary,
        "자본총계",
    )

    previous_equity = get_account_amount(
        summary,
        "자본총계",
        "previous_amount",
    )

    # ==============================================
    # 4. 시장정보 추출
    # ==============================================

    market_cap = None
    current_price = None
    shares_outstanding = None

    if market_result.get(
        "success"
    ):

        market_cap = safe_float(
            market_result.get(
                "market_cap"
            )
        )

        current_price = safe_float(
            market_result.get(
                "price"
            )
        )

        raw_info = (
            market_result.get(
                "raw",
                {},
            )
            .get(
                "info",
                {},
            )
        )

        if isinstance(
            raw_info,
            dict,
        ):

            shares_outstanding = safe_float(
                raw_info.get(
                    "sharesOutstanding"
                )
                or raw_info.get(
                    "impliedSharesOutstanding"
                )
            )

    # 시가총액이 없고 현재가·주식 수가 있으면 계산
    if (
        market_cap is None
        and current_price is not None
        and shares_outstanding is not None
    ):

        market_cap = (
            current_price
            * shares_outstanding
        )

    # ==============================================
    # 5. 평균 자기자본
    # ==============================================

    average_equity = None

    if (
        total_equity is not None
        and previous_equity is not None
    ):

        average_equity = (
            total_equity
            + previous_equity
        ) / 2

    elif total_equity is not None:

        average_equity = total_equity

    # ==============================================
    # 6. AssetOS 공통 재무지표 계산
    # ==============================================

    per_result = calculate_per(
        market_cap=market_cap,
        net_income=net_income,
    )

    pbr_result = calculate_pbr(
        market_cap=market_cap,
        equity=total_equity,
    )

    psr_result = calculate_psr(
        market_cap=market_cap,
        revenue=revenue,
    )

    roe_result = calculate_roe(
        net_income=net_income,
        current_equity=total_equity,
        previous_equity=previous_equity,
    )

    roa_result = calculate_roa(
        net_income=net_income,
        total_assets=total_assets,
    )

    debt_ratio_result = calculate_debt_ratio(
        liabilities=total_liabilities,
        equity=total_equity,
    )

    operating_margin_result = calculate_margin(
        profit=operating_income,
        revenue=revenue,
        profit_name="영업이익",
    )

    net_margin_result = calculate_margin(
        profit=net_income,
        revenue=revenue,
        profit_name="당기순이익",
    )

    revenue_growth_result = calculate_growth(
        current_value=revenue,
        previous_value=previous_revenue,
        item_name="매출액",
    )

    operating_income_growth_result = calculate_growth(
        current_value=operating_income,
        previous_value=previous_operating_income,
        item_name="영업이익",
    )

    net_income_growth_result = calculate_growth(
        current_value=net_income,
        previous_value=previous_net_income,
        item_name="당기순이익",
    )

    debt_to_assets = None

    if (
        total_liabilities is not None
        and total_assets not in (None, 0)
    ):
        debt_to_assets = (
            total_liabilities
            / total_assets
        )

    eps = None
    bps = None
    price_based_per = None
    price_based_pbr = None

    if shares_outstanding not in (None, 0):

        if net_income is not None:
            eps = (
                net_income
                / shares_outstanding
            )

        if total_equity is not None:
            bps = (
                total_equity
                / shares_outstanding
            )

    if (
        current_price is not None
        and eps is not None
        and eps > 0
    ):
        price_based_per = (
            current_price / eps
        )

    if (
        current_price is not None
        and bps is not None
        and bps > 0
    ):
        price_based_pbr = (
            current_price / bps
        )

    # ==============================================
    # 7. Yahoo 참고값
    # ==============================================

    reference = {
        "yahoo_per": safe_float(
            market_result.get(
                "trailing_pe"
            )
        ),
        "yahoo_forward_per": safe_float(
            market_result.get(
                "forward_pe"
            )
        ),
        "yahoo_pbr": safe_float(
            market_result.get(
                "price_to_book"
            )
        ),
        "yahoo_roe": safe_float(
            market_result.get(
                "return_on_equity"
            )
        ),
        "yahoo_operating_margin": safe_float(
            market_result.get(
                "operating_margin"
            )
        ),
        "yahoo_profit_margin": safe_float(
            market_result.get(
                "profit_margin"
            )
        ),
    }

    # ==============================================
    # 8. 경고 및 데이터 품질 안내
    # ==============================================

    warnings: list[str] = []
    
    metric_results = {
        "PER": per_result,
        "PBR": pbr_result,
        "PSR": psr_result,
        "ROE": roe_result,
        "ROA": roa_result,
        "부채비율": debt_ratio_result,
        "영업이익률": operating_margin_result,
        "순이익률": net_margin_result,
        "매출 성장률": revenue_growth_result,
        "영업이익 성장률": operating_income_growth_result,
        "순이익 성장률": net_income_growth_result,
    }

    for metric_name, metric_result in (
        metric_results.items()
    ):

        warning = metric_result.get(
            "warning"
        )

        if warning:
            warnings.append(
                f"{metric_name}: {warning}"
            )

    if market_cap is None:

        warnings.append(
            "Yahoo Finance에서 시가총액을 가져오지 못해 "
            "PER·PBR·PSR 계산이 제한됩니다."
        )

    if shares_outstanding is None:

        warnings.append(
            "상장주식 수를 가져오지 못해 "
            "EPS·BPS 직접 계산이 제한됩니다."
        )

    if net_income is not None and net_income <= 0:

        warnings.append(
            "당기순이익이 0 이하이므로 "
            "PER 해석에 주의해야 합니다."
        )

    warnings.append(
        "DART 재무정보는 최근 사업보고서 기준이고, "
        "시장가격은 최근 가격이므로 기준 시점이 서로 다를 수 있습니다."
    )

    warnings.append(
        "현재 계산은 총 당기순이익과 총 자본을 사용한 기본 버전입니다. "
        "향후 지배주주 순이익·지배주주지분 기준으로 고도화할 예정입니다."
    )

    return {
        "success": True,
        "message": "",
        "stock_code": normalized_code,
        "company_name": (
            corporation.get(
                "corp_name"
            )
            or market_result.get(
                "name"
            )
            or normalized_code
        ),
        "business_year": financial_result.get(
            "business_year"
        ),
        "market": {
            "current_price": current_price,
            "market_cap": market_cap,
            "shares_outstanding": shares_outstanding,
            "currency": market_result.get(
                "currency",
                "KRW",
            ),
            "resolved_symbol": market_result.get(
                "resolved_symbol"
            ),
        },
        "financials": {
            "revenue": revenue,
            "previous_revenue": previous_revenue,
            "operating_income": operating_income,
            "previous_operating_income": (
                previous_operating_income
            ),
            "net_income": net_income,
            "previous_net_income": previous_net_income,
            "total_assets": total_assets,
            "total_liabilities": total_liabilities,
            "total_equity": total_equity,
            "previous_equity": previous_equity,
            "average_equity": average_equity,
        },
                "calculated": {
            "per": per_result.get("value"),
            "pbr": pbr_result.get("value"),
            "psr": psr_result.get("value"),
            "price_based_per": price_based_per,
            "price_based_pbr": price_based_pbr,
            "eps": eps,
            "bps": bps,
            "roe": roe_result.get("value"),
            "roa": roa_result.get("value"),
            "debt_ratio": debt_ratio_result.get("value"),
            "debt_to_assets": debt_to_assets,
            "operating_margin": (
                operating_margin_result.get("value")
            ),
            "net_margin": net_margin_result.get("value"),
            "revenue_growth": (
                revenue_growth_result.get("value")
            ),
            "operating_income_growth": (
                operating_income_growth_result.get("value")
            ),
            "net_income_growth": (
                net_income_growth_result.get("value")
            ),
        },
        "reference": reference,
        "warnings": warnings,
        "sources": {
            "market": "Yahoo Finance",
            "financials": "OpenDART",
            "calculation": "AssetOS",
        },
        
        "metric_details": {
            "per": per_result,
            "pbr": pbr_result,
            "psr": psr_result,
            "roe": roe_result,
            "roa": roa_result,
            "debt_ratio": debt_ratio_result,
            "operating_margin": operating_margin_result,
            "net_margin": net_margin_result,
            "revenue_growth": revenue_growth_result,
            "operating_income_growth": (
                operating_income_growth_result
            ),
            "net_income_growth": (
                net_income_growth_result
            ),
        },
    }
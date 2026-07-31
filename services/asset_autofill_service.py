from __future__ import annotations

from typing import Any

from services.company_service import (
    analyze_company,
)
from services.asset_classification import classify_asset


SUPPORTED_ASSET_TYPES = {
    "국내주식",
    "미국주식",
    "국내ETF",
    "미국ETF",
    "코인",
}


def safe_float(
    value: Any,
) -> float | None:
    """값을 안전하게 실수로 변환합니다."""

    if value is None:
        return None

    try:
        return float(value)

    except (TypeError, ValueError):
        return None


def make_failure_result(
    message: str,
    asset_type: str,
    symbol: str,
) -> dict[str, Any]:
    """자동입력 조회 실패 결과입니다."""

    return {
        "success": False,
        "message": message,
        "asset_type": asset_type,
        "symbol": symbol,
        "asset_name": "",
        "current_price": None,
        "currency": "",
        "exchange": "",
        "sector": "",
        "industry": "",
        "resolved_symbol": "",
        "analysis": None,
        "warnings": [],
    }


def build_asset_autofill(
    *,
    asset_type: str,
    symbol: str,
) -> dict[str, Any]:
    """
    티커를 조회해 자산등록 화면에서 사용할
    자동입력 데이터를 반환합니다.
    """

    normalized_asset_type = str(
        asset_type or ""
    ).strip()

    normalized_symbol = str(
        symbol or ""
    ).strip().upper()

    if normalized_asset_type not in SUPPORTED_ASSET_TYPES:

        return make_failure_result(
            message=(
                "자동조회가 지원되지 않는 자산 종류입니다."
            ),
            asset_type=normalized_asset_type,
            symbol=normalized_symbol,
        )

    if not normalized_symbol:

        return make_failure_result(
            message=(
                "종목코드 또는 티커를 입력해 주세요."
            ),
            asset_type=normalized_asset_type,
            symbol=normalized_symbol,
        )

    analysis = analyze_company(
        asset_type=normalized_asset_type,
        symbol=normalized_symbol,
    )

    if not analysis.get(
        "success",
        False,
    ):

        return make_failure_result(
            message=analysis.get(
                "message",
                "종목정보 자동조회에 실패했습니다.",
            ),
            asset_type=normalized_asset_type,
            symbol=normalized_symbol,
        )

    metadata = analysis.get(
        "metadata"
    ) or {}

    if not metadata.get(
        "success",
        False,
    ):

        return make_failure_result(
            message=metadata.get(
                "message",
                "종목 기본정보를 가져오지 못했습니다.",
            ),
            asset_type=normalized_asset_type,
            symbol=normalized_symbol,
        )

    resolved_symbol = str(
        metadata.get(
            "resolved_symbol"
        )
        or normalized_symbol
    ).strip().upper()

    asset_name = str(
        metadata.get("name")
        or resolved_symbol
    ).strip()

    currency = str(
        metadata.get(
            "currency"
        )
        or analysis.get(
            "currency"
        )
        or ""
    ).strip().upper()

    exchange = str(
        metadata.get(
            "exchange"
        )
        or ""
    ).strip()

    sector = str(
        metadata.get(
            "sector"
        )
        or ""
    ).strip()

    industry = str(
        metadata.get(
            "industry"
        )
        or ""
    ).strip()

    current_price = safe_float(
        metadata.get(
            "price"
        )
    )

    warnings = analysis.get(
        "warnings",
        [],
    )

    if not isinstance(
        warnings,
        list,
    ):
        warnings = []

    if current_price is None:

        warnings.append(
            "현재가를 가져오지 못했습니다. "
            "등록 전에 현재가를 직접 확인해 주세요."
        )

    if not currency:

        warnings.append(
            "거래통화를 확인하지 못했습니다."
        )

    classification = classify_asset(
        asset_type=normalized_asset_type,
        symbol=resolved_symbol,
        currency=currency,
        exchange=exchange,
        sector=sector,
        industry=industry,
    )

    return {
        "success": True,
        "message": "",
        "asset_type": normalized_asset_type,
        "symbol": normalized_symbol,
        "asset_name": asset_name,
        "current_price": current_price,
        "currency": currency,
        "exchange": exchange,
        "sector": sector,
        "industry": industry,
        "resolved_symbol": resolved_symbol,
        **classification,
        "analysis": analysis,
        "warnings": list(
            dict.fromkeys(
                str(warning)
                for warning in warnings
                if warning
            )
        ),
    }
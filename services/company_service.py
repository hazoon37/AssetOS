from __future__ import annotations

from typing import Any

from services.analysis_engine import (
    analyze_korean_stock,
)
from services.asset_metadata_service import (
    get_asset_metadata,
)
from services.asset_resolver import AssetResolution, resolve_asset
from services.exchange_rate_service import (
    get_exchange_rates_to_krw,
)

SUPPORTED_ASSET_TYPES = {
    "국내주식",
    "미국주식",
    "국내ETF",
    "미국ETF",
    "코인",
}


DEFAULT_CURRENCIES = {
    "국내주식": "KRW",
    "미국주식": "USD",
    "국내ETF": "KRW",
    "미국ETF": "USD",
    "코인": "USD",
}


def normalize_symbol(
    symbol: str,
) -> str:
    """종목코드 또는 티커를 표준 형태로 정리합니다."""

    return str(
        symbol or ""
    ).strip().upper()


def validate_request(
    asset_type: str,
    symbol: str,
) -> str | None:
    """종목분석 요청값을 검사하고 오류 문구를 반환합니다."""

    if asset_type not in SUPPORTED_ASSET_TYPES:
        return (
            f"지원하지 않는 자산 종류입니다: "
            f"{asset_type or '정보 없음'}"
        )

    if not symbol:
        return "종목코드 또는 티커를 입력해 주세요."

    if asset_type in {"국내주식", "국내ETF"} and not (
        symbol.isdigit()
        and len(symbol) == 6
    ):
        return (
            "해당 키워드로는 검색이 불가합니다. "
            "국내주식과 국내ETF는 "
            "6자리 종목코드로 입력해 주세요."
        )

    return None


def make_failure_result(
    message: str,
    asset_type: str,
    symbol: str,
) -> dict[str, Any]:
    """종목 통합분석 실패 결과입니다."""

    return {
        "success": False,
        "message": message,
        "asset_type": asset_type,
        "symbol": symbol,
        "metadata": None,
        "exchange": None,
        "valuation": None,
        "warnings": [],
    }


def resolve_company_query(query: str) -> AssetResolution:
    """Resolve every company-search input through the shared Asset Resolver."""
    return resolve_asset(query)


def build_warnings(
    metadata: dict[str, Any],
    exchange: dict[str, Any],
    valuation: dict[str, Any] | None,
) -> list[str]:
    """하위 서비스의 오류와 경고를 하나의 목록으로 정리합니다."""

    warnings: list[str] = []

    if not metadata.get(
        "success",
        False,
    ):

        metadata_message = metadata.get(
            "message"
        )

        if metadata_message:
            warnings.append(
                f"종목정보: {metadata_message}"
            )

    if not exchange.get(
        "success",
        False,
    ):

        exchange_message = exchange.get(
            "message"
        )

        if exchange_message:
            warnings.append(
                f"환율정보: {exchange_message}"
            )

    if (
        valuation is not None
        and not valuation.get(
            "success",
            False,
        )
    ):

        valuation_message = valuation.get(
            "message"
        )

        if valuation_message:
            warnings.append(
                f"가치평가: {valuation_message}"
            )

    if valuation is not None:

        valuation_warnings = valuation.get(
            "warnings",
            [],
        )

        if isinstance(
            valuation_warnings,
            list,
        ):

            warnings.extend(
                str(warning)
                for warning in valuation_warnings
                if warning
            )

    # 중복 경고 제거
    return list(
        dict.fromkeys(warnings)
    )


def analyze_company(
    *,
    asset_type: str,
    symbol: str,
    currency: str | None = None,
) -> dict[str, Any]:
    """
    AssetOS 종목분석의 단일 진입점입니다.

    종목 기본정보, 환율정보와 국내주식 가치평가를
    하나의 공통 구조로 반환합니다.
    """

    normalized_asset_type = str(
        asset_type or ""
    ).strip()

    resolution = resolve_company_query(symbol)
    if resolution.status == "ambiguous":
        result = make_failure_result(
            message="여러 종목이 검색되었습니다. 분석할 종목을 선택해 주세요.",
            asset_type=normalized_asset_type,
            symbol=normalize_symbol(symbol),
        )
        result["resolution_status"] = "ambiguous"
        result["candidates"] = [
            {
                "ticker": candidate.ticker,
                "display_name": candidate.display_name,
                "exchange": candidate.exchange,
                "asset_type": candidate.asset_type,
                "currency": candidate.currency,
            }
            for candidate in resolution.candidates
        ]
        return result

    if resolution.success and resolution.asset is not None:
        resolved = resolution.asset
        normalized_asset_type = resolved.asset_type
        normalized_symbol = normalize_symbol(resolved.ticker)
        if normalized_asset_type in {"국내주식", "국내ETF"}:
            normalized_symbol = normalized_symbol.replace(".KS", "").replace(".KQ", "")
        currency = currency or resolved.currency
    else:
        normalized_symbol = normalize_symbol(symbol)

    validation_error = validate_request(
        asset_type=normalized_asset_type,
        symbol=normalized_symbol,
    )

    if validation_error:

        return make_failure_result(
            message=validation_error,
            asset_type=normalized_asset_type,
            symbol=normalized_symbol,
        )

    resolved_currency = str(
        currency
        or DEFAULT_CURRENCIES[
            normalized_asset_type
        ]
    ).strip().upper()

    # ==============================================
    # 기본 종목정보
    # ==============================================

    metadata = get_asset_metadata(
        asset_type=normalized_asset_type,
        symbol=normalized_symbol,
        currency=resolved_currency,
    )

    # ==============================================
    # 환율정보
    # ==============================================

    exchange = get_exchange_rates_to_krw()

    # ==============================================
    # 국내주식 가치평가
    # ==============================================

    valuation = None

    if normalized_asset_type == "국내주식":

        valuation = analyze_korean_stock(
            normalized_symbol
        )

        # 국내주식의 화면 지표는 AssetOS 직접 계산값을 단일 기준으로 사용합니다.
        # Yahoo 값은 valuation.reference에 검산용으로 보존합니다.
        if valuation.get("success"):
            calculated = valuation.get("calculated", {})
            metadata = dict(metadata)
            metadata.update(
                {
                    "trailing_pe": calculated.get("per"),
                    "price_to_book": calculated.get("pbr"),
                    "price_to_sales": calculated.get("psr"),
                    "return_on_equity": calculated.get("roe"),
                    "return_on_assets": calculated.get("roa"),
                    "operating_margin": calculated.get("operating_margin"),
                    "profit_margin": calculated.get("net_margin"),
                    "revenue_growth": calculated.get("revenue_growth"),
                    "metric_source": "AssetOS (OpenDART + Yahoo Finance)",
                }
            )

    warnings = build_warnings(
        metadata=metadata,
        exchange=exchange,
        valuation=valuation,
    )

    metadata_success = metadata.get(
        "success",
        False,
    )

    valuation_success = (
        True
        if valuation is None
        else valuation.get(
            "success",
            False,
        )
    )

    # 종목 기본정보가 실패하면 전체 요청을 실패로 처리합니다.
    # 국내주식 가치평가만 실패한 경우 기본정보는 계속 표시합니다.
    success = bool(
        metadata_success
    )

    message = ""

    if not metadata_success:

        message = metadata.get(
            "message",
            "종목정보 조회에 실패했습니다.",
        )

    elif not valuation_success:

        message = (
            "기본 종목정보는 조회했지만 "
            "국내주식 가치평가 일부를 불러오지 못했습니다."
        )

    return {
        "success": success,
        "message": message,
        "asset_type": normalized_asset_type,
        "symbol": normalized_symbol,
        "currency": resolved_currency,
        "metadata": metadata,
        "exchange": exchange,
        "valuation": valuation,
        "warnings": warnings,
        "status": {
            "metadata_success": bool(
                metadata_success
            ),
            "exchange_success": bool(
                exchange.get(
                    "success",
                    False,
                )
            ),
            "valuation_success": bool(
                valuation_success
            ),
        },
        "sources": {
            "metadata": "Yahoo Finance",
            "exchange": (
                exchange.get("source")
                or "환율 데이터 서비스"
            ),
            "valuation": (
                "OpenDART + Yahoo Finance + AssetOS"
                if valuation is not None
                else None
            ),
        },
    }

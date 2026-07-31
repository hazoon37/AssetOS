from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests
import streamlit as st
import yfinance as yf

from services.market_price_service import (
    COIN_ID_MAP,
    get_market_price,
    normalize_stock_ticker,
)


COINGECKO_API_URL = "https://api.coingecko.com/api/v3"

STOCK_ASSET_TYPES = [
    "국내주식",
    "미국주식",
]

ETF_ASSET_TYPES = [
    "국내ETF",
    "미국ETF",
]

SUPPORTED_ASSET_TYPES = [
    "미국주식",
    "미국ETF",
    "국내주식",
    "국내ETF",
    "코인",
]


# ==================================================
# 공통 유틸리티
# ==================================================

def safe_text(
    value: Any,
    default: str | None = None,
) -> str | None:
    """빈 문자열, None, NaN을 안전하게 처리합니다."""

    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except (TypeError, ValueError):
        pass

    text = str(value).strip()

    if not text:
        return default

    return text


def safe_float(
    value: Any,
) -> float | None:
    """값을 float로 변환하고 실패하면 None을 반환합니다."""

    if value is None:
        return None

    try:
        number = float(value)

        if pd.isna(number):
            return None

        return number

    except (TypeError, ValueError):
        return None


def safe_int(
    value: Any,
) -> int | None:
    """값을 int로 변환하고 실패하면 None을 반환합니다."""

    number = safe_float(value)

    if number is None:
        return None

    return int(round(number))


def first_available(
    source: dict[str, Any],
    keys: list[str],
    default: Any = None,
) -> Any:
    """여러 후보 키 중 값이 존재하는 첫 번째 항목을 반환합니다."""

    for key in keys:

        value = source.get(key)

        if value is None:
            continue

        try:
            if pd.isna(value):
                continue
        except (TypeError, ValueError):
            pass

        if isinstance(value, str) and not value.strip():
            continue

        return value

    return default


def normalize_percentage(
    value: Any,
) -> float | None:
    """
    배당수익률을 백분율 단위로 정리합니다.

    0.042 → 4.2
    4.2   → 4.2
    """

    number = safe_float(value)

    if number is None:
        return None

    if abs(number) <= 1:
        return number * 100

    return number


def dataframe_row_count(
    value: Any,
) -> int | None:
    """DataFrame 또는 유사 자료의 행 수를 반환합니다."""

    if isinstance(value, pd.DataFrame):

        if value.empty:
            return None

        return int(len(value))

    if isinstance(value, list):

        if not value:
            return None

        return len(value)

    if isinstance(value, dict):

        if not value:
            return None

        return len(value)

    return None


def make_json_safe(
    value: Any,
) -> Any:
    """st.json에서 표시할 수 있도록 값을 정리합니다."""

    if value is None:
        return None

    if isinstance(
        value,
        (
            str,
            int,
            float,
            bool,
        ),
    ):
        return value

    if isinstance(value, pd.DataFrame):

        return value.reset_index().to_dict(
            orient="records"
        )

    if isinstance(value, pd.Series):

        return value.to_dict()

    if isinstance(value, dict):

        return {
            str(key): make_json_safe(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple, set)):

        return [
            make_json_safe(item)
            for item in value
        ]

    if hasattr(value, "isoformat"):

        try:
            return value.isoformat()
        except Exception:
            pass

    return str(value)


def empty_result(
    message: str,
    asset_type: str,
    symbol: str,
) -> dict[str, Any]:
    """실패 시 반환할 공통 구조입니다."""

    return {
        "success": False,
        "message": message,
        "asset_type": asset_type,
        "symbol": symbol.strip().upper(),
        "resolved_symbol": None,
        "name": None,
        "price": None,
        "currency": None,
        "exchange": None,
        "quote_type": None,
        "sector": None,
        "industry": None,
        "market_cap": None,
        "dividend_yield": None,

        # 주식 가치평가 지표
        "trailing_pe": None,
        "forward_pe": None,
        "price_to_book": None,
        "price_to_sales": None,
        "enterprise_to_ebitda": None,

        # 주식 수익성 지표
        "return_on_equity": None,
        "return_on_assets": None,
        "operating_margin": None,
        "profit_margin": None,
        "gross_margin": None,

        # 주식 성장성·재무안정성
        "revenue_growth": None,
        "earnings_growth": None,
        "debt_to_equity": None,
        "current_ratio": None,
        "quick_ratio": None,

        # 시장 지표
        "beta": None,
        "fifty_two_week_high": None,
        "fifty_two_week_low": None,
        "target_mean_price": None,

        # ETF 전용
        "fund_family": None,
        "category": None,
        "holdings_count": None,

        # 코인 전용
        "coin_id": None,
        "change_24h": None,

        "homepage": None,
        "image_url": None,
        "description": None,
        "last_updated": None,
        "missing_fields": [],
        "raw": {},
    }


# ==================================================
# 국내·미국 주식 및 ETF
# ==================================================

def build_stock_candidates(
    ticker: str,
    asset_type: str,
) -> list[str]:
    """국내 종목은 코스피와 코스닥 후보를 함께 생성합니다."""

    normalized = normalize_stock_ticker(
        ticker=ticker,
        asset_type=asset_type,
    )

    candidates = [normalized]

    if (
        asset_type in [
            "국내주식",
            "국내ETF",
        ]
        and normalized.endswith(".KS")
    ):

        candidates.append(
            normalized.replace(
                ".KS",
                ".KQ",
            )
        )

    return list(dict.fromkeys(candidates))


def get_fund_details(
    ticker_object: yf.Ticker,
) -> dict[str, Any]:
    """
    ETF 전용 정보를 조회합니다.

    yfinance 또는 Yahoo 응답에 따라 일부 정보가 없을 수 있습니다.
    """

    result: dict[str, Any] = {
        "overview": {},
        "operations": {},
        "top_holdings": None,
        "holdings_count": None,
    }

    try:
        funds_data = ticker_object.funds_data
    except Exception:
        return result

    try:
        overview = funds_data.fund_overview

        if isinstance(overview, dict):
            result["overview"] = overview

    except Exception:
        pass

    try:
        operations = funds_data.fund_operations

        if isinstance(operations, dict):
            result["operations"] = operations
        elif isinstance(operations, pd.DataFrame):
            result["operations"] = (
                operations.to_dict()
            )

    except Exception:
        pass

    try:
        top_holdings = funds_data.top_holdings

        result["top_holdings"] = top_holdings
        result["holdings_count"] = (
            dataframe_row_count(
                top_holdings
            )
        )

    except Exception:
        pass

    return result


@st.cache_data(
    ttl=600,
    show_spinner=False,
)
def get_stock_or_etf_metadata(
    asset_type: str,
    symbol: str,
) -> dict[str, Any]:
    """국내·미국 주식 또는 ETF의 메타데이터를 조회합니다."""

    normalized_input = symbol.strip().upper()

    if not normalized_input:

        return empty_result(
            message="종목코드 또는 티커를 입력해 주세요.",
            asset_type=asset_type,
            symbol=symbol,
        )

    candidates = build_stock_candidates(
        ticker=normalized_input,
        asset_type=asset_type,
    )

    last_error = ""

    for candidate in candidates:

        try:
            ticker_object = yf.Ticker(
                candidate
            )

            info = ticker_object.get_info()

            if not isinstance(info, dict):
                info = {}

            price_result = get_market_price(
                asset_type=asset_type,
                symbol=candidate,
                currency=(
                    "KRW"
                    if asset_type
                    in ["국내주식", "국내ETF"]
                    else "USD"
                ),
            )

            name = safe_text(
                first_available(
                    info,
                    [
                        "longName",
                        "shortName",
                        "displayName",
                    ],
                )
            )

            if (
                not name
                and not price_result.get(
                    "success"
                )
            ):
                continue

            price = None
            resolved_symbol = candidate
            currency = safe_text(
                info.get("currency")
            )

            if price_result.get("success"):

                price = safe_float(
                    price_result.get("price")
                )

                resolved_symbol = safe_text(
                    price_result.get("ticker"),
                    candidate,
                ) or candidate

                currency = safe_text(
                    price_result.get("currency"),
                    currency,
                )

            if price is None:

                price = safe_float(
                    first_available(
                        info,
                        [
                            "currentPrice",
                            "regularMarketPrice",
                            "navPrice",
                            "previousClose",
                        ],
                    )
                )

            if currency is None:

                currency = (
                    "KRW"
                    if asset_type
                    in ["국내주식", "국내ETF"]
                    else "USD"
                )

            exchange = safe_text(
                first_available(
                    info,
                    [
                        "fullExchangeName",
                        "exchange",
                        "market",
                    ],
                )
            )

            quote_type = safe_text(
                info.get("quoteType")
            )

            sector = safe_text(
                info.get("sector")
            )

            industry = safe_text(
                info.get("industry")
            )

            market_cap = safe_float(
                info.get("marketCap")
            )

                        # --------------------------------------
            # 가치평가 지표
            # --------------------------------------

            trailing_pe = safe_float(
                info.get("trailingPE")
            )

            forward_pe = safe_float(
                info.get("forwardPE")
            )

            price_to_book = safe_float(
                info.get("priceToBook")
            )

            price_to_sales = safe_float(
                first_available(
                    info,
                    [
                        "priceToSalesTrailing12Months",
                        "priceToSales",
                    ],
                )
            )

            enterprise_to_ebitda = safe_float(
                info.get("enterpriseToEbitda")
            )

            # --------------------------------------
            # 수익성 지표
            # Yahoo 값은 보통 0.15 = 15% 형태입니다.
            # --------------------------------------

            return_on_equity = safe_float(
                info.get("returnOnEquity")
            )

            return_on_assets = safe_float(
                info.get("returnOnAssets")
            )

            operating_margin = safe_float(
                info.get("operatingMargins")
            )

            profit_margin = safe_float(
                info.get("profitMargins")
            )

            gross_margin = safe_float(
                info.get("grossMargins")
            )

            # --------------------------------------
            # 성장성 및 재무안정성
            # --------------------------------------

            revenue_growth = safe_float(
                info.get("revenueGrowth")
            )

            earnings_growth = safe_float(
                info.get("earningsGrowth")
            )

            debt_to_equity = safe_float(
                info.get("debtToEquity")
            )

            current_ratio = safe_float(
                info.get("currentRatio")
            )

            quick_ratio = safe_float(
                info.get("quickRatio")
            )

            # --------------------------------------
            # 시장 지표
            # --------------------------------------

            beta = safe_float(
                info.get("beta")
            )

            fifty_two_week_high = safe_float(
                info.get("fiftyTwoWeekHigh")
            )

            fifty_two_week_low = safe_float(
                info.get("fiftyTwoWeekLow")
            )

            target_mean_price = safe_float(
                info.get("targetMeanPrice")
            )
            
            dividend_yield = (
                normalize_percentage(
                    first_available(
                        info,
                        [
                            "dividendYield",
                            "trailingAnnualDividendYield",
                            "yield",
                        ],
                    )
                )
            )

            fund_family = safe_text(
                first_available(
                    info,
                    [
                        "fundFamily",
                        "legalType",
                    ],
                )
            )

            category = safe_text(
                first_available(
                    info,
                    [
                        "category",
                        "fundInceptionDate",
                    ],
                )
            )

            holdings_count = safe_int(
                first_available(
                    info,
                    [
                        "holdingsCount",
                        "numberOfHoldings",
                        "totalHoldings",
                    ],
                )
            )

            fund_details: dict[str, Any] = {}

            if asset_type in ETF_ASSET_TYPES:

                fund_details = get_fund_details(
                    ticker_object
                )

                overview = fund_details.get(
                    "overview",
                    {},
                )

                if (
                    not fund_family
                    and isinstance(overview, dict)
                ):
                    fund_family = safe_text(
                        first_available(
                            overview,
                            [
                                "family",
                                "fundFamily",
                                "legalType",
                            ],
                        )
                    )

                if (
                    not category
                    and isinstance(overview, dict)
                ):
                    category = safe_text(
                        first_available(
                            overview,
                            [
                                "category",
                                "categoryName",
                            ],
                        )
                    )

                if holdings_count is None:

                    holdings_count = safe_int(
                        fund_details.get(
                            "holdings_count"
                        )
                    )

            description = safe_text(
                first_available(
                    info,
                    [
                        "longBusinessSummary",
                        "description",
                    ],
                )
            )

            homepage = safe_text(
                first_available(
                    info,
                    [
                        "website",
                        "fundFamilyUrl",
                    ],
                )
            )

            missing_fields: list[str] = []

            common_checks = {
                "자산명": name,
                "현재가": price,
                "통화": currency,
                "거래소": exchange,
            }

            for label, value in (
                common_checks.items()
            ):

                if value is None:
                    missing_fields.append(
                        label
                    )
            if asset_type in STOCK_ASSET_TYPES:

                stock_checks = {
                    "섹터": sector,
                    "산업": industry,
                    "시가총액": market_cap,
                    "배당수익률": dividend_yield,
                    "PER": trailing_pe,
                    "Forward PER": forward_pe,
                    "PBR": price_to_book,
                    "PSR": price_to_sales,
                    "EV/EBITDA": enterprise_to_ebitda,
                    "ROE": return_on_equity,
                    "영업이익률": operating_margin,
                    "순이익률": profit_margin,
                    "매출 성장률": revenue_growth,
                    "이익 성장률": earnings_growth,
                    "부채비율": debt_to_equity,
                    "베타": beta,
                    "52주 고가": fifty_two_week_high,
                    "52주 저가": fifty_two_week_low,
                }

                for label, value in (
                    stock_checks.items()
                ):

                    if value is None:
                        missing_fields.append(
                            label
                        )


            if asset_type in ETF_ASSET_TYPES:

                etf_checks = {
                    "운용사·펀드 패밀리": fund_family,
                    "ETF 카테고리": category,
                    "배당수익률": dividend_yield,
                    "보유 종목 수": holdings_count,
                }

                for label, value in (
                    etf_checks.items()
                ):

                    if value is None:
                        missing_fields.append(
                            label
                        )

            raw_data = {
                "info": info,
                "fund_details": fund_details,
            }

            return {
                "success": True,
                "message": "",
                "asset_type": asset_type,
                "symbol": normalized_input,
                "resolved_symbol": resolved_symbol,
                "name": name or resolved_symbol,
                "price": price,
                "currency": currency,
                "exchange": exchange,
                "quote_type": quote_type,
                "sector": sector,
                "industry": industry,
                "market_cap": market_cap,
                "dividend_yield": dividend_yield,

                # 가치평가
                "trailing_pe": trailing_pe,
                "forward_pe": forward_pe,
                "price_to_book": price_to_book,
                "price_to_sales": price_to_sales,
                "enterprise_to_ebitda": enterprise_to_ebitda,

                # 수익성
                "return_on_equity": return_on_equity,
                "return_on_assets": return_on_assets,
                "operating_margin": operating_margin,
                "profit_margin": profit_margin,
                "gross_margin": gross_margin,

                # 성장성·재무안정성
                "revenue_growth": revenue_growth,
                "earnings_growth": earnings_growth,
                "debt_to_equity": debt_to_equity,
                "current_ratio": current_ratio,
                "quick_ratio": quick_ratio,

                # 시장 지표
                "beta": beta,
                "fifty_two_week_high": fifty_two_week_high,
                "fifty_two_week_low": fifty_two_week_low,
                "target_mean_price": target_mean_price,

                # ETF
                "fund_family": fund_family,
                "category": category,
                "holdings_count": holdings_count,

                # 코인
                "coin_id": None,
                "change_24h": None,

                "homepage": homepage,
                "image_url": None,
                "description": description,
                "last_updated": None,
                "missing_fields": missing_fields,
                "raw": make_json_safe(
                    raw_data
                ),
            }

        except Exception as error:
            last_error = str(error)
            continue

    error_suffix = (
        f" 상세 오류: {last_error}"
        if last_error
        else ""
    )

    return empty_result(
        message=(
            "종목정보를 불러오지 못했습니다. "
            "종목코드 또는 티커를 확인해 주세요."
            f"{error_suffix}"
        ),
        asset_type=asset_type,
        symbol=symbol,
    )


# ==================================================
# 코인
# ==================================================

@st.cache_data(
    ttl=3600,
    show_spinner=False,
)
def search_coingecko_coin_id(
    symbol: str,
) -> dict[str, Any]:
    """코인 심볼을 CoinGecko ID로 변환합니다."""

    normalized_symbol = (
        symbol.strip().upper()
    )

    mapped_coin_id = COIN_ID_MAP.get(
        normalized_symbol
    )

    if mapped_coin_id:

        return {
            "success": True,
            "coin_id": mapped_coin_id,
            "name": None,
        }

    try:
        response = requests.get(
            f"{COINGECKO_API_URL}/search",
            params={
                "query": normalized_symbol,
            },
            timeout=15,
        )

        response.raise_for_status()

        data = response.json()

        coins = data.get(
            "coins",
            [],
        )

        if not isinstance(coins, list):

            coins = []

        exact_matches = [
            coin
            for coin in coins
            if str(
                coin.get("symbol", "")
            ).upper()
            == normalized_symbol
        ]

        selected = (
            exact_matches[0]
            if exact_matches
            else (
                coins[0]
                if coins
                else None
            )
        )

        if selected is None:

            return {
                "success": False,
                "coin_id": None,
                "name": None,
            }

        return {
            "success": True,
            "coin_id": safe_text(
                selected.get("id")
            ),
            "name": safe_text(
                selected.get("name")
            ),
        }

    except (
        requests.RequestException,
        ValueError,
        TypeError,
    ):

        return {
            "success": False,
            "coin_id": None,
            "name": None,
        }


@st.cache_data(
    ttl=300,
    show_spinner=False,
)
def get_crypto_metadata(
    symbol: str,
    currency: str = "KRW",
) -> dict[str, Any]:
    """CoinGecko에서 코인 메타데이터와 시장정보를 조회합니다."""

    normalized_symbol = (
        symbol.strip().upper()
    )

    if not normalized_symbol:

        return empty_result(
            message="코인 티커를 입력해 주세요.",
            asset_type="코인",
            symbol=symbol,
        )

    currency = currency.upper()

    coin_search = search_coingecko_coin_id(
        normalized_symbol
    )

    coin_id = coin_search.get(
        "coin_id"
    )

    if not coin_search.get(
        "success"
    ) or not coin_id:

        return empty_result(
            message=(
                "CoinGecko에서 해당 코인을 찾지 못했습니다. "
                "티커를 확인해 주세요."
            ),
            asset_type="코인",
            symbol=symbol,
        )

    try:
        response = requests.get(
            f"{COINGECKO_API_URL}/coins/{coin_id}",
            params={
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "false",
            },
            timeout=20,
        )

        response.raise_for_status()

        data = response.json()

        market_data = data.get(
            "market_data",
            {},
        )

        current_prices = market_data.get(
            "current_price",
            {},
        )

        market_caps = market_data.get(
            "market_cap",
            {},
        )

        changes_24h = market_data.get(
            "price_change_percentage_24h_in_currency",
            {},
        )

        target_currency = currency.lower()

        price = safe_float(
            current_prices.get(
                target_currency
            )
        )

        market_cap = safe_float(
            market_caps.get(
                target_currency
            )
        )

        change_24h = safe_float(
            changes_24h.get(
                target_currency
            )
        )

        name = safe_text(
            data.get("name"),
            coin_search.get("name"),
        )

        resolved_symbol = safe_text(
            data.get("symbol"),
            normalized_symbol,
        )

        if resolved_symbol:
            resolved_symbol = (
                resolved_symbol.upper()
            )

        image_data = data.get(
            "image",
            {},
        )

        image_url = safe_text(
            first_available(
                image_data,
                [
                    "large",
                    "small",
                    "thumb",
                ],
            )
        )

        links = data.get(
            "links",
            {},
        )

        homepages = links.get(
            "homepage",
            [],
        )

        homepage = None

        if isinstance(
            homepages,
            list,
        ):

            homepage = next(
                (
                    safe_text(item)
                    for item in homepages
                    if safe_text(item)
                ),
                None,
            )

        description_data = data.get(
            "description",
            {},
        )

        description = safe_text(
            description_data.get("en")
        )

        categories = data.get(
            "categories",
            [],
        )

        category = None

        if isinstance(categories, list):

            valid_categories = [
                safe_text(item)
                for item in categories
                if safe_text(item)
            ]

            if valid_categories:
                category = ", ".join(
                    valid_categories[:3]
                )

        last_updated = safe_text(
            data.get("last_updated")
        )

        missing_fields: list[str] = []

        checks = {
            "코인명": name,
            "현재가": price,
            "시가총액": market_cap,
            "24시간 변동률": change_24h,
            "홈페이지": homepage,
        }

        for label, value in checks.items():

            if value is None:
                missing_fields.append(
                    label
                )

        return {
            "success": True,
            "message": "",
            "asset_type": "코인",
            "symbol": normalized_symbol,
            "resolved_symbol": resolved_symbol,
            "name": name or normalized_symbol,
            "price": price,
            "currency": currency,
            "exchange": "암호화폐 시장",
            "quote_type": "CRYPTOCURRENCY",
            "sector": None,
            "industry": None,
            "market_cap": market_cap,
            "dividend_yield": None,
            "fund_family": None,
            "category": category,
            "holdings_count": None,
            "coin_id": coin_id,
            "change_24h": change_24h,
            "homepage": homepage,
            "image_url": image_url,
            "description": description,
            "last_updated": last_updated,
            "missing_fields": missing_fields,
            "raw": make_json_safe(
                data
            ),
        }

    except requests.HTTPError as error:

        status_code = (
            error.response.status_code
            if error.response is not None
            else None
        )

        if status_code == 429:
            message = (
                "CoinGecko 무료 API 요청 한도를 초과했습니다. "
                "잠시 후 다시 시도해 주세요."
            )
        else:
            message = (
                "CoinGecko 코인정보 조회에 실패했습니다. "
                f"HTTP 상태: {status_code}"
            )

        return empty_result(
            message=message,
            asset_type="코인",
            symbol=symbol,
        )

    except (
        requests.RequestException,
        ValueError,
        TypeError,
        KeyError,
    ) as error:

        return empty_result(
            message=(
                "코인정보를 불러오지 못했습니다. "
                f"오류: {error}"
            ),
            asset_type="코인",
            symbol=symbol,
        )


# ==================================================
# 통합 진입 함수
# ==================================================

def get_asset_metadata(
    asset_type: str,
    symbol: str,
    currency: str = "KRW",
) -> dict[str, Any]:
    """선택한 자산 종류에 맞는 메타데이터 조회 함수를 실행합니다."""

    if asset_type not in SUPPORTED_ASSET_TYPES:

        return empty_result(
            message=(
                "현재 자동조회가 지원되지 않는 "
                "자산 종류입니다."
            ),
            asset_type=asset_type,
            symbol=symbol,
        )

    if asset_type == "코인":

        return get_crypto_metadata(
            symbol=symbol,
            currency=currency,
        )

    return get_stock_or_etf_metadata(
        asset_type=asset_type,
        symbol=symbol,
    )
from __future__ import annotations

from typing import Any

import requests
import streamlit as st
import yfinance as yf

from services.asset_resolver import is_resolvable_asset_type, resolve_asset

COINGECKO_API_URL = "https://api.coingecko.com/api/v3"


COIN_ID_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "XRP": "ripple",
    "SOL": "solana",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "DOT": "polkadot",
    "LINK": "chainlink",
    "TRX": "tron",
    "LTC": "litecoin",
    "BCH": "bitcoin-cash",
    "ATOM": "cosmos",
    "ETC": "ethereum-classic",
    "SHIB": "shiba-inu",
    "APT": "aptos",
    "SUI": "sui",
    "ARB": "arbitrum",
    "OP": "optimism",
    "NEAR": "near",
    "STX": "blockstack",
}


def normalize_stock_ticker(
    ticker: str,
    asset_type: str,
) -> str:
    """입력한 종목코드를 Yahoo Finance 형식으로 변환합니다."""

    normalized_ticker = ticker.strip().upper()

    if asset_type in [
        "국내주식",
        "국내ETF",
    ]:
        if normalized_ticker.endswith(
            (".KS", ".KQ")
        ):
            return normalized_ticker

        if (
            normalized_ticker.isdigit()
            and len(normalized_ticker) == 6
        ):
            return f"{normalized_ticker}.KS"

    return normalized_ticker


def extract_latest_price(
    ticker_object: yf.Ticker,
) -> float | None:
    """yfinance에서 조회 가능한 가장 최근 가격을 반환합니다."""

    try:
        fast_info = ticker_object.fast_info

        last_price = fast_info.get(
            "last_price"
        )

        if last_price is not None:
            price = float(last_price)

            if price > 0:
                return price

    except (AttributeError, KeyError, OSError, RuntimeError, TypeError, ValueError):
        fast_info = None

    try:
        history = ticker_object.history(
            period="5d",
            interval="1d",
            auto_adjust=False,
        )

        if (
            not history.empty
            and "Close" in history.columns
        ):
            close_prices = (
                history["Close"]
                .dropna()
            )

            if not close_prices.empty:
                price = float(
                    close_prices.iloc[-1]
                )

                if price > 0:
                    return price

    except (AttributeError, KeyError, OSError, RuntimeError, TypeError, ValueError):
        return None

    return None


@st.cache_data(ttl=300)
def get_stock_price(
    ticker: str,
    asset_type: str,
) -> dict[str, Any]:
    """국내·미국 주식과 ETF의 최근 가격을 조회합니다."""

    if not ticker.strip():
        return {
            "success": False,
            "price": None,
            "ticker": "",
            "currency": None,
            "message": "종목코드 또는 티커를 입력해 주세요.",
        }

    normalized_ticker = normalize_stock_ticker(
        ticker=ticker,
        asset_type=asset_type,
    )

    candidate_tickers = [
        normalized_ticker,
    ]

    if (
        asset_type
        in ["국내주식", "국내ETF"]
        and normalized_ticker.endswith(".KS")
    ):
        candidate_tickers.append(
            normalized_ticker.replace(
                ".KS",
                ".KQ",
            )
        )

    for candidate in candidate_tickers:
        try:
            ticker_object = yf.Ticker(
                candidate
            )

            price = extract_latest_price(
                ticker_object
            )

            if price is None:
                continue

            currency = (
                "KRW"
                if asset_type
                in ["국내주식", "국내ETF"]
                else "USD"
            )

            return {
                "success": True,
                "price": price,
                "ticker": candidate,
                "currency": currency,
                "message": "",
            }

        except (AttributeError, KeyError, OSError, RuntimeError, TypeError, ValueError):
            continue

    return {
        "success": False,
        "price": None,
        "ticker": normalized_ticker,
        "currency": None,
        "message": (
            "현재가를 불러오지 못했습니다. "
            "종목코드 또는 티커를 확인해 주세요."
        ),
    }


@st.cache_data(ttl=180)
def get_crypto_price(
    symbol: str,
    currency: str = "KRW",
) -> dict[str, Any]:
    """CoinGecko에서 코인의 현재 가격을 조회합니다."""

    normalized_symbol = (
        symbol.strip().upper()
    )

    if not normalized_symbol:
        return {
            "success": False,
            "price": None,
            "symbol": "",
            "currency": currency,
            "message": "코인 티커를 입력해 주세요.",
        }

    coin_id = COIN_ID_MAP.get(
        normalized_symbol
    )

    if coin_id is None:
        return {
            "success": False,
            "price": None,
            "symbol": normalized_symbol,
            "currency": currency,
            "message": (
                "자동 조회 목록에 없는 코인입니다. "
                "현재가는 직접 입력해야 합니다."
            ),
        }

    target_currency = currency.lower()

    try:
        response = requests.get(
            f"{COINGECKO_API_URL}/simple/price",
            params={
                "ids": coin_id,
                "vs_currencies": target_currency,
                "include_last_updated_at": "true",
            },
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        coin_data = data.get(
            coin_id,
            {},
        )

        price = coin_data.get(
            target_currency
        )

        if price is None:
            raise ValueError(
                "가격 항목이 없습니다."
            )

        price = float(price)

        if price <= 0:
            raise ValueError(
                "조회 가격이 올바르지 않습니다."
            )

        return {
            "success": True,
            "price": price,
            "symbol": normalized_symbol,
            "currency": currency,
            "last_updated_at": coin_data.get(
                "last_updated_at"
            ),
            "message": "",
        }

    except (
        requests.RequestException,
        ValueError,
        TypeError,
    ) as error:
        return {
            "success": False,
            "price": None,
            "symbol": normalized_symbol,
            "currency": currency,
            "message": (
                "코인 가격 조회에 실패했습니다. "
                f"오류: {error}"
            ),
        }


def get_market_price(
    asset_type: str,
    symbol: str,
    currency: str,
) -> dict[str, Any]:
    """자산 종류에 맞는 가격 조회 함수를 실행합니다."""

    if not is_resolvable_asset_type(asset_type):
        return {
            "success": False,
            "price": None,
            "symbol": None,
            "status": "Skip",
            "message": "시세 조회가 필요하지 않은 자산 종류입니다.",
        }
    requested_currency = str(currency or "").upper()
    resolution = resolve_asset(symbol, asset_type=asset_type)
    if resolution.success and resolution.asset is not None:
        symbol = resolution.asset.ticker
        asset_type = resolution.asset.asset_type or asset_type
        # CoinGecko can quote crypto directly in the portfolio currency.  Keep
        # that requested quote currency so a KRW cost basis is never compared
        # with a USD market price. Securities use their listing currency.
        currency = (
            requested_currency or resolution.asset.currency
            if asset_type == "코인"
            else resolution.asset.currency or requested_currency
        )
    elif resolution.status == "ambiguous":
        return {
            "success": False,
            "price": None,
            "message": "여러 자산 후보가 있어 티커를 확정할 수 없습니다.",
            "candidates": [candidate.ticker for candidate in resolution.candidates],
        }

    if asset_type == "코인":
        return get_crypto_price(
            symbol=symbol,
            currency=currency,
        )

    if asset_type in [
        "국내주식",
        "미국주식",
        "국내ETF",
        "미국ETF",
    ]:
        return get_stock_price(
            ticker=symbol,
            asset_type=asset_type,
        )

    return {
        "success": False,
        "price": None,
        "message": (
            "이 자산 종류는 아직 자동 가격 조회를 "
            "지원하지 않습니다."
        ),
    }

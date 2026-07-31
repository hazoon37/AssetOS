from __future__ import annotations

from datetime import datetime
from typing import Any

import requests
import streamlit as st


API_URL = "https://api.frankfurter.dev/v2/rates"

SUPPORTED_CURRENCIES = [
    "KRW",
    "USD",
    "JPY",
    "HKD",
    "EUR",
    "GBP",
]


@st.cache_data(ttl=3600)
def get_exchange_rates_to_krw() -> dict[str, Any]:
    """
    각 외화 1단위가 원화 몇 원인지 한 번에 조회합니다.

    반환 예시:
    {
        "rates": {
            "KRW": 1.0,
            "USD": 1385.25,
            "JPY": 9.31,
            "GBP": 1810.20,
        },
        "date": "2026-07-24",
        "success": True,
        "message": "",
    }
    """

    rates: dict[str, float] = {
        "KRW": 1.0,
    }

    foreign_currencies = [
        currency
        for currency in SUPPORTED_CURRENCIES
        if currency != "KRW"
    ]

    try:
        response = requests.get(
            API_URL,
            params={
                "base": "KRW",
                "quotes": ",".join(foreign_currencies),
            },
            timeout=15,
        )

        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            raise ValueError(
                "환율 API 응답 형식이 예상과 다릅니다."
            )

        rate_date = ""

        for item in data:

            base_currency = item.get("base")
            quote_currency = item.get("quote")
            rate = item.get("rate")

            if (
                base_currency != "KRW"
                or quote_currency not in foreign_currencies
                or rate is None
            ):
                continue

            krw_to_foreign_rate = float(rate)

            if krw_to_foreign_rate <= 0:
                continue

            # API 응답:
            # 1 KRW = 외화 금액
            #
            # 우리가 필요한 값:
            # 1 외화 = 몇 KRW
            rates[quote_currency] = (
                1.0 / krw_to_foreign_rate
            )

            item_date = item.get("date")

            if item_date:
                rate_date = max(
                    rate_date,
                    str(item_date),
                )

        missing_currencies = [
            currency
            for currency in foreign_currencies
            if currency not in rates
        ]

        if missing_currencies:

            return {
                "rates": rates,
                "date": (
                    rate_date
                    or datetime.now().strftime("%Y-%m-%d")
                ),
                "success": False,
                "message": (
                    "환율을 불러오지 못한 통화: "
                    + ", ".join(missing_currencies)
                ),
            }

        return {
            "rates": rates,
            "date": (
                rate_date
                or datetime.now().strftime("%Y-%m-%d")
            ),
            "success": True,
            "message": "",
        }

    except (
        requests.RequestException,
        ValueError,
        TypeError,
        ZeroDivisionError,
    ) as error:

        return {
            "rates": rates,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "success": False,
            "message": (
                "환율 정보를 불러오지 못했습니다. "
                f"오류 내용: {error}"
            ),
        }


def convert_to_krw(
    amount: float,
    currency: str,
    rates: dict[str, float],
) -> float | None:
    """지정 통화 금액을 원화로 환산합니다."""

    if currency == "KRW":
        return float(amount)

    exchange_rate = rates.get(currency)

    if exchange_rate is None:
        return None

    return float(amount) * float(exchange_rate)
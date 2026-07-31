from __future__ import annotations

from typing import Any


CURRENCY_SYMBOLS = {
    "KRW": "₩",
    "USD": "$",
    "JPY": "¥",
    "EUR": "€",
    "GBP": "£",
    "HKD": "HK$",
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


def normalize_currency(
    currency: str | None,
) -> str:
    """통화 코드를 대문자로 정리합니다."""

    return str(
        currency or ""
    ).strip().upper()


def format_currency(
    value: float | int | None,
    currency: str | None = "KRW",
) -> str:
    """통화별 금액을 표시합니다."""

    number = safe_float(value)

    if number is None:
        return "정보 없음"

    normalized_currency = normalize_currency(
        currency
    )

    symbol = CURRENCY_SYMBOLS.get(
        normalized_currency,
        normalized_currency,
    )

    if normalized_currency in {
        "KRW",
        "JPY",
    }:
        return f"{symbol} {number:,.0f}"

    return f"{symbol} {number:,.2f}"


def format_krw(
    value: float | int | None,
) -> str:
    """원화 금액을 표시합니다."""

    return format_currency(
        value=value,
        currency="KRW",
    )


def format_large_currency(
    value: float | int | None,
    currency: str | None = None,
) -> str:
    """큰 금액을 조·억·백만 단위로 표시합니다."""

    number = safe_float(value)

    if number is None:
        return "정보 없음"

    absolute_value = abs(number)

    if absolute_value >= 1_000_000_000_000:
        number_text = (
            f"{number / 1_000_000_000_000:,.2f}조"
        )

    elif absolute_value >= 100_000_000:
        number_text = (
            f"{number / 100_000_000:,.2f}억"
        )

    elif absolute_value >= 1_000_000:
        number_text = (
            f"{number / 1_000_000:,.2f}백만"
        )

    else:
        number_text = f"{number:,.0f}"

    normalized_currency = normalize_currency(
        currency
    )

    if not normalized_currency:
        return number_text

    symbol = CURRENCY_SYMBOLS.get(
        normalized_currency,
        normalized_currency,
    )

    return f"{symbol} {number_text}"


def format_multiple(
    value: float | int | None,
) -> str:
    """PER·PBR 등 배수 지표를 표시합니다."""

    number = safe_float(value)

    if number is None:
        return "정보 없음"

    return f"{number:,.2f}배"


def format_decimal_percentage(
    value: float | int | None,
) -> str:
    """0.15 형태의 값을 15.00%로 표시합니다."""

    number = safe_float(value)

    if number is None:
        return "정보 없음"

    return f"{number * 100:,.2f}%"


def format_percentage_value(
    value: float | int | None,
) -> str:
    """이미 퍼센트 단위인 값을 표시합니다."""

    number = safe_float(value)

    if number is None:
        return "정보 없음"

    return f"{number:,.2f}%"


def format_number(
    value: float | int | None,
    suffix: str = "",
    decimal_places: int = 0,
) -> str:
    """일반 숫자와 단위를 표시합니다."""

    number = safe_float(value)

    if number is None:
        return "정보 없음"

    return (
        f"{number:,.{decimal_places}f}"
        f"{suffix}"
    )
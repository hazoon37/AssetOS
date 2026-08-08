from __future__ import annotations

import math

CURRENCY_SYMBOLS = {
    "KRW": "₩",
    "USD": "$",
    "JPY": "¥",
    "EUR": "€",
    "GBP": "£",
    "HKD": "HK$",
}


def format_asset_type(value: object) -> str:
    """Translate internal asset type names for Korean UI surfaces."""
    label = str(value or "")
    return "계좌" if label == "Account" else label


def safe_float(
    value: object,
) -> float | None:
    """Convert Python, pandas, and NumPy scalar values to a finite float."""

    if value is None:
        return None

    try:
        number = float(str(value))

    except (TypeError, ValueError):
        return None

    return number if math.isfinite(number) else None


def normalize_currency(
    currency: object,
) -> str:
    """통화 코드를 대문자로 정리합니다."""

    if currency is None:
        return ""
    return str(currency).strip().upper()


def format_currency(
    value: object,
    currency: object = "KRW",
) -> str:
    """통화별 금액을 표시합니다."""

    number = safe_float(value)

    if number is None:
        return "-"

    normalized_currency = normalize_currency(
        currency
    )

    symbol = CURRENCY_SYMBOLS.get(
        normalized_currency,
        normalized_currency,
    )

    separator = "" if normalized_currency in CURRENCY_SYMBOLS else " "
    if normalized_currency in {"KRW", "JPY"}:
        return f"{symbol}{separator}{number:,.0f}"

    return f"{symbol}{separator}{number:,.2f}"


def format_krw(
    value: object,
) -> str:
    """원화 금액을 표시합니다."""

    return format_currency(
        value=value,
        currency="KRW",
    )


def format_large_currency(
    value: object,
    currency: object = None,
) -> str:
    """큰 금액을 조·억·백만 단위로 표시합니다."""

    number = safe_float(value)

    if number is None:
        return "정보 없음"

    normalized_currency = normalize_currency(currency)
    if normalized_currency == "KRW":
        return format_currency(number, normalized_currency)

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

    if not normalized_currency:
        return number_text

    symbol = CURRENCY_SYMBOLS.get(
        normalized_currency,
        normalized_currency,
    )

    return f"{symbol} {number_text}"


def format_multiple(
    value: object,
) -> str:
    """PER·PBR 등 배수 지표를 표시합니다."""

    number = safe_float(value)

    if number is None:
        return "정보 없음"

    return f"{number:,.2f}배"


def format_decimal_percentage(
    value: object,
) -> str:
    """0.15 형태의 값을 15.00%로 표시합니다."""

    number = safe_float(value)

    if number is None:
        return "정보 없음"

    return format_percent(number, decimal_input=True)


def format_percentage_value(
    value: object,
) -> str:
    """이미 퍼센트 단위인 값을 표시합니다."""

    number = safe_float(value)

    if number is None:
        return "정보 없음"

    return format_percent(number)


def format_percent(
    value: object,
    *,
    decimal_input: bool = False,
    signed: bool = False,
) -> str:
    """Format a percentage consistently with one decimal place."""
    number = safe_float(value)
    if number is None:
        return "-"
    if decimal_input:
        number *= 100
    sign = "+" if signed and number > 0 else ""
    return f"{sign}{number:,.1f}%"


def format_number(
    value: object,
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

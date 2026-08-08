import numpy as np
import pandas as pd

from ui.common.formatters import (
    format_asset_type,
    format_currency,
    format_number,
    format_percent,
)


def test_krw_has_symbol_separator_and_no_decimals() -> None:
    assert format_currency(2_610_585.7086, "KRW") == "₩2,610,586"


def test_percent_uses_one_decimal_place() -> None:
    assert format_percent(104.6432) == "104.6%"
    assert format_percent(0.1046432, decimal_input=True) == "10.5%"


def test_number_uses_shared_thousands_separator() -> None:
    assert format_number(2610585.7086) == "2,610,586"


def test_internal_account_type_is_localized_for_ui() -> None:
    assert format_asset_type("Account") == "계좌"


def test_currency_accepts_supported_numeric_and_missing_types() -> None:
    assert format_currency(1_000) == "₩1,000"
    assert format_currency(np.float64(1_000.4)) == "₩1,000"
    assert format_currency(None) == "-"
    assert format_currency(pd.NA) == "-"
    assert format_currency(np.nan) == "-"


def test_percent_accepts_supported_numeric_and_missing_types() -> None:
    assert format_percent(10) == "10.0%"
    assert format_percent(np.float64(10.04)) == "10.0%"
    assert format_percent(None) == "-"
    assert format_percent(pd.NA) == "-"
    assert format_percent(np.nan) == "-"

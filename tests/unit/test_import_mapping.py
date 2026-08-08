from __future__ import annotations

import pandas as pd

from services.import_mapping import map_import_columns


def test_maps_common_korean_columns() -> None:
    source = pd.DataFrame([{
        "종목명": "Apple",
        "보유수량": 2,
        "평균매입가": 180,
        "통화코드": "USD",
    }])
    result = map_import_columns(source)
    assert result.dataframe.loc[0, "자산명"] == "Apple"
    assert result.dataframe.loc[0, "수량"] == 2
    assert result.dataframe.loc[0, "평균단가"] == 180
    assert result.dataframe.loc[0, "통화"] == "USD"


def test_derives_average_price_from_holding_amount() -> None:
    source = pd.DataFrame([{"종목명": "Apple", "보유수량": 4, "보유금액": "800"}])
    result = map_import_columns(source)
    assert result.dataframe.loc[0, "평균단가"] == 200
    assert result.mappings["보유금액"] == "평균단가 (보유금액 ÷ 수량)"


def test_does_not_overwrite_explicit_average_price() -> None:
    source = pd.DataFrame([{
        "종목명": "Apple",
        "보유수량": 4,
        "평균매입가": 150,
        "보유금액": 800,
    }])
    result = map_import_columns(source)
    assert result.dataframe.loc[0, "평균단가"] == 150


def test_standard_column_wins_over_alias_column() -> None:
    source = pd.DataFrame([{"종목명": "Alias", "자산명": "Canonical", "수량": 1}])
    result = map_import_columns(source)
    assert result.dataframe.loc[0, "자산명"] == "Canonical"

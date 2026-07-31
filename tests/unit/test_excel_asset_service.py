from __future__ import annotations

from io import BytesIO

import pandas as pd

from services.excel_asset_service import validate_asset_excel


def _excel_bytes(dataframe: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name="Assets", index=False)
    return output.getvalue()


def test_validate_asset_excel_success() -> None:
    dataframe = pd.DataFrame([
        {
            "자산종류": "미국주식",
            "자산명": "Apple",
            "티커": "AAPL",
            "수량": 2,
            "평균단가": 180,
            "현재가": 210,
            "통화": "USD",
        }
    ])
    result = validate_asset_excel(_excel_bytes(dataframe))
    assert result.success is True
    assert len(result.rows) == 1
    assert result.rows[0]["symbol"] == "AAPL"


def test_validate_asset_excel_missing_required_column() -> None:
    dataframe = pd.DataFrame([{"자산명": "Apple"}])
    result = validate_asset_excel(_excel_bytes(dataframe))
    assert result.success is False
    assert result.errors

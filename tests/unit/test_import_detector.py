from __future__ import annotations

from collections.abc import Sequence
from io import BytesIO
from typing import Any, cast

import pandas as pd

from services.import_detector import ImportFileType, detect_import_file


def _workbook(dataframe: pd.DataFrame, sheet_name: str) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(cast(Any, output), engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name=sheet_name, index=False)
    return output.getvalue()


def test_detects_assetos_template() -> None:
    file = _workbook(pd.DataFrame([{"자산명": "Apple", "수량": 1}]), "Assets")
    result = detect_import_file(file)
    assert result.file_type is ImportFileType.ASSETOS_TEMPLATE
    assert result.sheet_name == "Assets"


def test_detects_generic_excel_and_uses_first_sheet() -> None:
    file = _workbook(pd.DataFrame([{"종목명": "Apple", "보유수량": 1}]), "보유자산")
    result = detect_import_file(file)
    assert result.file_type is ImportFileType.GENERIC_EXCEL
    assert result.sheet_name == "보유자산"


def test_registered_broker_adapter_can_claim_generic_file() -> None:
    class TestBrokerAdapter:
        name = "Test Broker"

        def matches(self, sheet_name: str, columns: Sequence[str]) -> bool:
            return sheet_name == "잔고" and "계좌상품" in columns

    file = _workbook(pd.DataFrame([{"계좌상품": "Apple"}]), "잔고")
    result = detect_import_file(file, adapters=[TestBrokerAdapter()])
    assert result.file_type is ImportFileType.BROKER_ADAPTER
    assert result.adapter_name == "Test Broker"

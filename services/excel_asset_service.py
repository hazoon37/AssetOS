from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO

import pandas as pd

from database.db import DB_PATH, replace_all_assets

SHEET_NAME = "Assets"
REQUIRED_COLUMNS = {
    "자산종류",
    "자산명",
    "수량",
    "평균단가",
    "현재가",
    "통화",
}

COLUMN_MAP = {
    "ID": "id",
    "자산종류": "asset_type",
    "자산명": "asset_name",
    "티커": "symbol",
    "수량": "quantity",
    "평균단가": "average_price",
    "현재가": "current_price",
    "통화": "currency",
    "메모": "memo",
    "자산군": "asset_class",
    "국가": "country",
    "거래소": "exchange",
    "섹터": "sector",
    "산업": "industry",
    "현금성": "is_cash",
    "레버리지": "is_leverage",
    "인버스": "is_inverse",
    "레버리지배수": "leverage_multiple",
    "데이터출처": "data_source",
    "태그": "tags",
}

TRUE_VALUES = {"true", "1", "yes", "y", "예", "네", "o"}
FALSE_VALUES = {"false", "0", "no", "n", "아니오", "아니요", "x", ""}


@dataclass(frozen=True)
class ExcelValidationResult:
    success: bool
    rows: list[dict[str, Any]]
    preview: pd.DataFrame
    errors: list[str]
    warnings: list[str]


def _clean_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _to_float(value: Any, *, field: str, row_number: int) -> float:
    if value is None or pd.isna(value) or str(value).strip() == "":
        return 0.0
    try:
        return float(str(value).replace(",", "").replace("₩", "").strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{row_number}행의 '{field}' 값이 숫자가 아닙니다: {value}") from exc


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        return False
    normalized = str(value).strip().lower()
    if normalized in TRUE_VALUES:
        return True
    if normalized in FALSE_VALUES:
        return False
    return False


def read_asset_excel(file: BinaryIO | bytes) -> pd.DataFrame:
    source = BytesIO(file) if isinstance(file, bytes) else file
    return pd.read_excel(source, sheet_name=SHEET_NAME, engine="openpyxl")


def validate_asset_excel(file: BinaryIO | bytes) -> ExcelValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        dataframe = read_asset_excel(file)
    except ValueError as exc:
        return ExcelValidationResult(
            success=False,
            rows=[],
            preview=pd.DataFrame(),
            errors=[f"'{SHEET_NAME}' 시트를 찾지 못했습니다: {exc}"],
            warnings=[],
        )
    except Exception as exc:
        return ExcelValidationResult(
            success=False,
            rows=[],
            preview=pd.DataFrame(),
            errors=[f"엑셀 파일을 읽지 못했습니다: {exc}"],
            warnings=[],
        )

    dataframe.columns = [str(column).strip() for column in dataframe.columns]
    missing = sorted(REQUIRED_COLUMNS - set(dataframe.columns))
    if missing:
        return ExcelValidationResult(
            success=False,
            rows=[],
            preview=dataframe.head(20),
            errors=["필수 열이 없습니다: " + ", ".join(missing)],
            warnings=[],
        )

    # Completely empty rows are ignored.
    dataframe = dataframe.dropna(how="all").copy()
    rows: list[dict[str, Any]] = []

    for index, excel_row in dataframe.iterrows():
        row_number = int(index) + 2
        asset_name = _clean_text(excel_row.get("자산명"))
        asset_type = _clean_text(excel_row.get("자산종류"))

        # Template spare rows are ignored.
        if not asset_name and not asset_type:
            continue

        if not asset_name:
            errors.append(f"{row_number}행: 자산명이 비어 있습니다.")
            continue
        if not asset_type:
            errors.append(f"{row_number}행: 자산종류가 비어 있습니다.")
            continue

        try:
            quantity = _to_float(excel_row.get("수량"), field="수량", row_number=row_number)
            average_price = _to_float(excel_row.get("평균단가"), field="평균단가", row_number=row_number)
            current_price = _to_float(excel_row.get("현재가"), field="현재가", row_number=row_number)
            leverage_multiple = _to_float(
                excel_row.get("레버리지배수", 1),
                field="레버리지배수",
                row_number=row_number,
            ) or 1.0
        except ValueError as exc:
            errors.append(str(exc))
            continue

        if quantity < 0 or average_price < 0 or current_price < 0:
            errors.append(f"{row_number}행: 수량과 가격은 음수가 될 수 없습니다.")
            continue
        if quantity == 0:
            warnings.append(f"{row_number}행 '{asset_name}': 수량이 0입니다.")

        currency = _clean_text(excel_row.get("통화")).upper()
        if not currency:
            errors.append(f"{row_number}행 '{asset_name}': 통화가 비어 있습니다.")
            continue

        row = {
            "asset_type": asset_type,
            "asset_name": asset_name,
            "symbol": _clean_text(excel_row.get("티커")).upper(),
            "quantity": quantity,
            "average_price": average_price,
            "current_price": current_price,
            "currency": currency,
            "memo": _clean_text(excel_row.get("메모")),
            "asset_class": _clean_text(excel_row.get("자산군")),
            "country": _clean_text(excel_row.get("국가")).upper(),
            "exchange": _clean_text(excel_row.get("거래소")),
            "sector": _clean_text(excel_row.get("섹터")),
            "industry": _clean_text(excel_row.get("산업")),
            "is_cash": _to_bool(excel_row.get("현금성")),
            "is_leverage": _to_bool(excel_row.get("레버리지")),
            "is_inverse": _to_bool(excel_row.get("인버스")),
            "leverage_multiple": leverage_multiple,
            "data_source": _clean_text(excel_row.get("데이터출처")) or "Excel Import",
            "tags": _clean_text(excel_row.get("태그")),
        }
        rows.append(row)

    if not rows and not errors:
        errors.append("가져올 자산 행이 없습니다.")

    preview_columns = [
        column
        for column in ["자산종류", "자산명", "티커", "수량", "평균단가", "현재가", "통화"]
        if column in dataframe.columns
    ]
    preview = dataframe[preview_columns].head(30).copy()

    return ExcelValidationResult(
        success=not errors,
        rows=rows,
        preview=preview,
        errors=errors,
        warnings=warnings,
    )


def backup_database() -> Path | None:
    if not DB_PATH.exists():
        return None
    backup_dir = DB_PATH.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"assets_before_excel_{timestamp}.db"
    backup_path.write_bytes(DB_PATH.read_bytes())
    return backup_path


def import_asset_excel(file: BinaryIO | bytes) -> dict[str, Any]:
    validation = validate_asset_excel(file)
    if not validation.success:
        return {
            "success": False,
            "imported_count": 0,
            "backup_path": None,
            "errors": validation.errors,
            "warnings": validation.warnings,
        }

    backup_path = backup_database()
    replace_all_assets(validation.rows)

    return {
        "success": True,
        "imported_count": len(validation.rows),
        "backup_path": str(backup_path) if backup_path else None,
        "errors": [],
        "warnings": validation.warnings,
    }

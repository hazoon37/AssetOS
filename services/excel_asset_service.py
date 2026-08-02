from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, BinaryIO

import pandas as pd
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from components.asset_management.constants import ASSET_TYPES, SUPPORTED_CURRENCIES
from database.db import DB_PATH, get_assets, replace_all_assets

SHEET_NAME = "Assets"
REQUIRED_COLUMNS = {
    "자산종류",
    "자산명",
    "수량",
    "평균단가",
    "현재가",
    "통화",
}
TEMPLATE_COLUMNS = ["자산종류", "자산명", "수량", "평균단가", "현재가", "통화"]

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
    "등록일": "created_at",
    "수정일": "updated_at",
}

EXCEL_COLUMNS = list(COLUMN_MAP)
GUIDE_SHEET_NAME = "📖 작성가이드"

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


def _dataframe_to_excel(dataframe: pd.DataFrame) -> bytes:
    """Serialize one Assets sheet without touching the filesystem."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, sheet_name=SHEET_NAME, index=False)
    return output.getvalue()


def build_asset_template_excel() -> bytes:
    """Return a styled, importer-compatible workbook for entering assets."""
    example = {
        "자산종류": "미국주식",
        "자산명": "Apple",
        "수량": 2,
        "평균단가": 180,
        "현재가": 210,
        "통화": "USD",
    }
    template = pd.DataFrame([example], columns=TEMPLATE_COLUMNS)
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        template.to_excel(writer, sheet_name=SHEET_NAME, index=False)
        workbook = writer.book
        assets_sheet = writer.sheets[SHEET_NAME]

        required_fill = PatternFill("solid", fgColor="D9EAF7")
        optional_fill = PatternFill("solid", fgColor="EAF0F6")
        example_fill = PatternFill("solid", fgColor="E7E7E7")

        for cell in assets_sheet[1]:
            cell.font = Font(bold=True, color="1F2937")
            cell.fill = required_fill if cell.value in REQUIRED_COLUMNS else optional_fill
            cell.alignment = Alignment(horizontal="center", vertical="center")
            if cell.value in REQUIRED_COLUMNS:
                cell.comment = Comment("* 필수 입력 항목", "AssetOS")

        for cell in assets_sheet[2]:
            cell.fill = example_fill
            cell.font = Font(italic=True, color="666666")
        assets_sheet["A2"].comment = Comment(
            "예시입니다. 삭제 후 사용하세요.",
            "AssetOS",
        )

        assets_sheet.freeze_panes = "A2"
        assets_sheet.auto_filter.ref = assets_sheet.dimensions
        assets_sheet.row_dimensions[1].height = 24

        dropdowns = {
            "자산종류": ASSET_TYPES,
            "통화": SUPPORTED_CURRENCIES,
            "현금성": ["예", "아니오"],
            "레버리지": ["예", "아니오"],
            "인버스": ["예", "아니오"],
        }
        for column_name, choices in dropdowns.items():
            if column_name not in TEMPLATE_COLUMNS:
                continue
            column_index = TEMPLATE_COLUMNS.index(column_name) + 1
            formula = '"' + ",".join(choices) + '"'
            validation = DataValidation(type="list", formula1=formula, allow_blank=True)
            validation.error = "목록에서 값을 선택해 주세요."
            validation.errorTitle = "올바르지 않은 값"
            validation.prompt = "목록에서 값을 선택할 수 있습니다."
            validation.promptTitle = column_name
            validation.showErrorMessage = True
            validation.showInputMessage = True
            assets_sheet.add_data_validation(validation)
            validation.add(f"{get_column_letter(column_index)}2:{get_column_letter(column_index)}1000")

        for column_index, column_name in enumerate(TEMPLATE_COLUMNS, start=1):
            values = [column_name, example.get(column_name, "")]
            width = min(max(len(str(value)) for value in values) + 4, 32)
            assets_sheet.column_dimensions[get_column_letter(column_index)].width = max(width, 11)

        guide = workbook.create_sheet(GUIDE_SHEET_NAME)
        guide_rows = [
            ("AssetOS Excel 작성가이드", ""),
            ("사용 방법", "Assets 시트의 회색 예시 행을 삭제한 뒤 자산을 한 행씩 입력하세요."),
            ("필수 항목 (*)", "자산종류 *, 자산명 *, 수량 *, 평균단가 *, 현재가 *, 통화 *"),
            ("업로드 과정", "Asset Manager에서 파일 선택 → 미리보기 및 오류 확인 → 동의 → Apply Changes"),
            ("주의", "열 이름과 Assets 시트 이름을 변경하지 마세요. 적용 전 현재 DB가 자동 백업됩니다."),
            ("간단한 예", "미국주식 | Apple | 2 | 180 | 210 | USD"),
        ]
        for row in guide_rows:
            guide.append(row)
        guide["A1"].font = Font(size=16, bold=True, color="FFFFFF")
        guide["B1"].font = Font(size=16, bold=True, color="FFFFFF")
        for cell in guide[1]:
            cell.fill = PatternFill("solid", fgColor="2563EB")
        for row_index in range(2, guide.max_row + 1):
            guide.cell(row_index, 1).font = Font(bold=True, color="1F2937")
            guide.cell(row_index, 1).fill = required_fill
            guide.cell(row_index, 2).alignment = Alignment(wrap_text=True, vertical="top")
        guide.column_dimensions["A"].width = 20
        guide.column_dimensions["B"].width = 86
        guide.freeze_panes = "A2"

    return output.getvalue()


def export_assets_excel(assets: pd.DataFrame | None = None) -> bytes:
    """Export the current assets table using the standard import column names."""
    source = get_assets() if assets is None else assets
    exported = pd.DataFrame()
    for excel_column, database_column in COLUMN_MAP.items():
        exported[excel_column] = (
            source[database_column]
            if database_column in source.columns
            else pd.Series(index=source.index, dtype="object")
        )
    return _dataframe_to_excel(exported)


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

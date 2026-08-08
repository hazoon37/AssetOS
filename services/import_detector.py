from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from io import BytesIO
from typing import BinaryIO, Protocol

import pandas as pd

from services.import_mapping import normalize_column_name


class ImportFileType(str, Enum):
    ASSETOS_TEMPLATE = "AssetOS template"
    GENERIC_EXCEL = "Generic Excel"
    BROKER_ADAPTER = "Broker adapter"


@dataclass(frozen=True)
class ImportDetection:
    file_type: ImportFileType
    sheet_name: str
    columns: tuple[str, ...]
    adapter_name: str | None = None


class BrokerImportAdapter(Protocol):
    """Extension contract for future broker-specific import adapters."""

    name: str

    def matches(self, sheet_name: str, columns: Sequence[str]) -> bool: ...


def _source(file: BinaryIO | bytes) -> BinaryIO:
    if isinstance(file, bytes):
        return BytesIO(file)
    file.seek(0)
    return file


def detect_import_file(
    file: BinaryIO | bytes,
    adapters: Sequence[BrokerImportAdapter] = (),
) -> ImportDetection:
    """Detect a standard workbook, registered broker format, or generic Excel."""
    source = _source(file)
    workbook = pd.ExcelFile(source, engine="openpyxl")
    sheet_name = "Assets" if "Assets" in workbook.sheet_names else workbook.sheet_names[0]
    columns_frame = pd.read_excel(workbook, sheet_name=sheet_name, nrows=0)
    columns = tuple(str(column).strip() for column in columns_frame.columns)
    normalized = {normalize_column_name(column) for column in columns}

    if sheet_name == "Assets" and {normalize_column_name("자산명"), normalize_column_name("수량")} <= normalized:
        return ImportDetection(ImportFileType.ASSETOS_TEMPLATE, sheet_name, columns)

    for adapter in adapters:
        if adapter.matches(sheet_name, columns):
            return ImportDetection(
                ImportFileType.BROKER_ADAPTER,
                sheet_name,
                columns,
                adapter_name=adapter.name,
            )

    return ImportDetection(ImportFileType.GENERIC_EXCEL, sheet_name, columns)

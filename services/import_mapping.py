from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

import pandas as pd

STANDARD_COLUMNS = {
    "자산종류",
    "자산명",
    "티커",
    "수량",
    "평균단가",
    "현재가",
    "통화",
    "메모",
    "자산군",
    "국가",
    "거래소",
    "섹터",
    "산업",
    "현금성",
    "레버리지",
    "인버스",
    "레버리지배수",
    "데이터출처",
    "태그",
    "ID",
    "등록일",
    "수정일",
}

COLUMN_ALIASES = {
    "자산명": ("종목명", "상품명", "증권명", "name", "assetname", "securityname"),
    "수량": ("보유수량", "잔고수량", "보유량", "quantity", "qty", "shares"),
    "평균단가": (
        "평균매입가",
        "평균매수가",
        "매입평균가",
        "매입단가",
        "averageprice",
        "avgprice",
        "costprice",
    ),
    "현재가": ("시장가", "종가", "현재가격", "currentprice", "marketprice", "lastprice"),
    "티커": ("종목코드", "종목번호", "심볼", "ticker", "symbol", "code"),
    "통화": ("화폐", "통화코드", "currency", "ccy"),
    "자산종류": ("종목유형", "상품유형", "자산유형", "assettype", "type"),
    "메모": ("비고", "备注", "memo", "note"),
}

HOLDING_AMOUNT_ALIASES = (
    "보유금액",
    "매입금액",
    "총매입금액",
    "취득금액",
    "purchaseamount",
    "costamount",
    "totalcost",
)


@dataclass(frozen=True)
class ImportMappingResult:
    dataframe: pd.DataFrame
    mappings: dict[str, str]
    warnings: list[str]


def normalize_column_name(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().casefold()
    return re.sub(r"[\s_\-./()\[\]]+", "", text)


def _alias_index() -> dict[str, str]:
    aliases: dict[str, str] = {}
    for standard in STANDARD_COLUMNS:
        aliases[normalize_column_name(standard)] = standard
    for standard, candidates in COLUMN_ALIASES.items():
        for candidate in candidates:
            aliases[normalize_column_name(candidate)] = standard
    return aliases


def map_import_columns(dataframe: pd.DataFrame) -> ImportMappingResult:
    """Map a generic statement to AssetOS columns without mutating its source."""
    result = dataframe.copy()
    alias_index = _alias_index()
    mappings: dict[str, str] = {}
    occupied: set[str] = {
        str(source).strip()
        for source in result.columns
        if str(source).strip() in STANDARD_COLUMNS
    }

    for source in result.columns:
        target = alias_index.get(normalize_column_name(source))
        if str(source).strip() in STANDARD_COLUMNS:
            mappings[str(source)] = str(source).strip()
        elif target and target not in occupied:
            mappings[str(source)] = target
            occupied.add(target)

    result = result.rename(columns=mappings)
    warnings: list[str] = []

    if "평균단가" not in result.columns:
        holding_amount_column = next(
            (
                column
                for column in result.columns
                if normalize_column_name(column)
                in {normalize_column_name(alias) for alias in HOLDING_AMOUNT_ALIASES}
            ),
            None,
        )
        if holding_amount_column is not None and "수량" in result.columns:
            amount_source = pd.Series(result[holding_amount_column], index=result.index)
            quantity_source = pd.Series(result["수량"], index=result.index)
            amounts = pd.Series(pd.to_numeric(
                amount_source.astype(str).str.replace(",", "", regex=False),
                errors="coerce",
            ), index=result.index)
            quantities = pd.Series(pd.to_numeric(
                quantity_source.astype(str).str.replace(",", "", regex=False),
                errors="coerce",
            ), index=result.index)
            result["평균단가"] = amounts.div(quantities.where(quantities.ne(0)))
            mappings[str(holding_amount_column)] = "평균단가 (보유금액 ÷ 수량)"
            if (quantities.eq(0) & amounts.notna()).any():
                warnings.append("수량이 0인 행은 보유금액으로 평균단가를 계산할 수 없습니다.")

    return ImportMappingResult(dataframe=result, mappings=mappings, warnings=warnings)

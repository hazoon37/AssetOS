from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import math
from typing import Any, Callable

import streamlit as st
import pandas as pd

from services.asset_resolver import (
    RESOLVABLE_ASSET_TYPES,
    AssetResolution,
    ResolvedAsset,
    is_resolvable_asset_type,
    resolve_asset,
)
from services.market_price_service import get_market_price


SEARCHABLE_ASSET_TYPES = RESOLVABLE_ASSET_TYPES
SKIPPED_ASSET_TYPES = {
    "예금", "예적금", "적금", "현금", "CMA", "MMF", "저축예금",
    "입출금", "입출금계좌", "SAVINGS ACCOUNT", "CHECKING ACCOUNT",
    "DEPOSIT", "CASH",
}
ACCOUNT_KEYWORDS = (
    "외화예수금", "외화계좌", "종합매매", "예수금", "증거금",
    "입출금", "계좌", "위탁", "CMA", "MMF", "RP",
)

STATUS_LABELS = {
    "resolved": "🟢 Auto",
    "skipped": "⚪ Skip",
    "needs_selection": "🟡 Select",
    "failed": "🔴 Fail",
}


@dataclass(frozen=True)
class SmartImportResolution:
    row: dict[str, Any]
    status: str
    current_value: float
    profit_available: bool
    warnings: list[str]
    candidates: tuple[ResolvedAsset, ...] = ()
    matched_asset: ResolvedAsset | None = None
    detected_keyword: str = ""
    classification: str = ""
    reason: str = ""


@dataclass(frozen=True)
class PreviewEditResult:
    """Validated rows reconstructed from the editable import preview."""

    rows: list[dict[str, Any]]
    errors: list[str]


def _market_price(asset_type: str, ticker: str, currency: str) -> float | None:
    result = get_market_price(asset_type=asset_type, symbol=ticker, currency=currency)
    if not result.get("success"):
        return None
    try:
        price = float(result.get("price"))
        return price if math.isfinite(price) and price > 0 else None
    except (TypeError, ValueError):
        return None


def _append_tag(tags: str, tag: str) -> str:
    values = [value.strip() for value in str(tags or "").split(",") if value.strip()]
    if tag not in values:
        values.append(tag)
    return ",".join(values)


def _smart_import_source(current: object, *, unresolved: bool) -> str:
    source = str(current or "").strip()
    if source and source != "Excel Import":
        return source
    return "Smart Import (Unresolved)" if unresolved else "Smart Import"


def should_skip_resolution(asset_type: object) -> bool:
    """Return whether a non-market asset does not require ticker search."""
    return not is_resolvable_asset_type(asset_type)


def detect_account_keyword(asset_name: object) -> str | None:
    """Return the highest-priority account keyword contained in an asset name."""
    normalized = str(asset_name or "").strip().upper()
    return next(
        (keyword for keyword in ACCOUNT_KEYWORDS if keyword.upper() in normalized),
        None,
    )


def display_asset_name(value: object) -> str:
    """Create a compact display label without changing the stored asset name."""
    parts = [part.strip() for part in str(value or "").split("*") if part.strip()]
    if len(parts) > 1 and parts[0].upper() in SKIPPED_ASSET_TYPES:
        return " ".join(parts[1:])
    return str(value or "")


def enrich_import_row(
    source: dict[str, Any],
    *,
    resolver: Callable[[str], AssetResolution] = resolve_asset,
    price_lookup: Callable[[str, str, str], float | None] = _market_price,
) -> SmartImportResolution:
    """Resolve and price one validated row without mutating the source."""
    row = dict(source)
    average_missing = bool(row.pop("_average_price_missing", False))
    account_keyword = detect_account_keyword(row.get("asset_name"))
    if account_keyword:
        row["asset_type"] = "Account"
        price = float(row.get("current_price") or 0.0)
        if average_missing:
            row["average_price"] = 0.0
            row["tags"] = _append_tag(str(row.get("tags") or ""), "COST_BASIS_UNKNOWN")
        return SmartImportResolution(
            row=row,
            status="skipped",
            current_value=float(row.get("quantity") or 0.0) * price,
            profit_available=not average_missing,
            warnings=[],
            detected_keyword=account_keyword,
            classification="Account",
            reason=f"'{account_keyword}' 계좌 키워드가 감지되어 ticker 검색이 필요하지 않습니다.",
        )
    if should_skip_resolution(row.get("asset_type")):
        price = float(row.get("current_price") or 0.0)
        if average_missing:
            row["average_price"] = 0.0
            row["tags"] = _append_tag(str(row.get("tags") or ""), "COST_BASIS_UNKNOWN")
        return SmartImportResolution(
            row=row,
            status="skipped",
            current_value=float(row.get("quantity") or 0.0) * price,
            profit_available=not average_missing,
            warnings=[],
        )
    provided_ticker = str(row.get("symbol") or "").strip()
    asset_name = str(row.get("asset_name") or "").strip()
    query = provided_ticker or asset_name
    resolution = resolver(query)
    if (
        provided_ticker
        and resolution.status == "unknown"
        and asset_name
        and asset_name.casefold() != provided_ticker.casefold()
    ):
        resolution = resolver(asset_name)
    recommended_candidates = tuple(resolution.candidates)
    resolved_asset = resolution.asset if resolution.status in {"exact", "fuzzy"} else None
    warnings: list[str] = []

    if resolved_asset is not None:
        values = {
            "symbol": resolved_asset.ticker,
            "exchange": resolved_asset.exchange,
            "currency": resolved_asset.currency,
            "country": resolved_asset.country,
            "asset_type": resolved_asset.asset_type,
            "sector": resolved_asset.sector,
            "industry": resolved_asset.industry,
            "is_leverage": int(resolved_asset.is_leveraged),
        }
        previous_ticker = provided_ticker.upper()
        for key, value in values.items():
            authoritative = key == "symbol" or (
                key == "currency" and resolved_asset.asset_type != "코인"
            )
            if authoritative or not row.get(key):
                row[key] = value
        ticker_changed = previous_ticker != resolved_asset.ticker.upper()
        master_tags = [tag for tag in resolved_asset.theme.split("|") if tag]
        if resolved_asset.is_dividend:
            master_tags.append("Dividend")
        if resolved_asset.is_leveraged:
            master_tags.append("Leveraged")
        for tag in master_tags:
            row["tags"] = _append_tag(str(row.get("tags") or ""), tag)

    else:
        ticker_changed = False

    try:
        price = float(row.get("current_price") or 0)
    except (TypeError, ValueError):
        price = 0.0
    price_is_invalid = not math.isfinite(price) or price <= 0
    # A source price belongs to its source ticker. Once resolution changes the
    # ticker it must be discarded and fetched again, even when it is positive.
    if (price_is_invalid or ticker_changed) and row.get("symbol") and row.get("asset_type") and row.get("currency"):
        fetched_price = price_lookup(
            str(row["asset_type"]),
            str(row["symbol"]),
            str(row["currency"]),
        )
        try:
            price = float(fetched_price or 0.0)
        except (TypeError, ValueError):
            price = 0.0
        if not math.isfinite(price) or price <= 0:
            price = 0.0
        row["current_price"] = price

    unresolved_reasons: list[str] = []
    if recommended_candidates:
        unresolved_reasons.append(
            "추천 후보를 확인해 주세요."
            if resolution.status == "fuzzy"
            else "여러 자산 후보가 있어 자동으로 확정하지 못했습니다."
        )
    elif provided_ticker and resolved_asset is None and str(row.get("asset_type") or "") != "기타":
        unresolved_reasons.append(f"입력한 티커 '{provided_ticker}'를 확인하지 못했습니다.")
    elif resolved_asset is None and not row.get("symbol"):
        unresolved_reasons.append("자산명을 티커로 확인하지 못했습니다.")
    if price <= 0:
        warnings.append("Price unavailable")

    if unresolved_reasons:
        status = "unresolved"
        warnings.extend(unresolved_reasons)
        row["asset_type"] = str(row.get("asset_type") or "기타")
        row["currency"] = str(row.get("currency") or "KRW")
        row["country"] = str(row.get("country") or "OTHER")
        row["sector"] = str(row.get("sector") or "Unclassified")
        row["tags"] = _append_tag(str(row.get("tags") or ""), "UNRESOLVED")
        row["data_source"] = _smart_import_source(row.get("data_source"), unresolved=True)
    else:
        status = "resolved"
        row["data_source"] = _smart_import_source(row.get("data_source"), unresolved=False)

    # The current schema stores numeric values. Zero remains an explicit unknown
    # sentinel; it is never replaced with current price as a fabricated cost basis.
    if average_missing:
        row["average_price"] = 0.0
        row["tags"] = _append_tag(str(row.get("tags") or ""), "COST_BASIS_UNKNOWN")
        warnings.append("평균단가가 없어 평가손익과 수익률을 계산하지 않습니다.")

    quantity = float(row.get("quantity") or 0)
    return SmartImportResolution(
        row=row,
        status=status,
        current_value=quantity * price,
        profit_available=not average_missing,
        warnings=warnings,
        candidates=recommended_candidates,
        matched_asset=resolved_asset,
    )


def apply_resolution_candidate(
    source: dict[str, Any],
    candidate: ResolvedAsset,
    *,
    price_lookup: Callable[[str, str, str], float | None] = _market_price,
) -> SmartImportResolution:
    """Apply an explicitly selected ambiguous candidate and run normal enrichment."""
    return enrich_import_row(
        source,
        resolver=lambda _query: AssetResolution(
            query=str(source.get("asset_name") or ""), status="exact", asset=candidate
        ),
        price_lookup=price_lookup,
    )


def apply_manual_ticker(source: dict[str, Any], ticker: str) -> SmartImportResolution:
    """Validate a ticker or company name through the shared resolver."""
    row = dict(source)
    row["symbol"] = str(ticker or "").strip().upper()
    return enrich_manual_import_row_cached(row)


@st.cache_data(ttl=900, show_spinner=False)
def enrich_manual_import_row_cached(source: dict[str, Any]) -> SmartImportResolution:
    """Resolve manual input with exact-ticker validation before name lookup."""
    return enrich_import_row(
        source,
        resolver=lambda query: resolve_asset(query, prefer_exact_ticker=True),
    )


@st.cache_data(ttl=900, show_spinner=False)
def enrich_import_row_cached(source: dict[str, Any]) -> SmartImportResolution:
    """Cache one deterministic import enrichment across Streamlit reruns."""
    return enrich_import_row(source)


@st.cache_data(ttl=900, show_spinner=False)
def enrich_import_rows_cached(
    rows: list[dict[str, Any]],
) -> list[SmartImportResolution]:
    """Resolve a validated batch once for persistent and session-only imports."""
    return enrich_import_rows(rows)


def enrich_import_rows(rows: list[dict[str, Any]]) -> list[SmartImportResolution]:
    """Resolve a batch without retaining uploaded rows outside caller-owned state."""
    return [enrich_import_row(row) for row in rows]


def build_import_preview(resolved_rows: list[dict[str, Any]]) -> pd.DataFrame:
    """Build the shared editable preview schema for every Smart Import mode."""
    return pd.DataFrame([
        {
            "Row Number": row.get("_excel_row_number", index + 2),
            "Asset": row.get("asset_name", ""),
            "Ticker": row.get("symbol", ""),
            "Asset Type": row.get("asset_type", ""),
            "Quantity": row.get("quantity", 0.0),
            "Average Price": row.get("average_price", 0.0),
            "Current Price": row.get("current_price", 0.0),
            "Currency": row.get("currency", ""),
            "Exchange": row.get("exchange", ""),
            "Country": row.get("country", ""),
            "Status": (
                "✅ Resolved"
                if row.get("resolution_status") == "resolved"
                else "⏭ Skipped"
                if row.get("resolution_status") == "skipped"
                else "⚠ Needs Selection"
                if row.get("resolution_status") == "needs_selection"
                else "❌ Failed"
            ),
        }
        for index, row in enumerate(resolved_rows)
    ])


def resolution_state(result: SmartImportResolution) -> str:
    if result.status == "skipped":
        return "skipped"
    if result.candidates:
        return "needs_selection"
    return "resolved" if result.status == "resolved" else "failed"


def build_resolution_table(
    source_rows: list[dict[str, Any]],
    results: list[SmartImportResolution],
) -> pd.DataFrame:
    """Build the compact one-screen resolution table shared by import modes."""
    records: list[dict[str, Any]] = []
    for index, (source, result) in enumerate(zip(source_rows, results), start=2):
        state = resolution_state(result)
        records.append({
            "Row": int(source.get("_excel_row_number") or index),
            "Type": result.row.get("asset_type") or source.get("asset_type") or "",
            "Asset": display_asset_name(source.get("asset_name")),
            "Ticker": (
                candidate_label(result.matched_asset, (result.matched_asset,))
                if result.matched_asset is not None
                else result.row.get("symbol") or ""
            ),
            "Status": STATUS_LABELS[state],
        })
    return pd.DataFrame(records)


def resolution_summary(results: list[SmartImportResolution]) -> dict[str, int]:
    states = [resolution_state(result) for result in results]
    return {
        "Total": len(states),
        "Auto": states.count("resolved"),
        "Select": states.count("needs_selection"),
        "Skip": states.count("skipped"),
        "Fail": states.count("failed"),
    }


def candidate_label(candidate: ResolvedAsset, candidates: tuple[ResolvedAsset, ...]) -> str:
    """Format one single-line candidate, adding exchange only for duplicate names."""
    duplicate_name = sum(
        item.display_name.casefold() == candidate.display_name.casefold()
        for item in candidates
    ) > 1
    ticker = candidate.ticker
    if ticker.endswith((".KS", ".KQ")):
        ticker = ticker.rsplit(".", 1)[0]
    label = f"{ticker} | {candidate.display_name}"
    return f"{label} | {candidate.exchange}" if duplicate_name and candidate.exchange else label


def finalize_import_rows(results: list[SmartImportResolution]) -> list[dict[str, Any]]:
    """Remove transient UX fields before passing rows to existing import logic."""
    rows: list[dict[str, Any]] = []
    for result in results:
        row = dict(result.row)
        row.pop("_excel_row_number", None)
        row.pop("resolution_status", None)
        row.pop("current_value", None)
        rows.append(row)
    return rows


def build_import_error_report(
    source_dataframe: pd.DataFrame,
    source_rows: list[dict[str, Any]],
    results: list[SmartImportResolution],
) -> bytes:
    """Append resolution details while retaining every original Excel column."""
    report = source_dataframe.copy()
    table = build_resolution_table(source_rows, results).set_index("Row")
    report["Status"] = [
        table.at[int(index) + 2, "Status"]
        if int(index) + 2 in table.index else ""
        for index in report.index
    ]
    report["Suggested Action"] = ""
    for source, result in zip(source_rows, results):
        row_number = int(source.get("_excel_row_number") or 0)
        source_index = row_number - 2
        if source_index in report.index:
            state = resolution_state(result)
            if result.candidates:
                report.at[source_index, "Suggested Action"] = "Select: " + "; ".join(
                    candidate_label(candidate, result.candidates)
                    for candidate in result.candidates
                )
            elif state == "failed":
                report.at[source_index, "Suggested Action"] = "Enter a valid ticker"
            elif state == "skipped":
                report.at[source_index, "Suggested Action"] = "Search not required"
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        report.to_excel(writer, sheet_name="Assets", index=False)
    return output.getvalue()


def apply_preview_edits(
    resolved_rows: list[dict[str, Any]],
    preview_rows: list[dict[str, Any]],
) -> PreviewEditResult:
    """Merge user preview edits without discarding resolver metadata."""
    if len(resolved_rows) != len(preview_rows):
        return PreviewEditResult([], ["미리보기 행 수가 원본과 일치하지 않습니다. 파일을 다시 선택해 주세요."])

    fields = {
        "Asset": "asset_name",
        "Ticker": "symbol",
        "Asset Type": "asset_type",
        "Quantity": "quantity",
        "Average Price": "average_price",
        "Current Price": "current_price",
        "Currency": "currency",
        "Exchange": "exchange",
        "Country": "country",
    }
    numeric_fields = {"Quantity", "Average Price", "Current Price"}
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, (source, edited) in enumerate(zip(resolved_rows, preview_rows), start=2):
        row = dict(source)
        row_number = int(source.get("_excel_row_number") or index)
        for preview_name, storage_name in fields.items():
            value = edited.get(preview_name)
            if preview_name in numeric_fields:
                try:
                    number = float(value)
                    if not math.isfinite(number) or number < 0:
                        raise ValueError
                    row[storage_name] = number
                except (TypeError, ValueError):
                    errors.append(f"{row_number}행의 '{preview_name}'은 0 이상의 숫자여야 합니다.")
            else:
                row[storage_name] = (
                    ""
                    if value is None or (isinstance(value, float) and math.isnan(value))
                    else str(value).strip()
                )

        if not row.get("asset_name"):
            errors.append(f"{row_number}행의 'Asset'을 입력해 주세요.")
        if not row.get("currency"):
            errors.append(f"{row_number}행의 'Currency'를 입력해 주세요.")
        row.pop("resolution_status", None)
        row.pop("current_value", None)
        row.pop("_excel_row_number", None)
        rows.append(row)
    return PreviewEditResult(rows, errors)

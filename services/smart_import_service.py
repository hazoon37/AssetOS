from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from services.asset_resolver import AssetResolution, resolve_asset
from services.market_price_service import get_market_price


@dataclass(frozen=True)
class SmartImportResolution:
    row: dict[str, Any]
    status: str
    current_value: float
    profit_available: bool
    warnings: list[str]


def _market_price(asset_type: str, ticker: str, currency: str) -> float | None:
    result = get_market_price(asset_type=asset_type, symbol=ticker, currency=currency)
    if not result.get("success"):
        return None
    try:
        price = float(result.get("price"))
        return price if price > 0 else None
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


def enrich_import_row(
    source: dict[str, Any],
    *,
    resolver: Callable[[str], AssetResolution] = resolve_asset,
    price_lookup: Callable[[str, str, str], float | None] = _market_price,
) -> SmartImportResolution:
    """Resolve and price one validated row without mutating the source."""
    row = dict(source)
    average_missing = bool(row.pop("_average_price_missing", False))
    query = str(row.get("symbol") or row.get("asset_name") or "").strip()
    resolution = resolver(query)
    resolved_asset = resolution.asset
    warnings: list[str] = []

    if resolved_asset is not None:
        values = {
            "symbol": resolved_asset.ticker,
            "exchange": resolved_asset.exchange,
            "currency": resolved_asset.currency,
            "country": resolved_asset.country,
            "asset_type": resolved_asset.asset_type,
            "sector": resolved_asset.sector,
        }
        for key, value in values.items():
            if not row.get(key):
                row[key] = value

    price = float(row.get("current_price") or 0)
    if price <= 0 and row.get("symbol") and row.get("asset_type") and row.get("currency"):
        price = price_lookup(
            str(row["asset_type"]),
            str(row["symbol"]),
            str(row["currency"]),
        ) or 0.0
        row["current_price"] = price

    unresolved_reasons: list[str] = []
    if resolution.status == "ambiguous":
        unresolved_reasons.append("여러 자산 후보가 있어 자동으로 확정하지 못했습니다.")
    elif resolved_asset is None and not row.get("symbol"):
        unresolved_reasons.append("자산명을 티커로 확인하지 못했습니다.")
    if price <= 0:
        unresolved_reasons.append("현재가를 조회하지 못했습니다.")

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
    )

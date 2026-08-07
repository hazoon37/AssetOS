from __future__ import annotations

from services.asset_resolver import AssetResolution, ResolvedAsset
from services.smart_import_service import enrich_import_row


def _base_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "asset_name": "Apple",
        "quantity": 2.0,
        "asset_type": "",
        "symbol": "",
        "average_price": 0.0,
        "current_price": 0.0,
        "currency": "",
        "country": "",
        "exchange": "",
        "sector": "",
        "tags": "",
        "data_source": "",
        "_average_price_missing": True,
    }
    row.update(overrides)
    return row


def test_resolves_name_fetches_price_and_calculates_value() -> None:
    result = enrich_import_row(
        _base_row(),
        price_lookup=lambda asset_type, ticker, currency: 210.0,
    )
    assert result.status == "resolved"
    assert result.row["symbol"] == "AAPL"
    assert result.row["current_price"] == 210.0
    assert result.current_value == 420.0
    assert result.profit_available is False
    assert result.row["average_price"] == 0.0
    assert "COST_BASIS_UNKNOWN" in result.row["tags"]
    assert result.row["data_source"] == "Smart Import"


def test_price_failure_keeps_asset_and_marks_unresolved() -> None:
    result = enrich_import_row(
        _base_row(),
        price_lookup=lambda asset_type, ticker, currency: None,
    )
    assert result.status == "unresolved"
    assert result.row["asset_name"] == "Apple"
    assert result.row["symbol"] == "AAPL"
    assert result.row["current_price"] == 0.0
    assert "UNRESOLVED" in result.row["tags"]
    assert result.row["data_source"] == "Smart Import (Unresolved)"
    assert result.current_value == 0.0


def test_manual_values_override_resolver_and_price_lookup() -> None:
    calls: list[tuple[str, str, str]] = []
    result = enrich_import_row(
        _base_row(
            symbol="MANUAL",
            asset_type="기타",
            currency="KRW",
            country="KR",
            exchange="직접입력",
            current_price=123.0,
            average_price=100.0,
            _average_price_missing=False,
        ),
        resolver=lambda query: AssetResolution(query=query, status="unknown"),
        price_lookup=lambda *args: calls.append(args) or 999.0,
    )
    assert result.row["symbol"] == "MANUAL"
    assert result.row["current_price"] == 123.0
    assert result.current_value == 246.0
    assert result.profit_available is True
    assert calls == []


def test_unknown_name_is_retained_with_persistence_fallbacks() -> None:
    result = enrich_import_row(
        _base_row(asset_name="Unknown Asset"),
        resolver=lambda query: AssetResolution(query=query, status="unknown"),
        price_lookup=lambda asset_type, ticker, currency: None,
    )
    assert result.status == "unresolved"
    assert result.row["asset_name"] == "Unknown Asset"
    assert result.row["asset_type"] == "기타"
    assert result.row["currency"] == "KRW"
    assert result.row["country"] == "OTHER"


def test_ambiguous_asset_is_not_auto_selected() -> None:
    candidates = [
        ResolvedAsset("AAA", "NASDAQ", "USD", "US", "미국주식", "Technology", "Alpha A"),
        ResolvedAsset("AAB", "NYSE", "USD", "US", "미국주식", "Technology", "Alpha B"),
    ]
    result = enrich_import_row(
        _base_row(asset_name="Alpha"),
        resolver=lambda query: AssetResolution(
            query=query,
            status="ambiguous",
            candidates=candidates,
        ),
        price_lookup=lambda asset_type, ticker, currency: 100.0,
    )
    assert result.status == "unresolved"
    assert result.row["symbol"] == ""
    assert "UNRESOLVED" in result.row["tags"]

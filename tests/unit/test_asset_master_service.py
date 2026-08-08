from __future__ import annotations

from unittest.mock import Mock, patch

import pandas as pd

from repositories.asset_repository import AssetRepository
from services.asset_master_service import (
    enrich_asset_metadata,
    get_asset_master,
    load_asset_master,
    search_asset_master,
)
from services.asset_metadata_service import get_asset_metadata
from services.asset_resolver import AssetResolution, ResolvedAsset, resolve_asset
from services.portfolio_service import get_portfolio_analysis


def test_asset_master_has_required_fields_and_types() -> None:
    records = load_asset_master()
    assert records
    apple = get_asset_master("AAPL")
    assert apple is not None
    assert apple.display_name == "Apple"
    assert apple.currency == "USD"
    assert apple.industry == "Consumer Electronics"
    assert apple.company_name == "Apple"
    assert "apple" in apple.aliases
    assert apple.status == "active"
    assert isinstance(apple.is_dividend, bool)
    assert isinstance(apple.is_leveraged, bool)


def test_asset_master_supports_alias_fuzzy_and_ambiguity() -> None:
    assert search_asset_master("애플").records[0].ticker == "AAPL"
    assert search_asset_master("Bitcon").records[0].ticker == "BTC"
    ambiguous = search_asset_master("Samsung")
    assert ambiguous.status == "ambiguous"
    assert {record.ticker for record in ambiguous.records} == {"005930.KS", "006400.KS"}


def test_resolver_uses_master_before_external_provider() -> None:
    with patch("services.asset_resolver._search_yahoo") as external_lookup:
        result = resolve_asset("Apple")
    assert result.asset is not None
    assert result.asset.ticker == "AAPL"
    assert result.asset.industry == "Consumer Electronics"
    external_lookup.assert_not_called()


def test_resolver_falls_back_to_external_provider() -> None:
    from services.asset_resolver import ResolvedAsset

    external = ResolvedAsset("NEW", "NASDAQ", "USD", "US", "미국주식", "Technology", "New Asset")
    with patch("services.asset_resolver._search_yahoo", return_value=[external]), patch(
        "services.asset_resolver.upsert_asset_master"
    ):
        result = resolve_asset("New Asset")
    assert result.asset == external


def test_enrichment_preserves_existing_values() -> None:
    enriched = enrich_asset_metadata({
        "symbol": "AAPL",
        "sector": "User Sector",
        "industry": "",
        "country": "OTHER",
    })
    assert enriched["sector"] == "User Sector"
    assert enriched["industry"] == "Consumer Electronics"
    assert enriched["country"] == "US"
    assert "Dividend" in enriched["tags"]


def test_portfolio_common_result_uses_master_metadata() -> None:
    repository = Mock(spec=AssetRepository)
    repository.get_assets.return_value = pd.DataFrame([{
        "id": 1,
        "asset_name": "Apple",
        "symbol": "AAPL",
        "asset_type": "미국주식",
        "asset_class": "STOCK",
        "country": "OTHER",
        "currency": "USD",
        "exchange": "",
        "sector": "Unclassified",
        "industry": "",
        "quantity": 1,
        "average_price": 100,
        "current_price": 120,
        "is_cash": 0,
        "is_leverage": 0,
        "is_inverse": 0,
        "leverage_multiple": 1,
        "tags": "",
    }])
    exchange = {"rates": {"KRW": 1.0, "USD": 1_300.0}, "success": True, "date": "2026-08-08"}
    with patch("services.portfolio_service.get_exchange_rates_to_krw", return_value=exchange):
        result = get_portfolio_analysis(repository=repository)
    assert result["assets"][0]["sector"] == "Technology"
    assert result["assets"][0]["industry"] == "Consumer Electronics"
    assert result["assets"][0]["country"] == "US"
    assert result["assets"][0]["provider"] == "AssetOS"
    assert result["assets"][0]["theme"] == "Technology|Consumer"
    assert result["assets"][0]["is_dividend"] is True


def test_analysis_metadata_uses_master_without_overwriting_provider_values() -> None:
    provider_result = {
        "success": True,
        "symbol": "AAPL",
        "sector": "Provider Sector",
        "industry": "",
        "exchange": "",
    }
    with patch("services.asset_metadata_service.get_stock_or_etf_metadata", return_value=provider_result):
        result = get_asset_metadata("미국주식", "AAPL", "USD")
    assert result["sector"] == "Provider Sector"
    assert result["industry"] == "Consumer Electronics"
    assert result["exchange"] == "NASDAQ"


def test_asset_detail_resolves_company_name_before_metadata_provider() -> None:
    apple = ResolvedAsset(
        "AAPL", "NASDAQ", "USD", "US", "미국주식", "Technology", "Apple"
    )
    provider_result = {"success": True, "symbol": "AAPL"}
    with patch(
        "services.asset_metadata_service.resolve_asset",
        return_value=AssetResolution("Apple", "exact", asset=apple),
    ), patch(
        "services.asset_metadata_service.get_stock_or_etf_metadata",
        return_value=provider_result,
    ) as metadata_provider:
        get_asset_metadata("미국주식", "Apple", "KRW")
    metadata_provider.assert_called_once_with(asset_type="미국주식", symbol="AAPL")

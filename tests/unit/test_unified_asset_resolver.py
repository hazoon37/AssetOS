from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from services import asset_master_service
from services.asset_resolver import (
    AssetResolution,
    ResolvedAsset,
    learn_asset_alias,
    resolve_asset,
)
from services.market_price_service import get_market_price
from services.portfolio_ai_service import diagnose_portfolio
from services.portfolio_service import analyze_asset_rows


def test_learned_alias_resolves_on_next_lookup() -> None:
    with TemporaryDirectory() as directory:
        learned_path = Path(directory) / "learned_asset_master.json"
        learned_path.write_text("{}", encoding="utf-8")
        with patch.object(asset_master_service, "LEARNED_MASTER_PATH", learned_path):
            asset_master_service.load_alias_dictionary.cache_clear()
            asset_master_service.load_asset_master.cache_clear()
            asset_master_service._by_ticker.cache_clear()
            asset_master_service.search_asset_master.cache_clear()
            assert learn_asset_alias("내 최애 회사", "AAPL") is True
            assert resolve_asset("내 최애 회사").ticker == "AAPL"
    asset_master_service.load_alias_dictionary.cache_clear()
    asset_master_service.load_asset_master.cache_clear()
    asset_master_service._by_ticker.cache_clear()
    asset_master_service.search_asset_master.cache_clear()


def test_current_price_resolves_name_before_provider_call() -> None:
    with patch("services.market_price_service.get_stock_price") as price:
        price.return_value = {"success": True, "price": 200.0, "ticker": "AAPL"}
        result = get_market_price("미국주식", "Apple", "USD")
    assert result["success"] is True
    price.assert_called_once_with(ticker="AAPL", asset_type="미국주식")


def test_portfolio_uses_shared_resolver_enrichment() -> None:
    row = {
        "asset_name": "Apple", "symbol": "", "asset_type": "미국주식",
        "quantity": 1, "average_price": 100, "current_price": 120,
        "currency": "USD", "account_name": "Test",
    }
    with patch(
        "services.portfolio_service.enrich_asset_with_resolver",
        wraps=lambda asset: {**asset, "symbol": "AAPL", "country": "US"},
    ) as resolver:
        analyze_asset_rows([row], {"KRW": 1.0, "USD": 1300.0})
    resolver.assert_called_once()


def test_ai_advisor_normalizes_assets_through_shared_resolver() -> None:
    provider = Mock()
    provider.generate.return_value = "diagnosis"
    portfolio = {"assets": [{"name": "Apple", "symbol": ""}]}
    with patch(
        "services.portfolio_ai_service.enrich_asset_with_resolver",
        return_value={"name": "Apple", "symbol": "AAPL"},
    ) as resolver:
        assert diagnose_portfolio(portfolio, provider) == "diagnosis"
    resolver.assert_called_once()
    assert provider.generate.call_args.args[0]["assets"][0]["symbol"] == "AAPL"


def test_partial_name_match_precedes_fuzzy_fallback() -> None:
    result = resolve_asset("Apple Incorporated", include_external=False)
    assert result.ticker == "AAPL"


def test_reliable_online_result_is_added_to_learned_master() -> None:
    external = ResolvedAsset(
        "NEWX", "NASDAQ", "USD", "US", "미국주식", "Technology", "New Example"
    )
    with TemporaryDirectory() as directory:
        learned_path = Path(directory) / "learned_asset_master.json"
        learned_path.write_text("{}", encoding="utf-8")
        with patch.object(asset_master_service, "LEARNED_MASTER_PATH", learned_path), patch(
            "services.asset_resolver._search_yahoo", return_value=[external]
        ):
            asset_master_service.load_alias_dictionary.cache_clear()
            asset_master_service.load_asset_master.cache_clear()
            asset_master_service._by_ticker.cache_clear()
            asset_master_service.search_asset_master.cache_clear()
            result = resolve_asset("NEWX")
            assert result.ticker == "NEWX"
            learned = learned_path.read_text(encoding="utf-8")
            assert '"company_name": "New Example"' in learned
            assert '"status": "active"' in learned
    asset_master_service.load_alias_dictionary.cache_clear()
    asset_master_service.load_asset_master.cache_clear()
    asset_master_service._by_ticker.cache_clear()
    asset_master_service.search_asset_master.cache_clear()


def test_online_lookup_filters_unrelated_candidates() -> None:
    unrelated = ResolvedAsset(
        "XYZ", "NASDAQ", "USD", "US", "미국주식", "Technology", "Example Holdings"
    )
    with patch("services.asset_resolver._search_yahoo", return_value=[unrelated]):
        result = resolve_asset("completely unrelated query")
    assert result.status == "unknown"
    assert result.candidates == []


def test_ai_provider_runs_only_after_local_and_online_resolution_fail() -> None:
    provider = Mock()
    provider.resolve.return_value = AssetResolution(query="unknown-new", status="unknown")
    with patch("services.asset_resolver._AI_RESOLVER_PROVIDER", provider), patch(
        "services.asset_resolver._search_yahoo", return_value=[]
    ):
        assert resolve_asset("Apple").ticker == "AAPL"
        provider.resolve.assert_not_called()
        assert resolve_asset("unknown-new").status == "unknown"
        provider.resolve.assert_called_once_with("unknown-new")

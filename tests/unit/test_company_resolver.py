from __future__ import annotations

from unittest.mock import patch

from services.analysis_engine import analyze_korean_stock
from services.asset_resolver import AssetResolution
from services.company_service import resolve_company_query


def test_company_search_uses_shared_asset_resolver() -> None:
    assert resolve_company_query("Alphabet").ticker == "GOOGL"
    assert resolve_company_query("구글").ticker == "GOOGL"
    assert resolve_company_query("엔비디아").ticker == "NVDA"
    assert resolve_company_query("Apple").ticker == "AAPL"


def test_analysis_engine_uses_shared_resolver_before_validation() -> None:
    unknown = AssetResolution(query="not-a-stock", status="unknown")
    with patch("services.analysis_engine.resolve_asset", return_value=unknown) as resolver:
        result = analyze_korean_stock("not-a-stock")
    resolver.assert_called_once_with("not-a-stock")
    assert result["success"] is False

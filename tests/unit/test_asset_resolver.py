from __future__ import annotations

from unittest.mock import patch

from services.asset_resolver import AssetResolution, resolve_asset


def test_resolve_korean_name() -> None:
    result = resolve_asset("삼성전자")
    assert isinstance(result, AssetResolution)
    assert result.success is True
    assert result.asset is not None
    assert result.asset.ticker == "005930.KS"
    assert result.asset.currency == "KRW"
    assert result.ticker == "005930.KS"
    assert result.exchange == "KOSPI"
    assert result.country == "KR"
    assert result.asset_type == "국내주식"
    assert result.sector == "Technology"
    assert result.display_name == "삼성전자"


def test_resolve_english_name() -> None:
    result = resolve_asset("Apple")
    assert result.success is True
    assert result.asset is not None
    assert result.asset.ticker == "AAPL"


def test_resolve_ticker() -> None:
    result = resolve_asset("NVDA")
    assert result.success is True
    assert result.asset is not None
    assert result.asset.display_name == "NVIDIA"


def test_resolve_fuzzy_name() -> None:
    result = resolve_asset("Bitcon")
    assert result.success is True
    assert result.status == "fuzzy"
    assert result.asset is not None
    assert result.asset.ticker == "BTC"


def test_unknown_asset() -> None:
    with patch("services.asset_resolver._search_yahoo", return_value=[]):
        result = resolve_asset("completely unknown asset")
    assert result.success is False
    assert result.status == "unknown"
    assert result.asset is None
    assert result.candidates == []


def test_ambiguous_asset_does_not_auto_select() -> None:
    result = resolve_asset("Samsung")
    assert result.success is False
    assert result.status == "ambiguous"
    assert result.asset is None
    assert {candidate.ticker for candidate in result.candidates} == {
        "005930.KS",
        "006400.KS",
    }


def test_supported_product_examples() -> None:
    expected = {
        "Samsung Electronics": "005930.KS",
        "005930": "005930.KS",
        "애플": "AAPL",
        "AAPL": "AAPL",
        "엔비디아": "NVDA",
        "NVIDIA": "NVDA",
        "비트코인": "BTC",
        "Bitcoin": "BTC",
        "BTC": "BTC",
    }
    for query, ticker in expected.items():
        result = resolve_asset(query)
        assert result.asset is not None
        assert result.asset.ticker == ticker

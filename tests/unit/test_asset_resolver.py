from __future__ import annotations

from unittest.mock import patch

from services.asset_resolver import (
    RESOLVABLE_ASSET_TYPES,
    enrich_asset_with_resolver,
    AssetResolution,
    ResolvedAsset,
    load_alias_dictionary,
    resolve_asset,
)


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
        "NAVER": "035420.KS",
        "네이버": "035420.KS",
        "035420": "035420.KS",
        "삼성전기": "009150.KS",
        "009150": "009150.KS",
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


def test_global_alias_dictionary_is_cached_and_supports_100_stocks() -> None:
    aliases = load_alias_dictionary()
    assert load_alias_dictionary() is aliases
    assert len({ticker for values in aliases.values() for ticker in values}) >= 100
    assert resolve_asset("브로드컴").ticker == "AVGO"
    assert resolve_asset("microsoft").ticker == "MSFT"


def test_stock_search_regression_aliases_resolve_to_shared_tickers() -> None:
    expected = {
        "GOOGL": "GOOGL",
        "GOOG": "GOOG",
        "Alphabet": "GOOGL",
        "Google": "GOOGL",
        "구글": "GOOGL",
        "알파벳": "GOOGL",
        "NVDA": "NVDA",
        "NVIDIA": "NVDA",
        "엔비디아": "NVDA",
        "TSLA": "TSLA",
        "Tesla": "TSLA",
        "테슬라": "TSLA",
        "Apple": "AAPL",
        "애플": "AAPL",
        "AAPL": "AAPL",
    }
    for query, ticker in expected.items():
        assert resolve_asset(query).ticker == ticker


def test_common_krx_assets_resolve_locally_without_selection() -> None:
    expected = {
        "삼성전자": "005930.KS",
        "삼성전기": "009150.KS",
        "NAVER": "035420.KS",
        "셀트리온": "068270.KS",
        "한화오션": "042660.KS",
        "현대글로비스": "086280.KS",
        "카카오뱅크": "323410.KS",
        "HMM": "011200.KS",
        "KODEX 200": "069500.KS",
        "TIGER 미국S&P500": "360750.KS",
        "우진엔텍": "457550.KQ",
        "ACE 미국S&P500": "360200.KS",
        "TIGER 미국나스닥100": "133690.KS",
        "TIGER 미국나스닥100타겟데일리커버드콜": "486290.KS",
        "KODEX 미국배당커버드콜액티브": "441640.KS",
        "TIGER 미국배당다우존스": "458730.KS",
        "QQQ 2배 프로셰어즈 ETF": "QLD",
        "그리티": "204020.KQ",
        "한화시스템": "272210.KS",
    }
    with patch("services.asset_resolver._search_yahoo") as external:
        for query, ticker in expected.items():
            result = resolve_asset(query)
            assert result.status == "exact"
            assert result.ticker == ticker
            assert result.candidates == []
    external.assert_not_called()


def test_online_candidates_below_auto_threshold_are_not_discarded() -> None:
    candidates = [
        ResolvedAsset("NMA", "NASDAQ", "USD", "US", "미국주식", "Technology", "Nimbus One"),
        ResolvedAsset("NMB", "NYSE", "USD", "US", "미국주식", "Technology", "Nimbus Two"),
    ]
    with patch("services.asset_resolver._search_yahoo", return_value=candidates):
        result = resolve_asset("Nimbus")
    assert result.status == "ambiguous"
    assert [candidate.ticker for candidate in result.candidates] == ["NMA", "NMB"]


def test_manual_uppercase_ticker_uses_exact_market_validation_first() -> None:
    dfdv = ResolvedAsset(
        "DFDV", "NMS", "USD", "US", "미국주식", "Financial Services",
        "DeFi Development Corp.", provider="Yahoo Finance",
    )
    with patch("services.asset_resolver.get_asset_master", return_value=None), patch(
        "services.asset_resolver._lookup_yahoo_ticker", return_value=dfdv
    ) as direct, patch(
        "services.asset_resolver._search_yahoo"
    ) as company_search, patch("services.asset_resolver.upsert_asset_master") as persist:
        result = resolve_asset("DFDV", prefer_exact_ticker=True)
    assert result.status == "exact"
    assert result.ticker == "DFDV"
    direct.assert_called_once_with("DFDV")
    company_search.assert_not_called()
    persist.assert_called_once()


def test_invalid_manual_ticker_falls_back_to_company_name_resolution() -> None:
    with patch("services.asset_resolver._lookup_yahoo_ticker", return_value=None) as direct:
        result = resolve_asset("APPLE", prefer_exact_ticker=True)
    assert result.ticker == "AAPL"
    direct.assert_called_once_with("APPLE")


def test_non_market_asset_types_bypass_every_resolver_stage() -> None:
    non_market_types = (
        "현금", "예금", "입출금통장", "계좌", "증권계좌", "ISA", "IRP",
        "연금", "예수금", "외화예수금", "보험", "기타비시장자산", "Account",
    )
    with patch("services.asset_resolver._PROVIDERS") as providers:
        for asset_type in non_market_types:
            result = resolve_asset(
                "카카오페이*종합계좌*주식", asset_type=asset_type
            )
            assert result.status == "Skip"
            assert result.ticker is None
            assert result.candidates == []
    providers.assert_not_called()


def test_market_asset_type_whitelist_is_explicit() -> None:
    assert RESOLVABLE_ASSET_TYPES == {
        "국내주식", "미국주식", "국내ETF", "미국ETF", "코인", "리츠",
    }


def test_non_market_enrichment_preserves_name_without_ticker_inference() -> None:
    source = {
        "asset_name": "카카오페이*종합계좌*주식",
        "asset_type": "Account",
        "symbol": "",
    }
    assert enrich_asset_with_resolver(source) == source

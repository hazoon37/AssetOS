from __future__ import annotations

from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Protocol

import streamlit as st
import yfinance as yf


@dataclass(frozen=True)
class ResolvedAsset:
    ticker: str
    exchange: str
    currency: str
    country: str
    asset_type: str
    sector: str
    display_name: str


@dataclass(frozen=True)
class AssetResolution:
    query: str
    status: str
    asset: ResolvedAsset | None = None
    candidates: list[ResolvedAsset] = field(default_factory=list)

    @property
    def success(self) -> bool:
        return self.status in {"exact", "fuzzy"} and self.asset is not None

    @property
    def ticker(self) -> str | None:
        return self.asset.ticker if self.asset else None

    @property
    def exchange(self) -> str | None:
        return self.asset.exchange if self.asset else None

    @property
    def currency(self) -> str | None:
        return self.asset.currency if self.asset else None

    @property
    def country(self) -> str | None:
        return self.asset.country if self.asset else None

    @property
    def asset_type(self) -> str | None:
        return self.asset.asset_type if self.asset else None

    @property
    def sector(self) -> str | None:
        return self.asset.sector if self.asset else None

    @property
    def display_name(self) -> str | None:
        return self.asset.display_name if self.asset else None


class AssetResolverProvider(Protocol):
    """Provider boundary for future Yahoo Finance, KRX, or CoinGecko adapters."""

    def resolve(self, query: str) -> AssetResolution | None: ...


_ASSETS: dict[str, ResolvedAsset] = {
    "005930": ResolvedAsset(
        ticker="005930.KS", exchange="KOSPI", currency="KRW", country="KR",
        asset_type="국내주식", sector="Technology", display_name="삼성전자",
    ),
    "006400": ResolvedAsset(
        ticker="006400.KS", exchange="KOSPI", currency="KRW", country="KR",
        asset_type="국내주식", sector="Technology", display_name="삼성SDI",
    ),
    "AAPL": ResolvedAsset(
        ticker="AAPL", exchange="NASDAQ", currency="USD", country="US",
        asset_type="미국주식", sector="Technology", display_name="Apple",
    ),
    "NVDA": ResolvedAsset(
        ticker="NVDA", exchange="NASDAQ", currency="USD", country="US",
        asset_type="미국주식", sector="Technology", display_name="NVIDIA",
    ),
    "BTC": ResolvedAsset(
        ticker="BTC", exchange="CoinGecko", currency="USD", country="OTHER",
        asset_type="코인", sector="Cryptocurrency", display_name="Bitcoin",
    ),
}

# Aliases intentionally map to one or more canonical keys. Multiple keys are
# preserved so callers can ask users to choose instead of making a risky guess.
_ALIASES: dict[str, tuple[str, ...]] = {
    "삼성전자": ("005930",),
    "samsung electronics": ("005930",),
    "005930": ("005930",),
    "005930.ks": ("005930",),
    "삼성sdi": ("006400",),
    "samsung sdi": ("006400",),
    "006400": ("006400",),
    "006400.ks": ("006400",),
    "samsung": ("005930", "006400"),
    "애플": ("AAPL",),
    "apple": ("AAPL",),
    "aapl": ("AAPL",),
    "엔비디아": ("NVDA",),
    "nvidia": ("NVDA",),
    "nvda": ("NVDA",),
    "비트코인": ("BTC",),
    "bitcoin": ("BTC",),
    "btc": ("BTC",),
}

_FUZZY_THRESHOLD = 0.72
_AMBIGUOUS_MARGIN = 0.06

_EXCHANGE_COUNTRY = {
    "KSC": "KR", "KOE": "KR", "KOSPI": "KR", "KOSDAQ": "KR",
    "NMS": "US", "NYQ": "US", "NGM": "US", "ASE": "US", "PCX": "US",
    "LSE": "GB", "HKG": "HK", "JPX": "JP", "GER": "DE", "PAR": "FR",
}


def _normalize(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _resolution(query: str, status: str, keys: tuple[str, ...]) -> AssetResolution:
    candidates = list(dict.fromkeys(_ASSETS[key] for key in keys))
    if len(candidates) == 1:
        return AssetResolution(query=query, status=status, asset=candidates[0])
    return AssetResolution(query=query, status="ambiguous", candidates=candidates)


def _resolve_aliases(name: str) -> AssetResolution:
    query = str(name or "").strip()
    normalized = _normalize(query)
    if not normalized:
        return AssetResolution(query=query, status="unknown")

    exact_keys = _ALIASES.get(normalized)
    if exact_keys:
        return _resolution(query, "exact", exact_keys)

    scored = sorted(
        (
            (SequenceMatcher(None, normalized, alias).ratio(), alias, keys)
            for alias, keys in _ALIASES.items()
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    matches = [item for item in scored if item[0] >= _FUZZY_THRESHOLD]
    if not matches:
        return AssetResolution(query=query, status="unknown")

    best_score = matches[0][0]
    close_matches = [item for item in matches if best_score - item[0] <= _AMBIGUOUS_MARGIN]
    keys = tuple(key for _, _, matched_keys in close_matches for key in matched_keys)
    return _resolution(query, "fuzzy", keys)


class _AliasProvider:
    def resolve(self, query: str) -> AssetResolution:
        return _resolve_aliases(query)


def _market_asset_type(quote: dict[str, object]) -> str:
    quote_type = str(quote.get("quoteType") or "").upper()
    if quote_type == "CRYPTOCURRENCY":
        return "코인"
    symbol = str(quote.get("symbol") or "").upper()
    exchange = str(quote.get("exchange") or quote.get("exchDisp") or "").upper()
    domestic = symbol.endswith((".KS", ".KQ")) or exchange in {"KSC", "KOE", "KOSPI", "KOSDAQ"}
    if domestic:
        return "국내ETF" if quote_type == "ETF" else "국내주식"
    return "미국ETF" if quote_type == "ETF" else "미국주식"


@st.cache_data(ttl=3600, show_spinner=False)
def _search_yahoo(query: str) -> list[ResolvedAsset]:
    try:
        quotes = yf.Search(
            query,
            max_results=8,
            news_count=0,
            lists_count=0,
            include_cb=False,
            include_nav_links=False,
            include_research=False,
            timeout=8,
            raise_errors=False,
        ).quotes
    except Exception:
        return []

    candidates: list[ResolvedAsset] = []
    seen: set[tuple[str, str]] = set()
    for quote in quotes:
        quote_type = str(quote.get("quoteType") or "").upper()
        if quote_type not in {"EQUITY", "ETF", "CRYPTOCURRENCY"}:
            continue
        ticker = str(quote.get("symbol") or "").strip().upper()
        if quote_type == "CRYPTOCURRENCY":
            ticker = ticker.split("-")[0]
        exchange = str(quote.get("exchange") or quote.get("exchDisp") or "").strip()
        if not ticker or (ticker, exchange) in seen:
            continue
        seen.add((ticker, exchange))
        asset_type = _market_asset_type(quote)
        currency = str(quote.get("currency") or "").strip().upper()
        if not currency:
            currency = "KRW" if asset_type.startswith("국내") else "USD"
        country = "OTHER" if asset_type == "코인" else _EXCHANGE_COUNTRY.get(
            exchange.upper(),
            "KR" if currency == "KRW" else "US" if currency == "USD" else "OTHER",
        )
        candidates.append(ResolvedAsset(
            ticker=ticker,
            exchange=exchange,
            currency=currency,
            country=country,
            asset_type=asset_type,
            sector=str(quote.get("sector") or "Unclassified"),
            display_name=str(quote.get("longname") or quote.get("shortname") or ticker).strip(),
        ))
    return candidates


class _YahooProvider:
    def resolve(self, query: str) -> AssetResolution | None:
        candidates = _search_yahoo(query)
        if not candidates:
            return None
        normalized = _normalize(query).upper()
        exact = [candidate for candidate in candidates if candidate.ticker.upper() == normalized]
        if len(exact) == 1:
            return AssetResolution(query=query, status="exact", asset=exact[0])
        if len(candidates) == 1:
            return AssetResolution(query=query, status="fuzzy", asset=candidates[0])
        return AssetResolution(query=query, status="ambiguous", candidates=candidates)


# Future remote providers can be appended here without changing resolve_asset()
# or any caller that consumes AssetResolution.
_PROVIDERS: tuple[AssetResolverProvider, ...] = (_AliasProvider(), _YahooProvider())


def resolve_asset(name: str) -> AssetResolution:
    """Resolve an asset name or ticker without silently selecting ambiguity."""
    query = str(name or "").strip()
    for provider in _PROVIDERS:
        result = provider.resolve(query)
        if result is not None and result.status != "unknown":
            return result
    return AssetResolution(query=query, status="unknown")

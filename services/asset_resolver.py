from __future__ import annotations

from dataclasses import dataclass, field, replace
from difflib import SequenceMatcher
import re
from typing import Protocol

import streamlit as st
import yfinance as yf

from services.asset_master_service import (
    AssetMasterRecord,
    get_asset_master,
    load_alias_dictionary,
    save_learned_alias,
    search_asset_master,
    upsert_asset_master,
)


AUTO_CONFIDENCE_THRESHOLD = 0.82
CANDIDATE_CONFIDENCE_THRESHOLD = 0.45
_TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9.-]{0,14}$")
RESOLVABLE_ASSET_TYPES = frozenset({
    "국내주식",
    "미국주식",
    "국내ETF",
    "미국ETF",
    "코인",
    "리츠",
})


@dataclass(frozen=True)
class ResolvedAsset:
    ticker: str
    exchange: str
    currency: str
    country: str
    asset_type: str
    sector: str
    display_name: str
    industry: str = ""
    provider: str = ""
    theme: str = ""
    is_dividend: bool = False
    is_leveraged: bool = False
    confidence: float = 1.0


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


class AIAssetResolverProvider(Protocol):
    """Optional last-resort provider; no AI implementation is enabled by default."""

    def resolve(self, query: str) -> AssetResolution | None: ...


_EXCHANGE_COUNTRY = {
    "KSC": "KR", "KOE": "KR", "KOSPI": "KR", "KOSDAQ": "KR",
    "NMS": "US", "NYQ": "US", "NGM": "US", "ASE": "US", "PCX": "US",
    "LSE": "GB", "HKG": "HK", "JPX": "JP", "GER": "DE", "PAR": "FR",
}


def _normalize(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _resolved_asset(record: AssetMasterRecord) -> ResolvedAsset:
    return ResolvedAsset(
        ticker=record.ticker,
        exchange=record.exchange,
        currency=record.currency,
        country=record.country,
        asset_type=record.asset_type,
        sector=record.sector,
        display_name=record.display_name,
        industry=record.industry,
        provider=record.provider,
        theme=record.theme,
        is_dividend=record.is_dividend,
        is_leveraged=record.is_leveraged,
    )


class _AssetMasterProvider:
    def resolve(self, query: str) -> AssetResolution:
        result = search_asset_master(query)
        candidates = [_resolved_asset(record) for record in result.records]
        if len(candidates) == 1 and result.status in {"exact", "fuzzy"}:
            return AssetResolution(query=query, status=result.status, asset=candidates[0])
        if candidates:
            return AssetResolution(query=query, status="ambiguous", candidates=candidates)
        return AssetResolution(query=query, status="unknown")


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
def _lookup_yahoo_ticker(symbol: str) -> ResolvedAsset | None:
    """Validate one exact ticker directly, without company-name search."""
    normalized = str(symbol or "").strip().upper()
    if not _TICKER_PATTERN.fullmatch(normalized):
        return None
    try:
        info = yf.Ticker(normalized).get_info()
    except Exception:
        return None
    if not isinstance(info, dict):
        return None
    returned_symbol = str(info.get("symbol") or "").strip().upper()
    quote_type = str(info.get("quoteType") or "").upper()
    if returned_symbol != normalized or quote_type not in {"EQUITY", "ETF", "CRYPTOCURRENCY"}:
        return None
    exchange = str(info.get("exchange") or info.get("fullExchangeName") or "").strip()
    asset_type = _market_asset_type({**info, "symbol": normalized, "exchange": exchange})
    currency = str(info.get("currency") or "").strip().upper()
    if not currency:
        currency = "KRW" if asset_type.startswith("국내") else "USD"
    country = "OTHER" if asset_type == "코인" else _EXCHANGE_COUNTRY.get(
        exchange.upper(),
        "KR" if currency == "KRW" else "US" if currency == "USD" else "OTHER",
    )
    return ResolvedAsset(
        ticker=normalized,
        exchange=exchange,
        currency=currency,
        country=country,
        asset_type=asset_type,
        sector=str(info.get("sector") or "Unclassified"),
        display_name=str(info.get("longName") or info.get("shortName") or normalized).strip(),
        industry=str(info.get("industry") or ""),
        provider="Yahoo Finance",
    )


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
            return AssetResolution(query=query, status="exact", asset=replace(exact[0], confidence=1.0))
        scored = [
            replace(
                candidate,
                confidence=max(
                    SequenceMatcher(None, _normalize(query), _normalize(candidate.ticker)).ratio(),
                    SequenceMatcher(None, _normalize(query), _normalize(candidate.display_name)).ratio(),
                ),
            )
            for candidate in candidates
        ]
        reliable = [
            candidate for candidate in scored
            if candidate.confidence >= CANDIDATE_CONFIDENCE_THRESHOLD
        ]
        if len(reliable) == 1 and reliable[0].confidence >= AUTO_CONFIDENCE_THRESHOLD:
            return AssetResolution(query=query, status="fuzzy", asset=reliable[0])
        if reliable:
            return AssetResolution(query=query, status="ambiguous", candidates=reliable)
        return None


# Future remote providers can be appended here without changing resolve_asset()
# or any caller that consumes AssetResolution.
_PROVIDERS: tuple[AssetResolverProvider, ...] = (_AssetMasterProvider(), _YahooProvider())
_AI_RESOLVER_PROVIDER: AIAssetResolverProvider | None = None


def _persist_online_asset(asset: ResolvedAsset, query: str) -> None:
    record = AssetMasterRecord(
        ticker=asset.ticker,
        display_name=asset.display_name,
        asset_type=asset.asset_type,
        country=asset.country,
        currency=asset.currency,
        sector=asset.sector,
        industry=asset.industry,
        exchange=asset.exchange,
        provider=asset.provider or "Yahoo Finance",
        theme=asset.theme,
        is_dividend=asset.is_dividend,
        is_leveraged=asset.is_leveraged,
        company_name=asset.display_name if not any("가" <= char <= "힣" for char in asset.display_name) else "",
        company_name_ko=asset.display_name if any("가" <= char <= "힣" for char in asset.display_name) else "",
        aliases=(_normalize(query),),
        status="active",
    )
    upsert_asset_master(record, alias=query)


def resolve_asset(
    name: str,
    *,
    asset_type: str | None = None,
    include_external: bool = True,
    prefer_exact_ticker: bool = False,
) -> AssetResolution:
    """Resolve an asset name or ticker without silently selecting ambiguity."""
    query = str(name or "").strip()
    if asset_type is not None and not is_resolvable_asset_type(asset_type):
        return AssetResolution(query=query, status="Skip")
    if not query:
        return AssetResolution(query="", status="unknown")
    if prefer_exact_ticker and query == query.upper() and _TICKER_PATTERN.fullmatch(query):
        master_ticker = get_asset_master(query)
        if master_ticker is not None:
            return AssetResolution(query=query, status="exact", asset=_resolved_asset(master_ticker))
        if include_external:
            market_ticker = _lookup_yahoo_ticker(query)
            if market_ticker is not None:
                _persist_online_asset(market_ticker, query)
                return AssetResolution(query=query, status="exact", asset=market_ticker)
    local_result = _PROVIDERS[0].resolve(query)
    if local_result is not None and local_result.status != "unknown":
        return local_result
    if not include_external:
        return AssetResolution(query=query, status="unknown")

    # A bundled alias may point at an asset not shipped in the compact local
    # master. Preserve that deterministic hint when entering the online stage.
    alias_tickers = load_alias_dictionary().get(_normalize(query), ())
    online_query = alias_tickers[0] if len(alias_tickers) == 1 else query
    for provider in _PROVIDERS[1:]:
        result = provider.resolve(online_query)
        if result is not None and result.status != "unknown":
            if result.success and result.asset is not None:
                _persist_online_asset(result.asset, query)
            return AssetResolution(
                query=query,
                status=result.status,
                asset=result.asset,
                candidates=result.candidates,
            )
    if _AI_RESOLVER_PROVIDER is not None:
        result = _AI_RESOLVER_PROVIDER.resolve(query)
        if result is not None and result.status != "unknown":
            return result
    return AssetResolution(query=query, status="unknown")


def is_resolvable_asset_type(asset_type: object) -> bool:
    """Allow ticker lookup only for explicitly whitelisted market assets."""
    return str(asset_type or "").strip() in RESOLVABLE_ASSET_TYPES


def learn_asset_alias(asset_name: str, ticker: str) -> bool:
    """Validate a ticker, then persist the name-to-ticker association."""
    resolution = resolve_asset(ticker)
    if not resolution.success or resolution.asset is None:
        return False
    return save_learned_alias(asset_name, resolution.asset.ticker)


def enrich_asset_with_resolver(asset: dict[str, object]) -> dict[str, object]:
    """Fill portfolio metadata through the shared local resolver boundary."""
    enriched = dict(asset)
    asset_type = str(enriched.get("asset_type") or "").strip()
    if not is_resolvable_asset_type(asset_type):
        return enriched
    query = str(
        enriched.get("symbol") or enriched.get("ticker")
        or enriched.get("asset_name") or enriched.get("name") or ""
    )
    resolution = resolve_asset(
        query, asset_type=asset_type, include_external=False
    )
    if not resolution.success or resolution.asset is None:
        return enriched
    resolved = resolution.asset
    values = {
        "symbol": resolved.ticker,
        "ticker": resolved.ticker,
        "asset_type": resolved.asset_type,
        "country": resolved.country,
        "currency": resolved.currency,
        "sector": resolved.sector,
        "industry": resolved.industry,
        "exchange": resolved.exchange,
        "provider": resolved.provider,
        "theme": resolved.theme,
        "is_dividend": resolved.is_dividend,
        "is_leveraged": resolved.is_leveraged,
        "is_leverage": int(resolved.is_leveraged),
    }
    for key, value in values.items():
        if enriched.get(key) in (None, "", "Unclassified", "OTHER"):
            enriched[key] = value
    tags = [
        tag.strip() for tag in str(enriched.get("tags") or "").split(",")
        if tag.strip()
    ]
    tags.extend(tag.strip() for tag in resolved.theme.split("|") if tag.strip())
    if resolved.is_dividend:
        tags.append("Dividend")
    if resolved.is_leveraged:
        tags.append("Leveraged")
    if tags:
        enriched["tags"] = ",".join(dict.fromkeys(tags))
    return enriched

from __future__ import annotations

import csv
import json
import threading
import unicodedata
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_ASSET_MASTER_PATH = Path(__file__).resolve().parent.parent / "data" / "asset_master.csv"
ALIAS_DICTIONARY_PATH = Path(__file__).resolve().parent.parent / "resources" / "alias_dictionary.json"
LEARNED_ALIAS_PATH = Path(__file__).resolve().parent.parent / "data" / "learned_aliases.json"
LEARNED_MASTER_PATH = Path(__file__).resolve().parent.parent / "data" / "learned_asset_master.json"
FUZZY_THRESHOLD = 0.72
AMBIGUOUS_MARGIN = 0.06
_ALIAS_WRITE_LOCK = threading.Lock()


@dataclass(frozen=True)
class AssetMasterRecord:
    ticker: str
    display_name: str
    asset_type: str
    country: str
    currency: str
    sector: str
    industry: str
    exchange: str
    provider: str
    theme: str
    is_dividend: bool
    is_leveraged: bool
    company_name: str = ""
    company_name_ko: str = ""
    aliases: tuple[str, ...] = ()
    status: str = "active"


@dataclass(frozen=True)
class AssetMasterSearch:
    query: str
    status: str
    records: tuple[AssetMasterRecord, ...] = ()


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip().casefold()
    return " ".join(text.split())


@lru_cache(maxsize=1)
def load_alias_dictionary() -> dict[str, tuple[str, ...]]:
    """Load the one shared alias dictionary used by every search surface."""
    with ALIAS_DICTIONARY_PATH.open("r", encoding="utf-8") as source:
        aliases = json.load(source)
    if LEARNED_ALIAS_PATH.exists():
        try:
            with LEARNED_ALIAS_PATH.open("r", encoding="utf-8") as source:
                aliases.update(json.load(source))
        except (OSError, ValueError, TypeError):
            pass
    if LEARNED_MASTER_PATH.exists():
        try:
            learned_master = json.loads(LEARNED_MASTER_PATH.read_text(encoding="utf-8"))
            for record in learned_master.values():
                ticker = str(record.get("ticker") or "").strip().upper()
                for alias in record.get("aliases") or []:
                    if ticker:
                        aliases[str(alias)] = ticker
        except (OSError, ValueError, TypeError, AttributeError):
            pass
    return {
        _normalize(alias): tuple(
            str(ticker).strip().upper()
            for ticker in (value if isinstance(value, list) else [value])
        )
        for alias, value in aliases.items()
    }


def save_learned_alias(alias: str, ticker: str) -> bool:
    """Persist one validated alias in the learned Asset Master overlay."""
    normalized_alias = _normalize(alias)
    normalized_ticker = str(ticker or "").strip().upper()
    if not normalized_alias or not normalized_ticker:
        return False
    record = get_asset_master(normalized_ticker)
    if record is None:
        return False
    return upsert_asset_master(record, alias=normalized_alias)


def upsert_asset_master(record: AssetMasterRecord, *, alias: str = "") -> bool:
    """Atomically add online metadata or a learned alias to the master overlay."""
    with _ALIAS_WRITE_LOCK:
        learned: dict[str, dict[str, Any]] = {}
        if LEARNED_MASTER_PATH.exists():
            try:
                learned = json.loads(LEARNED_MASTER_PATH.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                learned = {}
        existing = dict(learned.get(record.ticker) or {})
        aliases = list(existing.get("aliases") or record.aliases)
        normalized_alias = _normalize(alias)
        if normalized_alias and normalized_alias not in aliases:
            aliases.append(normalized_alias)
        payload = {
            "ticker": record.ticker,
            "asset_type": record.asset_type,
            "company_name": record.company_name or record.display_name,
            "company_name_ko": record.company_name_ko,
            "aliases": aliases,
            "exchange": record.exchange,
            "currency": record.currency,
            "status": record.status or "active",
            "display_name": record.display_name,
            "country": record.country,
            "sector": record.sector,
            "industry": record.industry,
            "provider": record.provider,
            "theme": record.theme,
            "is_dividend": record.is_dividend,
            "is_leveraged": record.is_leveraged,
        }
        if existing == payload:
            return False
        learned[record.ticker] = payload
        temporary = LEARNED_MASTER_PATH.with_suffix(".tmp")
        try:
            temporary.write_text(
                json.dumps(learned, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
            temporary.replace(LEARNED_MASTER_PATH)
        except OSError:
            temporary.unlink(missing_ok=True)
            return False
    load_alias_dictionary.cache_clear()
    load_asset_master.cache_clear()
    _by_ticker.cache_clear()
    search_asset_master.cache_clear()
    return True


def _boolean(value: Any) -> bool:
    return _normalize(value) in {"1", "true", "yes", "y", "예"}


def _contains_korean(value: str) -> bool:
    return any("가" <= character <= "힣" for character in str(value or ""))


def _record_from_mapping(row: dict[str, Any], aliases: tuple[str, ...] = ()) -> AssetMasterRecord:
    display_name = str(
        row.get("display_name") or row.get("company_name_ko")
        or row.get("company_name") or row.get("ticker") or ""
    ).strip()
    return AssetMasterRecord(
        ticker=str(row.get("ticker") or "").strip().upper(),
        display_name=display_name,
        asset_type=str(row.get("asset_type") or "").strip(),
        country=str(row.get("country") or "OTHER").strip().upper(),
        currency=str(row.get("currency") or "").strip().upper(),
        sector=str(row.get("sector") or "Unclassified").strip(),
        industry=str(row.get("industry") or "").strip(),
        exchange=str(row.get("exchange") or "").strip(),
        provider=str(row.get("provider") or "AssetOS").strip(),
        theme=str(row.get("theme") or "").strip(),
        is_dividend=_boolean(row.get("is_dividend")),
        is_leveraged=_boolean(row.get("is_leveraged")),
        company_name=str(
            row.get("company_name") or ("" if _contains_korean(display_name) else display_name)
        ).strip(),
        company_name_ko=str(
            row.get("company_name_ko") or (display_name if _contains_korean(display_name) else "")
        ).strip(),
        aliases=tuple(dict.fromkeys(str(alias).strip() for alias in aliases if str(alias).strip())),
        status=str(row.get("status") or "active").strip(),
    )


@lru_cache(maxsize=4)
def load_asset_master(path: str | Path = DEFAULT_ASSET_MASTER_PATH) -> tuple[AssetMasterRecord, ...]:
    """Load the small local master lazily and cache immutable records."""
    aliases_by_ticker: dict[str, list[str]] = {}
    for alias, tickers in load_alias_dictionary().items():
        for ticker in tickers:
            aliases_by_ticker.setdefault(ticker, []).append(alias)
    with Path(path).open("r", encoding="utf-8-sig", newline="") as source:
        records = {
            str(row["ticker"]).strip().upper(): _record_from_mapping(
                row, tuple(aliases_by_ticker.get(str(row["ticker"]).strip().upper(), []))
            )
            for row in csv.DictReader(source)
        }
    if LEARNED_MASTER_PATH.exists():
        try:
            learned = json.loads(LEARNED_MASTER_PATH.read_text(encoding="utf-8"))
            for ticker, row in learned.items():
                records[str(ticker).upper()] = _record_from_mapping(
                    row, tuple(row.get("aliases") or ())
                )
        except (OSError, ValueError, TypeError, AttributeError):
            pass
    return tuple(records.values())


@lru_cache(maxsize=1)
def _by_ticker() -> dict[str, AssetMasterRecord]:
    return {record.ticker: record for record in load_asset_master()}


def get_asset_master(ticker: str) -> AssetMasterRecord | None:
    normalized = str(ticker or "").strip().upper()
    records = _by_ticker()
    if normalized in records:
        return records[normalized]
    if normalized.isdigit() and len(normalized) == 6:
        return records.get(f"{normalized}.KS") or records.get(f"{normalized}.KQ")
    return None


@lru_cache(maxsize=256)
def search_asset_master(query: str) -> AssetMasterSearch:
    original = str(query or "").strip()
    normalized = _normalize(original)
    if not normalized:
        return AssetMasterSearch(original, "unknown")

    records = _by_ticker()
    aliases = dict(load_alias_dictionary())

    def matches_for(field: str) -> tuple[AssetMasterRecord, ...]:
        return tuple(
            record
            for record in records.values()
            if _normalize(getattr(record, field)) == normalized
        )

    # One deterministic local pipeline shared by every caller: Korean company
    # name, English company name, learned/bundled alias, then ticker.
    for field in ("company_name_ko", "company_name"):
        name_matches = matches_for(field)
        if name_matches:
            return AssetMasterSearch(
                original,
                "exact" if len(name_matches) == 1 else "ambiguous",
                name_matches,
            )

    alias_tickers = aliases.get(normalized)
    if alias_tickers:
        alias_matches = tuple(
            records[ticker]
            for ticker in dict.fromkeys(alias_tickers)
            if ticker in records
        )
        if alias_matches:
            return AssetMasterSearch(
                original,
                "exact" if len(alias_matches) == 1 else "ambiguous",
                alias_matches,
            )

    ticker_match = get_asset_master(original)
    if ticker_match is not None:
        return AssetMasterSearch(original, "exact", (ticker_match,))

    for record in records.values():
        aliases.setdefault(_normalize(record.ticker), (record.ticker,))
        aliases.setdefault(_normalize(record.display_name), (record.ticker,))

    if len(normalized) >= 3:
        partial_tickers = tuple(
            ticker
            for alias, tickers in aliases.items()
            if len(alias) >= 3 and (normalized in alias or alias in normalized)
            for ticker in tickers
        )
        partial_matches = tuple(
            records[ticker]
            for ticker in dict.fromkeys(partial_tickers)
            if ticker in records
        )
        if partial_matches:
            return AssetMasterSearch(
                original,
                "fuzzy" if len(partial_matches) == 1 else "ambiguous",
                partial_matches,
            )

    scored = sorted(
        (
            (SequenceMatcher(None, normalized, alias).ratio(), tickers)
            for alias, tickers in aliases.items()
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    qualified = [item for item in scored if item[0] >= FUZZY_THRESHOLD]
    if not qualified:
        return AssetMasterSearch(original, "unknown")
    best = qualified[0][0]
    tickers = tuple(
        ticker
        for score, candidates in qualified
        if best - score <= AMBIGUOUS_MARGIN
        for ticker in candidates
    )
    matches = tuple(records[ticker] for ticker in dict.fromkeys(tickers) if ticker in records)
    return AssetMasterSearch(original, "fuzzy" if len(matches) == 1 else "ambiguous", matches)


def enrich_asset_metadata(asset: dict[str, Any]) -> dict[str, Any]:
    """Fill missing metadata from the master while preserving user/source values."""
    enriched = dict(asset)
    query = str(enriched.get("symbol") or enriched.get("ticker") or enriched.get("asset_name") or enriched.get("name") or "")
    search = search_asset_master(query)
    if len(search.records) != 1:
        return enriched
    record = search.records[0]
    master_values = {
        "symbol": record.ticker,
        "ticker": record.ticker,
        "asset_type": record.asset_type,
        "country": record.country,
        "currency": record.currency,
        "sector": record.sector,
        "industry": record.industry,
        "exchange": record.exchange,
        "provider": record.provider,
        "theme": record.theme,
        "is_dividend": record.is_dividend,
        "is_leveraged": record.is_leveraged,
        "is_leverage": int(record.is_leveraged),
    }
    for key, value in master_values.items():
        if enriched.get(key) in (None, "", "Unclassified", "OTHER"):
            enriched[key] = value

    tags = [tag.strip() for tag in str(enriched.get("tags") or "").split(",") if tag.strip()]
    tags.extend(theme.strip() for theme in record.theme.split("|") if theme.strip())
    if record.is_dividend:
        tags.append("Dividend")
    if record.is_leveraged:
        tags.append("Leveraged")
    if tags:
        enriched["tags"] = ",".join(dict.fromkeys(tags))
    return enriched


def asset_master_metadata(ticker: str) -> dict[str, Any]:
    record = get_asset_master(ticker)
    return asdict(record) if record else {}

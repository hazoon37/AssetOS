from __future__ import annotations

from typing import Any

from services.asset_resolver import resolve_asset

LEVERAGE_MAP: dict[str, float] = {
    "TQQQ": 3.0, "SQQQ": -3.0, "SOXL": 3.0, "SOXS": -3.0,
    "UPRO": 3.0, "SPXU": -3.0, "TECL": 3.0, "TECS": -3.0,
    "FAS": 3.0, "FAZ": -3.0, "LABU": 3.0, "LABD": -3.0,
    "QLD": 2.0, "QID": -2.0, "SSO": 2.0, "SDS": -2.0,
    "USD": 2.0, "PSQ": -1.0, "SH": -1.0,
}

CASH_EQUIVALENT_TICKERS = {"SGOV", "BIL", "SHV", "USFR", "TFLO", "MMF", "CASH"}
BOND_TICKERS = {"TLT", "IEF", "SHY", "GOVT", "AGG", "BND", "SGOV", "BIL", "SHV", "USFR", "TFLO"}
SEMICONDUCTOR_TICKERS = {"SOXL", "SOXS", "SOXX", "SMH", "USD", "XSD"}
TECH_TICKERS = {"QQQ", "QQQM", "TQQQ", "SQQQ", "QLD", "QID", "VGT", "XLK", "TECL", "TECS"}
BROAD_US_TICKERS = {"SPY", "VOO", "IVV", "SPLG", "SPYM", "VTI", "UPRO", "SPXU", "SSO", "SDS"}

ASSET_CLASS_LABELS = {
    "STOCK": "개별주식",
    "ETF": "ETF",
    "BOND": "채권",
    "CASH": "현금성",
    "CRYPTO": "코인",
    "REAL_ESTATE": "부동산",
    "PENSION": "연금·절세계좌",
    "ALTERNATIVE": "기타",
}

COUNTRY_LABELS = {
    "KR": "한국",
    "US": "미국",
    "JP": "일본",
    "HK": "홍콩",
    "CN": "중국",
    "GB": "영국",
    "EU": "유럽",
    "GLOBAL": "글로벌",
    "OTHER": "기타",
}


def _text(value: Any) -> str:
    return str(value or "").strip()


def infer_asset_class(asset_type: str, symbol: str = "") -> str:
    asset_type = _text(asset_type)
    ticker = _text(symbol).upper()
    if asset_type in {"현금·예금", "현금", "예금", "CMA", "MMF"}:
        return "CASH"
    if asset_type in {"국내주식", "미국주식"}:
        return "STOCK"
    if asset_type in {"국내ETF", "미국ETF"}:
        return "BOND" if ticker in BOND_TICKERS else "ETF"
    if asset_type in {"국내채권", "미국채권"}:
        return "BOND"
    if asset_type == "코인":
        return "CRYPTO"
    if asset_type == "부동산":
        return "REAL_ESTATE"
    if asset_type in {"ISA", "IRP", "연금저축"}:
        return "PENSION"
    return "ALTERNATIVE"


def infer_country(asset_type: str, currency: str, exchange: str = "") -> str:
    asset_type = _text(asset_type)
    currency = _text(currency).upper()
    exchange = _text(exchange).upper()
    if asset_type == "코인":
        return "GLOBAL"
    if asset_type in {"국내주식", "국내ETF", "국내채권", "부동산"}:
        return "KR"
    if asset_type in {"미국주식", "미국ETF", "미국채권"}:
        return "US"
    if "KOSPI" in exchange or "KOSDAQ" in exchange:
        return "KR"
    if any(x in exchange for x in ("NASDAQ", "NYSE", "AMEX", "NMS", "NYQ")):
        return "US"
    return {
        "KRW": "KR", "USD": "US", "JPY": "JP", "HKD": "HK",
        "GBP": "GB", "EUR": "EU",
    }.get(currency, "GLOBAL" if asset_type == "코인" else "OTHER")


def infer_sector(symbol: str, asset_class: str, sector: str = "", industry: str = "") -> str:
    ticker = _text(symbol).upper()
    existing_sector = _text(sector)
    if existing_sector and existing_sector != "Unclassified":
        return existing_sector
    if ticker in SEMICONDUCTOR_TICKERS:
        return "Semiconductors"
    if ticker in TECH_TICKERS:
        return "Technology"
    if ticker in BROAD_US_TICKERS:
        return "Broad Market"
    if ticker in BOND_TICKERS or asset_class == "BOND":
        return "Fixed Income"
    if asset_class == "CASH":
        return "Cash"
    if asset_class == "CRYPTO":
        return "Crypto"
    if asset_class == "REAL_ESTATE":
        return "Real Estate"
    return _text(industry) or "Unclassified"


def classify_asset(
    *,
    asset_type: str,
    symbol: str = "",
    currency: str = "KRW",
    exchange: str = "",
    sector: str = "",
    industry: str = "",
) -> dict[str, Any]:
    ticker = _text(symbol).upper()
    resolution = resolve_asset(
        ticker, asset_type=asset_type, include_external=False
    )
    master = resolution.asset if resolution.success else None
    effective_asset_type = _text(asset_type) or (master.asset_type if master else "")
    effective_exchange = _text(exchange) or (master.exchange if master else "")
    effective_sector = _text(sector) or (master.sector if master else "")
    effective_industry = _text(industry) or (master.industry if master else "")
    asset_class = infer_asset_class(effective_asset_type, ticker)
    leverage_multiple = LEVERAGE_MAP.get(ticker, 1.0)
    is_inverse = leverage_multiple < 0
    is_leverage = abs(leverage_multiple) > 1.0 or is_inverse or bool(master and master.is_leveraged)
    is_cash = asset_class == "CASH" or ticker in CASH_EQUIVALENT_TICKERS
    if ticker in CASH_EQUIVALENT_TICKERS and asset_class in {"ETF", "BOND"}:
        # 초단기채 ETF는 자산군은 채권으로 유지하되 현금성 플래그를 부여합니다.
        is_cash = True
    country = master.country if master else infer_country(effective_asset_type, currency, effective_exchange)
    normalized_sector = infer_sector(ticker, asset_class, effective_sector, effective_industry)
    tags: list[str] = []
    if ticker in SEMICONDUCTOR_TICKERS:
        tags += ["AI", "Semiconductor"]
    if ticker in TECH_TICKERS:
        tags += ["Technology", "Growth"]
    if ticker in BROAD_US_TICKERS:
        tags += ["US Market", "Core"]
    if is_leverage:
        tags.append("Leveraged")
    if is_inverse:
        tags.append("Inverse")
    if is_cash:
        tags.append("Cash Equivalent")
    if master:
        tags.extend(theme.strip() for theme in master.theme.split("|") if theme.strip())
        if master.is_dividend:
            tags.append("Dividend")
    return {
        "asset_class": asset_class,
        "country": country,
        "exchange": effective_exchange,
        "sector": normalized_sector,
        "industry": effective_industry,
        "is_cash": int(is_cash),
        "is_leverage": int(is_leverage),
        "is_inverse": int(is_inverse),
        "leverage_multiple": float(leverage_multiple),
        "data_source": master.provider if master else "AssetOS Classification",
        "tags": ",".join(dict.fromkeys(tags)),
    }

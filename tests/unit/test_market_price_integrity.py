from unittest.mock import patch

from services.asset_resolver import AssetResolution, ResolvedAsset
from services.market_price_service import get_market_price


def test_crypto_price_provider_uses_requested_portfolio_currency() -> None:
    bitcoin = ResolvedAsset(
        "BTC", "CoinGecko", "USD", "GLOBAL", "코인", "Cryptocurrency", "Bitcoin"
    )
    with patch(
        "services.market_price_service.resolve_asset",
        return_value=AssetResolution("BTC", "exact", asset=bitcoin),
    ), patch(
        "services.market_price_service.get_crypto_price",
        return_value={"success": True, "price": 100_000_000, "currency": "KRW"},
    ) as provider:
        result = get_market_price("코인", "BTC", "KRW")
    assert result["success"] is True
    provider.assert_called_once_with(symbol="BTC", currency="KRW")

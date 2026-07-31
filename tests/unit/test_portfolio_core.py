import unittest

from services.asset_classification import classify_asset
from services.portfolio_analyzer import analyze_portfolio


class PortfolioCoreTests(unittest.TestCase):
    def test_leveraged_etf_classification(self):
        result = classify_asset(asset_type="미국ETF", symbol="SOXL", currency="USD")
        self.assertEqual(result["asset_class"], "ETF")
        self.assertEqual(result["country"], "US")
        self.assertEqual(result["leverage_multiple"], 3.0)
        self.assertEqual(result["is_leverage"], 1)
        self.assertEqual(result["sector"], "Semiconductors")

    def test_portfolio_summary_and_allocations(self):
        assets = [
            {
                "name": "SPYM", "symbol": "SPYM", "asset_class": "ETF", "country": "US",
                "currency": "USD", "sector": "Broad Market", "value_krw": 64_700_000,
                "cost_value_krw": 60_000_000, "is_cash": False, "is_leverage": False,
                "is_inverse": False, "leverage_multiple": 1.0,
            },
            {
                "name": "TQQQ", "symbol": "TQQQ", "asset_class": "ETF", "country": "US",
                "currency": "USD", "sector": "Technology", "value_krw": 17_600_000,
                "cost_value_krw": 15_000_000, "is_cash": False, "is_leverage": True,
                "is_inverse": False, "leverage_multiple": 3.0,
            },
            {
                "name": "SOXL", "symbol": "SOXL", "asset_class": "ETF", "country": "US",
                "currency": "USD", "sector": "Semiconductors", "value_krw": 11_800_000,
                "cost_value_krw": 10_000_000, "is_cash": False, "is_leverage": True,
                "is_inverse": False, "leverage_multiple": 3.0,
            },
            {
                "name": "현금", "symbol": "CASH", "asset_class": "CASH", "country": "KR",
                "currency": "KRW", "sector": "Cash", "value_krw": 5_900_000,
                "cost_value_krw": 5_900_000, "is_cash": True, "is_leverage": False,
                "is_inverse": False, "leverage_multiple": 1.0,
            },
        ]
        result = analyze_portfolio(assets)
        self.assertTrue(result["success"])
        self.assertAlmostEqual(result["summary"]["cash_weight"], 0.059, places=3)
        self.assertAlmostEqual(result["summary"]["leveraged_weight"], 0.294, places=3)
        self.assertAlmostEqual(result["summary"]["gross_exposure"], 1.529, places=3)
        self.assertEqual(result["allocations"]["country"][0]["label"], "미국")


if __name__ == "__main__":
    unittest.main()

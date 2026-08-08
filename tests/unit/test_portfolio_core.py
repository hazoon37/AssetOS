import unittest
from unittest.mock import patch

from services.asset_classification import classify_asset
from services.portfolio_analyzer import analyze_portfolio
from services.portfolio_service import analyze_asset_rows, calculate_asset_values


class PortfolioCoreTests(unittest.TestCase):
    def test_in_memory_analysis_requires_no_repository(self):
        result = analyze_asset_rows(
            [{
                "asset_name": "현금", "asset_type": "현금·예금", "asset_class": "CASH",
                "quantity": 1, "average_price": 100, "current_price": 100,
                "currency": "KRW", "is_cash": True,
            }],
            {"KRW": 1.0},
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["source_asset_count"], 1)

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

    def test_invalid_price_is_refetched_before_profit_calculation(self):
        market_result = {
            "success": True, "price": 200.0, "currency": "USD", "symbol": "GOOGL"
        }
        with patch("services.portfolio_service.get_market_price", return_value=market_result):
            result = analyze_asset_rows([{
                "asset_name": "Alphabet", "symbol": "GOOGL", "asset_type": "미국주식",
                "quantity": 2, "average_price": 150, "current_price": float("nan"),
                "currency": "USD",
            }], {"KRW": 1.0, "USD": 1_400.0})
        asset = result["assets"][0]
        self.assertEqual(asset["current_price"], 200.0)
        self.assertEqual(asset["value_krw"], 560_000.0)
        self.assertAlmostEqual(asset["return_rate"], 1 / 3)

    def test_representative_assets_use_one_finite_profit_formula(self):
        cases = [
            ("BTC", 100_000_000, 120_000_000, "KRW"),
            ("DFDV", 24.08, 2.89, "USD"),
            ("SBET", 29.886, 6.43, "USD"),
            ("Greety", 3_209, 3_500, "KRW"),
            ("GOOGL", 300, 354.30, "USD"),
            ("NVDA", 180, 223.96, "USD"),
            ("TMF", 40, 31.43, "USD"),
            ("BITX", 20, 12.41, "USD"),
            ("ACE 미국S&P500", 25_000, 27_365, "KRW"),
            ("TIGER 미국나스닥100", 170_000, 184_660, "KRW"),
        ]
        for name, average, current, currency in cases:
            values = calculate_asset_values(1, average, current, currency, {"KRW": 1, "USD": 1_400})
            self.assertIsNotNone(values, name)
            assert values is not None
            self.assertGreater(values["value_krw"], 0, name)
            self.assertAlmostEqual(
                values["profit_loss_krw"],
                values["value_krw"] - values["cost_value_krw"],
                msg=name,
            )

    def test_exact_asset_name_repairs_mismatched_ticker_and_price(self):
        with patch(
            "services.portfolio_service.get_market_price",
            return_value={"success": True, "price": 3_500.0},
        ) as provider:
            result = analyze_asset_rows([{
                "asset_name": "그리티", "symbol": "034020.KS", "asset_type": "국내주식",
                "quantity": 350, "average_price": 3_209, "current_price": 77_100,
                "currency": "KRW",
            }], {"KRW": 1.0})
        asset = result["assets"][0]
        self.assertEqual(asset["symbol"], "204020.KQ")
        self.assertEqual(asset["current_price"], 3_500.0)
        self.assertLess(abs(asset["return_rate"]), 1.0)
        provider.assert_called_once_with(
            asset_type="국내주식", symbol="204020.KQ", currency="KRW"
        )

    def test_listing_currency_mismatch_forces_price_refresh(self):
        with patch(
            "services.portfolio_service.get_market_price",
            return_value={"success": True, "price": 200.0},
        ) as provider:
            result = analyze_asset_rows([{
                "asset_name": "Apple", "symbol": "AAPL", "asset_type": "미국주식",
                "quantity": 1, "average_price": 150, "current_price": 280_000,
                "currency": "KRW",
            }], {"KRW": 1.0, "USD": 1_400.0})
        asset = result["assets"][0]
        self.assertEqual(asset["currency"], "USD")
        self.assertEqual(asset["current_price"], 200.0)
        provider.assert_called_once_with(
            asset_type="미국주식", symbol="AAPL", currency="USD"
        )

    def test_extreme_btc_ratio_is_refetched_as_quote_currency_corruption(self):
        with patch(
            "services.portfolio_service.get_market_price",
            return_value={"success": True, "price": 120_000_000.0},
        ) as provider:
            result = analyze_asset_rows([{
                "asset_name": "비트코인", "symbol": "BTC", "asset_type": "코인",
                "quantity": 0.5, "average_price": 135_975_879,
                "current_price": 64_946, "currency": "KRW",
            }], {"KRW": 1.0})
        asset = result["assets"][0]
        self.assertEqual(asset["current_price"], 120_000_000.0)
        self.assertGreater(asset["return_rate"], -0.2)
        provider.assert_called_once_with(asset_type="코인", symbol="BTC", currency="KRW")


if __name__ == "__main__":
    unittest.main()

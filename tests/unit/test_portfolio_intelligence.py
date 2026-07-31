from services.portfolio_analyzer import analyze_portfolio


def sample_assets():
    return [
        {"name": "SPYM", "symbol": "SPYM", "asset_class": "ETF", "country": "US", "currency": "USD", "sector": "Broad Market", "value_krw": 64_700_000, "cost_value_krw": 55_000_000, "is_cash": False, "is_leverage": False, "is_inverse": False, "leverage_multiple": 1.0, "tags": "US Market,Core"},
        {"name": "TQQQ", "symbol": "TQQQ", "asset_class": "ETF", "country": "US", "currency": "USD", "sector": "Technology", "value_krw": 17_600_000, "cost_value_krw": 15_000_000, "is_cash": False, "is_leverage": True, "is_inverse": False, "leverage_multiple": 3.0, "tags": "Technology,Growth,Leveraged"},
        {"name": "SOXL", "symbol": "SOXL", "asset_class": "ETF", "country": "US", "currency": "USD", "sector": "Semiconductor", "value_krw": 11_800_000, "cost_value_krw": 10_000_000, "is_cash": False, "is_leverage": True, "is_inverse": False, "leverage_multiple": 3.0, "tags": "AI,Semiconductor,Leveraged"},
        {"name": "현금", "symbol": "CASH", "asset_class": "CASH", "country": "KR", "currency": "KRW", "sector": "Cash", "value_krw": 5_900_000, "cost_value_krw": 5_900_000, "is_cash": True, "is_leverage": False, "is_inverse": False, "leverage_multiple": 1.0, "tags": "Cash Equivalent"},
    ]


def test_intelligence_sections_exist():
    result = analyze_portfolio(sample_assets())
    assert result["success"] is True
    assert 0 <= result["score"]["total"] <= 100
    assert len(result["stress_tests"]) == 4
    assert result["investment_dna"]
    assert result["insights"]


def test_stress_broad_selloff_is_negative():
    result = analyze_portfolio(sample_assets())
    broad = next(row for row in result["stress_tests"] if row["key"] == "broad_selloff")
    assert broad["impact_rate"] < 0

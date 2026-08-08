from __future__ import annotations

from services.ai_advisor import generate_portfolio_advice
from services.portfolio_ai_service import (
    PortfolioAIProvider,
    RuleBasedPortfolioAIProvider,
)


def test_advisor_uses_structured_portfolio_values() -> None:
    portfolio = {
        "success": True,
        "summary": {
            "asset_count": 4,
            "total_value_krw": 1_000_000,
            "profit_loss_krw": 50_000,
        },
        "concentration": {
            "effective_asset_count": 2.5,
            "top_1_weight": 0.55,
            "level": "높음",
        },
        "allocations": {
            "currency": [{"label": "USD", "weight": 0.7}],
            "sector": [{"label": "Technology", "weight": 0.6}],
            "account": [{"label": "ISA", "weight": 0.8}],
        },
    }
    advice = generate_portfolio_advice(portfolio)
    assert "4개" in advice.diversification
    assert "55.0%" in advice.concentration
    assert "USD" in advice.currency_risk
    assert "Technology" in advice.sector_risk
    assert "ISA" in advice.account_advice
    assert "1,000,000원" in advice.investment_summary


def test_advisor_handles_insufficient_data_without_fabrication() -> None:
    advice = generate_portfolio_advice({"success": False})
    assert all("판단할 수 없습니다" in value for value in advice.to_dict().values())


def test_portfolio_ai_contract_is_openai_provider_ready() -> None:
    assert issubclass(RuleBasedPortfolioAIProvider, PortfolioAIProvider)

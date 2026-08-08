from __future__ import annotations

import json

from services.portfolio_ai_service import diagnose_portfolio
from services.portfolio_analyzer import analyze_portfolio
from services.quick_analysis_export_service import (
    export_quick_analysis_json,
    export_quick_analysis_pdf,
    export_quick_analysis_png,
)


def _analysis() -> dict[str, object]:
    return analyze_portfolio([{
        "name": "Apple", "symbol": "AAPL", "asset_class": "STOCK",
        "country": "US", "currency": "USD", "sector": "Technology",
        "account_name": "Quick Analysis", "value_krw": 1_200_000,
        "cost_value_krw": 1_000_000, "is_cash": False,
        "is_leverage": False, "is_inverse": False, "leverage_multiple": 1,
    }])


def test_quick_exports_generate_pdf_png_and_json() -> None:
    analysis = _analysis()
    diagnosis = diagnose_portfolio(analysis)
    assert export_quick_analysis_pdf(analysis).startswith(b"%PDF")
    assert export_quick_analysis_pdf(analysis, diagnosis).startswith(b"%PDF")
    assert export_quick_analysis_png(analysis, diagnosis).startswith(b"\x89PNG")
    payload = json.loads(export_quick_analysis_json(analysis, diagnosis))
    assert payload["format"] == "AssetOS Quick Analysis"
    assert payload["advisor"]["overall_score"] == diagnosis.overall_score
    assert payload["advisor"]["risk_level"] == diagnosis.risk_level
    assert payload["advisor"]["recommended_actions"]

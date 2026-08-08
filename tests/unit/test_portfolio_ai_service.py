from __future__ import annotations

from services.portfolio_ai_service import (
    allocation_ratio,
    build_rule_cards,
    calculate_metrics,
    calculate_scores,
    diagnose_portfolio,
)


def _portfolio() -> dict[str, object]:
    return {
        "success": True,
        "summary": {"cash_weight": 0.02, "leveraged_weight": 0.25},
        "score": {
            "total": 62.5,
            "categories": {
                "diversification": 45.0,
                "leverage_control": 40.0,
                "cash_flexibility": 40.0,
            },
        },
        "concentration": {"top_1_weight": 0.55},
        "allocations": {
            "country": [
                {"code": "US", "label": "미국", "weight": 0.70},
                {"code": "KR", "label": "한국", "weight": 0.30},
            ],
            "asset_class": [
                {"code": "ETF", "weight": 0.45},
                {"code": "STOCK", "weight": 0.25},
                {"code": "CRYPTO", "weight": 0.20},
                {"code": "REAL_ESTATE", "weight": 0.10},
            ],
        },
    }


def test_allocation_ratio_matches_code_and_bounds_result() -> None:
    assert allocation_ratio(_portfolio(), "country", "us") == 0.70
    assert allocation_ratio(_portfolio(), "country", "JP") == 0.0
    source = {"allocations": {"country": [{"code": "US", "weight": 1.2}]}}
    assert allocation_ratio(source, "country", "US") == 1.0


def test_calculate_scores_uses_existing_structured_categories() -> None:
    total, diversification, risk = calculate_scores(_portfolio())
    assert total == 62.5
    assert diversification == 45.0
    assert risk == 41.2
    bounded = {"score": {"total": 120, "categories": {"diversification": -1}}}
    assert calculate_scores(bounded)[0:2] == (100.0, 0.0)


def test_calculate_metrics_returns_every_requested_ratio() -> None:
    metrics = calculate_metrics(_portfolio())
    assert metrics.cash_ratio == 0.02
    assert metrics.us_ratio == 0.70
    assert metrics.kr_ratio == 0.30
    assert metrics.etf_ratio == 0.45
    assert metrics.stock_ratio == 0.25
    assert metrics.crypto_ratio == 0.20
    assert metrics.real_estate_ratio == 0.10


def test_build_rule_cards_applies_leverage_cash_etf_and_concentration_rules() -> None:
    metrics = calculate_metrics(_portfolio())
    strengths, risks, recommendations = build_rule_cards(_portfolio(), metrics)
    assert any("ETF 비중" in item for item in strengths)
    assert any("레버리지" in item for item in risks)
    assert any("현금 비중" in item for item in risks)
    assert any("단일 자산" in item for item in risks)
    assert any("레버리지 비중 축소" in item for item in recommendations)
    assert any("현금 확보" in item for item in recommendations)


def test_build_rule_cards_always_returns_nonempty_cards() -> None:
    balanced = _portfolio()
    balanced["summary"] = {"cash_weight": 0.10, "leveraged_weight": 0.0}
    balanced["concentration"] = {"top_1_weight": 0.20}
    balanced["score"] = {
        "total": 90,
        "categories": {
            "diversification": 90,
            "leverage_control": 100,
            "cash_flexibility": 100,
        },
    }
    balanced["allocations"]["asset_class"][2]["weight"] = 0.05
    cards = build_rule_cards(balanced, calculate_metrics(balanced))
    assert all(cards)


def test_diagnose_portfolio_returns_result_and_rejects_empty_analysis() -> None:
    diagnosis = diagnose_portfolio(_portfolio())
    assert diagnosis.overall_score == 62.5
    assert diagnosis.metrics.portfolio_score == 62.5
    assert diagnosis.strengths
    assert diagnosis.weaknesses
    assert diagnosis.risks
    assert diagnosis.risk == diagnosis.risks
    assert diagnosis.recommendations
    assert diagnosis.next_action == diagnosis.recommendations[0]
    assert diagnosis.risk_level in {"낮음", "보통", "높음"}
    assert diagnosis.diversification_score == diagnosis.metrics.diversification_score
    assert diagnosis.cash_ratio == diagnosis.metrics.cash_ratio
    assert diagnosis.top_strengths == diagnosis.strengths[:3]
    assert diagnosis.top_risks == diagnosis.combined_risks[:3]
    assert diagnosis.recommended_actions == diagnosis.recommendations[:5]
    try:
        diagnose_portfolio({"success": False})
    except ValueError as error:
        assert "분석 가능한" in str(error)
    else:
        raise AssertionError("분석 불가 포트폴리오는 ValueError를 발생시켜야 합니다.")

from __future__ import annotations

from collections import defaultdict
from typing import Any


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def _largest_weight(rows: list[dict[str, Any]]) -> float:
    return max((_float(row.get("weight")) for row in rows), default=0.0)


def _score_diversification(concentration: dict[str, Any]) -> float:
    hhi = _float(concentration.get("hhi"))
    top1 = _float(concentration.get("top_1_weight"))
    # HHI 0.10 이하를 우수, 0.50 이상을 취약으로 봅니다.
    hhi_score = _clamp((0.50 - hhi) / 0.40 * 100)
    top1_score = _clamp((0.60 - top1) / 0.45 * 100)
    return round(hhi_score * 0.65 + top1_score * 0.35, 1)


def _score_cash(cash_weight: float) -> float:
    # 5~15% 구간을 가장 유연한 수준으로 평가합니다.
    if 0.05 <= cash_weight <= 0.15:
        return 100.0
    if cash_weight < 0.05:
        return round(_clamp(cash_weight / 0.05 * 100), 1)
    if cash_weight <= 0.30:
        return round(_clamp(100 - (cash_weight - 0.15) / 0.15 * 35), 1)
    return round(_clamp(65 - (cash_weight - 0.30) / 0.40 * 65), 1)


def _score_leverage(leveraged_weight: float, gross_exposure: float) -> float:
    weight_penalty = max(0.0, leveraged_weight - 0.10) * 180
    exposure_penalty = max(0.0, gross_exposure - 1.10) * 65
    return round(_clamp(100 - weight_penalty - exposure_penalty), 1)


def _score_distribution(rows: list[dict[str, Any]], preferred_max: float = 0.70) -> float:
    largest = _largest_weight(rows)
    if largest <= preferred_max:
        return 100.0
    return round(_clamp(100 - (largest - preferred_max) / (1 - preferred_max) * 75), 1)


def build_portfolio_score(
    summary: dict[str, Any],
    concentration: dict[str, Any],
    allocations: dict[str, Any],
) -> dict[str, Any]:
    category_scores = {
        "diversification": _score_diversification(concentration),
        "cash_flexibility": _score_cash(_float(summary.get("cash_weight"))),
        "leverage_control": _score_leverage(
            _float(summary.get("leveraged_weight")),
            _float(summary.get("gross_exposure")),
        ),
        "country_balance": _score_distribution(allocations.get("country", []), 0.75),
        "currency_balance": _score_distribution(allocations.get("currency", []), 0.75),
    }
    weights = {
        "diversification": 0.30,
        "cash_flexibility": 0.15,
        "leverage_control": 0.30,
        "country_balance": 0.125,
        "currency_balance": 0.125,
    }
    total = sum(category_scores[key] * weights[key] for key in category_scores)
    if total >= 85:
        grade = "A"
        label = "우수"
    elif total >= 70:
        grade = "B"
        label = "양호"
    elif total >= 55:
        grade = "C"
        label = "보통"
    elif total >= 40:
        grade = "D"
        label = "주의"
    else:
        grade = "E"
        label = "고위험"
    return {
        "total": round(total, 1),
        "grade": grade,
        "label": label,
        "categories": category_scores,
        "method": "분산 30%, 레버리지 30%, 현금 15%, 국가 12.5%, 통화 12.5%의 규칙 기반 점수",
    }


def _asset_shock(asset: dict[str, Any], scenario: str) -> float:
    asset_class = str(asset.get("asset_class") or "ALTERNATIVE")
    sector = str(asset.get("sector") or "").lower()
    leverage = _float(asset.get("leverage_multiple"), 1.0)
    is_cash = bool(asset.get("is_cash"))
    if is_cash:
        return 0.0

    base: dict[str, dict[str, float]] = {
        "broad_selloff": {
            "STOCK": -0.20, "ETF": -0.18, "BOND": 0.02, "CRYPTO": -0.35,
            "REAL_ESTATE": -0.10, "PENSION": -0.12, "ALTERNATIVE": -0.12,
        },
        "tech_correction": {
            "STOCK": -0.10, "ETF": -0.08, "BOND": 0.01, "CRYPTO": -0.18,
            "REAL_ESTATE": -0.04, "PENSION": -0.06, "ALTERNATIVE": -0.06,
        },
        "rate_shock": {
            "STOCK": -0.08, "ETF": -0.07, "BOND": -0.06, "CRYPTO": -0.15,
            "REAL_ESTATE": -0.10, "PENSION": -0.06, "ALTERNATIVE": -0.05,
        },
        "usd_weakness": {
            "STOCK": 0.0, "ETF": 0.0, "BOND": 0.0, "CRYPTO": 0.0,
            "REAL_ESTATE": 0.0, "PENSION": 0.0, "ALTERNATIVE": 0.0,
        },
    }
    shock = base[scenario].get(asset_class, -0.08)
    if scenario == "tech_correction" and any(token in sector for token in ("tech", "semi", "ai", "technology", "반도체")):
        shock -= 0.12
    if scenario == "broad_selloff" and asset.get("is_inverse"):
        return min(0.30, abs(leverage) * 0.10)
    if scenario == "usd_weakness":
        return -0.10 if str(asset.get("currency") or "KRW").upper() == "USD" else 0.0
    if abs(leverage) > 1:
        shock *= abs(leverage)
    return max(-0.85, min(0.50, shock))


def build_stress_tests(assets: list[dict[str, Any]], total_value_krw: float) -> list[dict[str, Any]]:
    scenarios = [
        ("broad_selloff", "글로벌 위험자산 급락", "주식 -20%, 코인 -35%를 기초로 레버리지 배수를 반영한 단순 충격"),
        ("tech_correction", "기술주·AI 조정", "기술·반도체에 추가 하락 충격을 적용"),
        ("rate_shock", "금리 급등", "성장주·장기채·부동산에 부정적 충격을 적용"),
        ("usd_weakness", "달러 10% 약세", "USD 표시 자산의 원화 평가액이 10% 감소한다고 가정"),
    ]
    results: list[dict[str, Any]] = []
    for key, label, description in scenarios:
        impact = sum(
            _float(asset.get("value_krw")) * _asset_shock(asset, key)
            for asset in assets
        )
        results.append({
            "key": key,
            "label": label,
            "description": description,
            "impact_krw": impact,
            "impact_rate": impact / total_value_krw if total_value_krw > 0 else 0.0,
            "after_value_krw": total_value_krw + impact,
        })
    return results


def build_investment_dna(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    exposure: dict[str, float] = defaultdict(float)
    total = sum(_float(asset.get("value_krw")) for asset in assets)
    for asset in assets:
        value = _float(asset.get("value_krw"))
        tags = [tag.strip() for tag in str(asset.get("tags") or "").split(",") if tag.strip()]
        sector = str(asset.get("sector") or "").strip()
        if sector and sector != "Unclassified":
            tags.append(sector)
        if asset.get("is_leverage"):
            tags.append("레버리지")
        if asset.get("is_cash"):
            tags.append("유동성")
        if str(asset.get("asset_class")) == "CRYPTO":
            tags.append("고변동성 대체자산")
        for tag in dict.fromkeys(tags):
            exposure[tag] += value
    return [
        {"theme": theme, "value_krw": value, "weight": value / total if total > 0 else 0.0}
        for theme, value in sorted(exposure.items(), key=lambda item: item[1], reverse=True)[:10]
    ]


def build_insights(
    summary: dict[str, Any],
    concentration: dict[str, Any],
    allocations: dict[str, Any],
    score: dict[str, Any],
) -> list[str]:
    insights = [f"포트폴리오 진단 점수는 {score['total']:.1f}점({score['grade']}등급, {score['label']})입니다."]
    top_asset = _float(concentration.get("top_1_weight"))
    if top_asset >= 0.50:
        insights.append(f"최대 자산 비중이 {top_asset * 100:.1f}%로 단일 자산 의존도가 높습니다.")
    leverage = _float(summary.get("leveraged_weight"))
    if leverage >= 0.20:
        insights.append(f"레버리지 자산 비중이 {leverage * 100:.1f}%여서 하락장 손실 속도가 빨라질 수 있습니다.")
    cash = _float(summary.get("cash_weight"))
    if cash < 0.05:
        insights.append(f"현금성 비중이 {cash * 100:.1f}%로 조정 시 추가매수 여력이 제한적입니다.")
    elif cash <= 0.15:
        insights.append(f"현금성 비중 {cash * 100:.1f}%는 유동성과 투자 효율의 균형 구간에 있습니다.")
    country = allocations.get("country", [])
    if country:
        insights.append(f"가장 큰 국가 노출은 {country[0]['label']} {country[0]['weight'] * 100:.1f}%입니다.")
    return insights

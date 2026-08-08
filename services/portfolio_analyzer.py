from __future__ import annotations

from collections import defaultdict
from typing import Any

from services.asset_classification import ASSET_CLASS_LABELS, COUNTRY_LABELS
from services.portfolio_intelligence import (
    build_investment_dna,
    build_insights,
    build_portfolio_score,
    build_stress_tests,
)


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _group_by_value(assets: list[dict[str, Any]], key: str, labels: dict[str, str] | None = None) -> list[dict[str, Any]]:
    grouped: dict[str, float] = defaultdict(float)
    for asset in assets:
        code = str(asset.get(key) or "OTHER")
        grouped[code] += _float(asset.get("value_krw"))
    total = sum(grouped.values())
    rows = []
    for code, value in sorted(grouped.items(), key=lambda item: item[1], reverse=True):
        rows.append({
            "code": code,
            "label": (labels or {}).get(code, code or "미분류"),
            "value_krw": value,
            "weight": value / total if total > 0 else 0.0,
        })
    return rows


def _concentration(weights: list[float]) -> dict[str, Any]:
    ordered = sorted(weights, reverse=True)
    hhi = sum(weight ** 2 for weight in weights)
    if hhi >= 0.25:
        level = "높음"
    elif hhi >= 0.15:
        level = "보통"
    else:
        level = "낮음"
    return {
        "top_1_weight": sum(ordered[:1]),
        "top_3_weight": sum(ordered[:3]),
        "top_5_weight": sum(ordered[:5]),
        "hhi": hhi,
        "level": level,
        "effective_asset_count": (1 / hhi) if hhi > 0 else 0.0,
    }


def _warnings(summary: dict[str, Any], concentration: dict[str, Any], allocations: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    leverage = summary["leveraged_weight"]
    cash = summary["cash_weight"]
    if leverage >= 0.30:
        warnings.append("레버리지 자산 비중이 30% 이상입니다. 급락장과 변동성 높은 횡보장에서 손실이 빠르게 확대될 수 있습니다.")
    elif leverage >= 0.20:
        warnings.append("레버리지 자산 비중이 20% 이상입니다. 포트폴리오 변동성 관리가 필요합니다.")
    if cash < 0.05:
        warnings.append("현금성 자산 비중이 5% 미만입니다. 추가매수와 비상 유동성 여력이 제한될 수 있습니다.")
    if concentration["top_1_weight"] >= 0.50:
        warnings.append("최대 보유자산 비중이 50% 이상입니다. 단일 자산 가격 변화가 전체 성과를 크게 좌우합니다.")
    if concentration["top_3_weight"] >= 0.85:
        warnings.append("상위 3개 자산 비중이 85% 이상으로 집중도가 높습니다.")
    country = allocations.get("country", [])
    if country and country[0]["weight"] >= 0.80:
        warnings.append(f"{country[0]['label']} 자산 비중이 80% 이상입니다. 국가·정책·환율 위험이 한 방향으로 집중될 수 있습니다.")
    currency = allocations.get("currency", [])
    if currency and currency[0]["weight"] >= 0.80:
        warnings.append(f"{currency[0]['label']} 통화 노출이 80% 이상입니다. 환율 변화가 원화 평가액에 미치는 영향이 큽니다.")
    return list(dict.fromkeys(warnings))


def analyze_portfolio(assets: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [asset.copy() for asset in assets if _float(asset.get("value_krw")) > 0]
    total_value = sum(_float(asset.get("value_krw")) for asset in valid)
    total_cost = sum(_float(asset.get("cost_value_krw")) for asset in valid)
    if total_value <= 0:
        return {
            "success": False,
            "message": "분석 가능한 평가금액이 없습니다.",
            "assets": [],
            "summary": {},
            "allocations": {},
            "concentration": {},
            "warnings": [],
        }

    for asset in valid:
        asset["weight"] = _float(asset.get("value_krw")) / total_value
        asset["profit_loss_krw"] = _float(asset.get("value_krw")) - _float(asset.get("cost_value_krw"))
        cost = _float(asset.get("cost_value_krw"))
        asset["return_rate"] = asset["profit_loss_krw"] / cost if cost > 0 else None

    valid.sort(key=lambda item: _float(item.get("value_krw")), reverse=True)
    profit = total_value - total_cost
    cash_weight = sum(asset["weight"] for asset in valid if bool(asset.get("is_cash")))
    leveraged_weight = sum(asset["weight"] for asset in valid if bool(asset.get("is_leverage")))
    inverse_weight = sum(asset["weight"] for asset in valid if bool(asset.get("is_inverse")))
    gross_exposure = sum(asset["weight"] * abs(_float(asset.get("leverage_multiple"), 1.0)) for asset in valid if not bool(asset.get("is_cash")))
    net_exposure = sum(asset["weight"] * _float(asset.get("leverage_multiple"), 1.0) for asset in valid if not bool(asset.get("is_cash")))

    summary = {
        "total_value_krw": total_value,
        "total_cost_krw": total_cost,
        "profit_loss_krw": profit,
        "return_rate": profit / total_cost if total_cost > 0 else None,
        "cash_weight": cash_weight,
        "invested_weight": 1.0 - cash_weight,
        "leveraged_weight": leveraged_weight,
        "inverse_weight": inverse_weight,
        "gross_exposure": gross_exposure,
        "net_exposure": net_exposure,
        "asset_count": len(valid),
    }
    allocations = {
        "asset_class": _group_by_value(valid, "asset_class", ASSET_CLASS_LABELS),
        "country": _group_by_value(valid, "country", COUNTRY_LABELS),
        "currency": _group_by_value(valid, "currency"),
        "sector": _group_by_value(valid, "sector"),
        "account": _group_by_value(valid, "account_name"),
    }
    concentration = _concentration([asset["weight"] for asset in valid])
    score = build_portfolio_score(summary, concentration, allocations)
    stress_tests = build_stress_tests(valid, total_value)
    investment_dna = build_investment_dna(valid)
    return {
        "success": True,
        "message": "",
        "assets": valid,
        "summary": summary,
        "allocation": summary,  # 이전 UI 호환
        "allocations": allocations,
        "concentration": concentration,
        "score": score,
        "stress_tests": stress_tests,
        "investment_dna": investment_dna,
        "insights": build_insights(summary, concentration, allocations, score),
        "warnings": _warnings(summary, concentration, allocations),
    }

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from services.asset_resolver import enrich_asset_with_resolver


@dataclass(frozen=True)
class PortfolioAIMetrics:
    portfolio_score: float
    diversification_score: float
    risk_score: float
    cash_ratio: float
    us_ratio: float
    kr_ratio: float
    etf_ratio: float
    stock_ratio: float
    crypto_ratio: float
    real_estate_ratio: float


@dataclass(frozen=True)
class PortfolioAIDiagnosis:
    overall_score: float
    metrics: PortfolioAIMetrics
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]
    risks: tuple[str, ...]
    recommendations: tuple[str, ...]
    next_action: str
    risk_level: str
    diversification_score: float
    cash_ratio: float
    currency_exposure: dict[str, float]
    top_strengths: tuple[str, ...]
    top_risks: tuple[str, ...]
    recommended_actions: tuple[str, ...]

    @property
    def risk(self) -> tuple[str, ...]:
        """Backward-compatible singular alias for Feature Pack #1 clients."""
        return self.risks

    @property
    def combined_risks(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(self.weaknesses + self.risks))


class PortfolioAIProvider(ABC):
    """Provider boundary shared by the MVP rules and future OpenAI adapter."""

    @abstractmethod
    def generate(self, portfolio: dict[str, Any]) -> PortfolioAIDiagnosis:
        """Generate a structured advisory result from sanitized analysis data."""


def allocation_ratio(portfolio: dict[str, Any], dimension: str, code: str) -> float:
    """Return one normalized allocation ratio from structured analysis data."""
    expected = str(code).strip().upper()
    for row in portfolio.get("allocations", {}).get(dimension, []):
        row_code = str(row.get("code") or row.get("label") or "").strip().upper()
        if row_code == expected:
            return max(0.0, min(1.0, float(row.get("weight") or 0.0)))
    return 0.0


def calculate_scores(portfolio: dict[str, Any]) -> tuple[float, float, float]:
    """Calculate bounded portfolio, diversification and risk scores."""
    score = portfolio.get("score", {})
    categories = score.get("categories", {})
    portfolio_score = max(0.0, min(100.0, float(score.get("total") or 0.0)))
    diversification = max(
        0.0, min(100.0, float(categories.get("diversification") or 0.0))
    )
    leverage_control = max(
        0.0, min(100.0, float(categories.get("leverage_control") or 0.0))
    )
    cash_flexibility = max(
        0.0, min(100.0, float(categories.get("cash_flexibility") or 0.0))
    )
    risk_score = round(
        leverage_control * 0.60 + diversification * 0.25 + cash_flexibility * 0.15,
        1,
    )
    return round(portfolio_score, 1), round(diversification, 1), risk_score


def calculate_metrics(portfolio: dict[str, Any]) -> PortfolioAIMetrics:
    """Build all requested MVP metrics from a portfolio analysis result."""
    portfolio_score, diversification, risk_score = calculate_scores(portfolio)
    summary = portfolio.get("summary", {})
    cash_ratio = max(0.0, min(1.0, float(summary.get("cash_weight") or 0.0)))
    return PortfolioAIMetrics(
        portfolio_score=portfolio_score,
        diversification_score=diversification,
        risk_score=risk_score,
        cash_ratio=cash_ratio,
        us_ratio=allocation_ratio(portfolio, "country", "US"),
        kr_ratio=allocation_ratio(portfolio, "country", "KR"),
        etf_ratio=allocation_ratio(portfolio, "asset_class", "ETF"),
        stock_ratio=allocation_ratio(portfolio, "asset_class", "STOCK"),
        crypto_ratio=allocation_ratio(portfolio, "asset_class", "CRYPTO"),
        real_estate_ratio=allocation_ratio(portfolio, "asset_class", "REAL_ESTATE"),
    )


def build_rule_cards(
    portfolio: dict[str, Any],
    metrics: PortfolioAIMetrics,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    """Generate evidence-based strengths, risks and recommendations."""
    summary = portfolio.get("summary", {})
    concentration = portfolio.get("concentration", {})
    leverage_ratio = max(0.0, float(summary.get("leveraged_weight") or 0.0))
    top_one = max(0.0, float(concentration.get("top_1_weight") or 0.0))
    strengths: list[str] = []
    risks: list[str] = []
    recommendations: list[str] = []

    if metrics.diversification_score >= 70:
        strengths.append(f"분산 점수가 {metrics.diversification_score:.1f}점으로 양호합니다.")
    elif metrics.diversification_score < 50:
        risks.append(f"분산 점수가 {metrics.diversification_score:.1f}점으로 낮습니다.")
        recommendations.append("상관관계가 다른 자산군과 지역의 비중을 함께 검토하세요.")
    if metrics.etf_ratio >= 0.40:
        strengths.append(f"ETF 비중 {metrics.etf_ratio:.1%}로 장기 분산투자 구조에 적합합니다.")
    if 0.05 <= metrics.cash_ratio <= 0.15:
        strengths.append(f"현금 비중 {metrics.cash_ratio:.1%}로 유동성 균형 구간에 있습니다.")
    if leverage_ratio >= 0.20:
        risks.append(f"레버리지 자산 비중이 {leverage_ratio:.1%}로 높습니다.")
        recommendations.append("급락 시 손실 확대 가능성을 고려해 레버리지 비중 축소를 검토하세요.")
    if metrics.cash_ratio < 0.03:
        risks.append(f"현금 비중이 {metrics.cash_ratio:.1%}로 3% 미만입니다.")
        recommendations.append("비상 유동성과 리밸런싱 여력을 위한 현금 확보를 검토하세요.")
    if top_one >= 0.50:
        risks.append(f"최대 단일 자산 비중이 {top_one:.1%}입니다.")
        recommendations.append("단일 자산 의존도를 낮출 수 있는 단계적 리밸런싱을 검토하세요.")
    if metrics.crypto_ratio >= 0.20:
        risks.append(f"가상자산 비중이 {metrics.crypto_ratio:.1%}로 변동성 노출이 큽니다.")
        recommendations.append("가상자산 변동이 전체 자산에 미치는 허용 손실 범위를 점검하세요.")

    if not strengths:
        strengths.append("현재 데이터에서 명확한 구조적 강점 신호는 확인되지 않았습니다.")
    if not risks:
        risks.append("설정된 주요 위험 임계치를 초과한 항목이 없습니다.")
    if not recommendations:
        recommendations.append("현재 배분을 정기적으로 점검하고 목표 비중과의 차이를 관리하세요.")
    return tuple(strengths), tuple(risks), tuple(recommendations)


class RuleBasedPortfolioAIProvider(PortfolioAIProvider):
    """Deterministic provider with no network or external AI dependency."""

    def generate(self, portfolio: dict[str, Any]) -> PortfolioAIDiagnosis:
        if not portfolio.get("success"):
            raise ValueError("분석 가능한 포트폴리오 데이터가 없습니다.")
        metrics = calculate_metrics(portfolio)
        strengths, combined_risks, recommendations = build_rule_cards(portfolio, metrics)
        leverage_and_volatility = tuple(
            item for item in combined_risks if "레버리지" in item or "가상자산" in item
        )
        weaknesses = tuple(item for item in combined_risks if item not in leverage_and_volatility)
        if not weaknesses:
            weaknesses = ("현재 규칙에서 별도의 구조적 약점이 확인되지 않았습니다.",)
        if not leverage_and_volatility:
            leverage_and_volatility = ("현재 규칙에서 높은 변동성 위험 신호가 없습니다.",)
        combined = tuple(dict.fromkeys(weaknesses + leverage_and_volatility))
        risk_level = "낮음" if metrics.risk_score >= 75 else "보통" if metrics.risk_score >= 50 else "높음"
        currency_exposure = {
            str(row.get("code") or row.get("label") or "Unclassified"): max(
                0.0, min(1.0, float(row.get("weight") or 0.0))
            )
            for row in portfolio.get("allocations", {}).get("currency", [])
        }
        return PortfolioAIDiagnosis(
            overall_score=metrics.portfolio_score,
            metrics=metrics,
            strengths=strengths,
            weaknesses=weaknesses,
            risks=leverage_and_volatility,
            recommendations=recommendations,
            next_action=recommendations[0],
            risk_level=risk_level,
            diversification_score=metrics.diversification_score,
            cash_ratio=metrics.cash_ratio,
            currency_exposure=currency_exposure,
            top_strengths=strengths[:3],
            top_risks=combined[:3],
            recommended_actions=recommendations[:5],
        )


def diagnose_portfolio(
    portfolio: dict[str, Any],
    provider: PortfolioAIProvider | None = None,
) -> PortfolioAIDiagnosis:
    """Run the advisor through a replaceable provider contract."""
    normalized = dict(portfolio)
    normalized["assets"] = [
        enrich_asset_with_resolver(dict(asset))
        for asset in portfolio.get("assets", [])
    ]
    return (provider or RuleBasedPortfolioAIProvider()).generate(normalized)

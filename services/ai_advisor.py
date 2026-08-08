from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class PortfolioAdvice:
    """Provider-independent, structured portfolio advisory response."""

    diversification: str
    concentration: str
    currency_risk: str
    sector_risk: str
    account_advice: str
    investment_summary: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


class AIAdvisorProvider(ABC):
    """Stable provider contract for rules-based and future hosted AI advisors."""

    @abstractmethod
    def generate(self, portfolio: dict[str, Any]) -> PortfolioAdvice:
        """Generate advice exclusively from structured portfolio data."""


def _top_allocation(portfolio: dict[str, Any], dimension: str) -> tuple[str, float] | None:
    rows = portfolio.get("allocations", {}).get(dimension, [])
    if not rows:
        return None
    row = rows[0]
    return str(row.get("label") or row.get("code") or "미분류"), float(row.get("weight") or 0)


class StructuredRulesAdvisorProvider(AIAdvisorProvider):
    """Deterministic MVP provider that explains supplied portfolio metrics."""

    def generate(self, portfolio: dict[str, Any]) -> PortfolioAdvice:
        if not portfolio.get("success"):
            unavailable = "분석 가능한 평가금액이 없어 판단할 수 없습니다."
            return PortfolioAdvice(*(unavailable for _ in range(6)))

        summary = portfolio.get("summary", {})
        concentration_data = portfolio.get("concentration", {})
        asset_count = int(summary.get("asset_count") or 0)
        effective_count = float(concentration_data.get("effective_asset_count") or 0)
        top_one = float(concentration_data.get("top_1_weight") or 0)
        diversification = (
            f"보유자산 {asset_count}개, 유효 분산 자산 수 {effective_count:.1f}개입니다. "
            "명목 종목 수와 실제 비중 분산을 함께 점검하세요."
        )
        concentration = (
            f"최대 보유자산 비중은 {top_one:.1%}, "
            f"집중도 수준은 {concentration_data.get('level') or '정보 없음'}입니다."
        )

        currency = _top_allocation(portfolio, "currency")
        currency_risk = (
            f"가장 큰 통화 노출은 {currency[0]} {currency[1]:.1%}입니다. "
            "기준통화 대비 환율 변동 영향을 확인하세요."
            if currency else "통화 메타데이터가 부족해 환위험을 판단할 수 없습니다."
        )
        sector = _top_allocation(portfolio, "sector")
        sector_risk = (
            f"가장 큰 섹터 노출은 {sector[0]} {sector[1]:.1%}입니다. "
            "해당 섹터 변화가 전체 평가액에 미치는 영향을 점검하세요."
            if sector else "섹터 메타데이터가 부족해 섹터 위험을 판단할 수 없습니다."
        )
        account = _top_allocation(portfolio, "account")
        account_advice = (
            f"가장 큰 투자계정은 {account[0]} {account[1]:.1%}입니다. "
            "계정별 목적·유동성·세제 조건과 실제 자산 배치가 일치하는지 확인하세요."
            if account else "계정별 평가금액이 없어 계정 배치를 판단할 수 없습니다."
        )
        total = float(summary.get("total_value_krw") or 0)
        profit = float(summary.get("profit_loss_krw") or 0)
        investment_summary = (
            f"총 평가금액은 {total:,.0f}원, 평가손익은 {profit:+,.0f}원입니다. "
            "이 요약은 현재 구조를 설명하며 매수·매도 권고가 아닙니다."
        )
        return PortfolioAdvice(
            diversification, concentration, currency_risk, sector_risk,
            account_advice, investment_summary,
        )


class AIAdvisorService:
    """Application service whose callers remain unchanged when providers change."""

    def __init__(self, provider: AIAdvisorProvider | None = None) -> None:
        self.provider = provider or StructuredRulesAdvisorProvider()

    def advise(self, portfolio: dict[str, Any]) -> PortfolioAdvice:
        return self.provider.generate(portfolio)


def generate_portfolio_advice(
    portfolio: dict[str, Any],
    provider: AIAdvisorProvider | None = None,
) -> PortfolioAdvice:
    return AIAdvisorService(provider).advise(portfolio)

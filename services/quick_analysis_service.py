from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from repositories.asset_repository import AssetRepository
from services.excel_asset_service import import_asset_rows
from services.portfolio_ai_service import (
    PortfolioAIDiagnosis,
    PortfolioAIProvider,
    diagnose_portfolio,
)
from services.portfolio_service import analyze_asset_rows


@dataclass(frozen=True)
class QuickAnalysisResult:
    analysis: dict[str, Any]
    diagnosis: PortfolioAIDiagnosis


def run_quick_analysis(
    rows: list[dict[str, Any]],
    exchange_rates: dict[str, float],
    provider: PortfolioAIProvider | None = None,
) -> QuickAnalysisResult:
    """Analyze session-owned rows without touching persistent storage."""
    analysis = analyze_asset_rows(rows, exchange_rates)
    if not analysis.get("success"):
        raise ValueError(analysis.get("message") or "분석 가능한 평가금액이 없습니다.")
    return QuickAnalysisResult(analysis, diagnose_portfolio(analysis, provider))


def save_quick_analysis(
    rows: list[dict[str, Any]],
    *,
    account_id: int,
    warnings: list[str] | None = None,
    repository: AssetRepository | None = None,
) -> dict[str, Any]:
    """Persist only after the user explicitly selects and confirms save mode."""
    return import_asset_rows(
        rows,
        warnings,
        repository=repository,
        account_id=account_id,
    )

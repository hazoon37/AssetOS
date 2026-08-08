from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from repositories.asset_repository import AssetRepository
from services.quick_analysis_service import run_quick_analysis, save_quick_analysis


def _rows() -> list[dict[str, object]]:
    return [{
        "asset_name": "Apple", "asset_type": "미국주식", "asset_class": "STOCK",
        "symbol": "AAPL", "quantity": 2, "average_price": 100,
        "current_price": 120, "currency": "USD", "country": "US",
        "sector": "Technology", "is_cash": False, "is_leverage": False,
        "is_inverse": False, "leverage_multiple": 1,
    }]


def test_analyze_only_builds_analysis_without_repository() -> None:
    result = run_quick_analysis(_rows(), {"KRW": 1.0, "USD": 1_300.0})
    assert result.analysis["success"] is True
    assert result.analysis["summary"]["asset_count"] == 1
    assert result.diagnosis.overall_score >= 0


def test_save_mode_uses_existing_atomic_import_service() -> None:
    repository = Mock(spec=AssetRepository)
    repository.backup.return_value = Path("backup.db")
    result = save_quick_analysis(
        _rows(), account_id=7, warnings=["review"], repository=repository
    )
    assert result["success"] is True
    repository.backup.assert_called_once_with()
    repository.replace_all_assets.assert_called_once_with(_rows(), account_id=7)

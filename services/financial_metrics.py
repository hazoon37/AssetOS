from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

MetricStatus = Literal[
    "valid",
    "missing",
    "not_meaningful",
    "invalid",
]


@dataclass(frozen=True)
class MetricResult:
    """하나의 재무지표 계산 결과입니다."""

    value: float | None
    status: MetricStatus
    formula: str
    warning: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _result(
    value: float | None,
    status: MetricStatus,
    formula: str,
    warning: str | None = None,
) -> dict[str, object]:
    return MetricResult(
        value=value,
        status=status,
        formula=formula,
        warning=warning,
    ).to_dict()


def calculate_per(
    market_cap: float | None,
    net_income: float | None,
) -> dict[str, object]:
    formula = "시가총액 ÷ 당기순이익"

    if market_cap is None or net_income is None:
        return _result(
            None,
            "missing",
            formula,
            "시가총액 또는 당기순이익이 없습니다.",
        )

    if market_cap < 0:
        return _result(
            None,
            "invalid",
            formula,
            "시가총액은 음수가 될 수 없습니다.",
        )

    if net_income <= 0:
        return _result(
            None,
            "not_meaningful",
            formula,
            "당기순이익이 0 이하이므로 PER은 의미가 없습니다.",
        )

    return _result(
        market_cap / net_income,
        "valid",
        formula,
    )


def calculate_pbr(
    market_cap: float | None,
    equity: float | None,
) -> dict[str, object]:
    formula = "시가총액 ÷ 자본총계"

    if market_cap is None or equity is None:
        return _result(
            None,
            "missing",
            formula,
            "시가총액 또는 자본총계가 없습니다.",
        )

    if market_cap < 0:
        return _result(
            None,
            "invalid",
            formula,
            "시가총액은 음수가 될 수 없습니다.",
        )

    if equity <= 0:
        return _result(
            None,
            "not_meaningful",
            formula,
            "자본총계가 0 이하이므로 PBR 해석이 어렵습니다.",
        )

    return _result(
        market_cap / equity,
        "valid",
        formula,
    )


def calculate_psr(
    market_cap: float | None,
    revenue: float | None,
) -> dict[str, object]:
    formula = "시가총액 ÷ 매출액"

    if market_cap is None or revenue is None:
        return _result(
            None,
            "missing",
            formula,
            "시가총액 또는 매출액이 없습니다.",
        )

    if market_cap < 0:
        return _result(
            None,
            "invalid",
            formula,
            "시가총액은 음수가 될 수 없습니다.",
        )

    if revenue <= 0:
        return _result(
            None,
            "not_meaningful",
            formula,
            "매출액이 0 이하이므로 PSR을 계산할 수 없습니다.",
        )

    return _result(
        market_cap / revenue,
        "valid",
        formula,
    )


def calculate_roe(
    net_income: float | None,
    current_equity: float | None,
    previous_equity: float | None = None,
) -> dict[str, object]:
    formula = "당기순이익 ÷ 평균 자기자본"

    if net_income is None or current_equity is None:
        return _result(
            None,
            "missing",
            formula,
            "당기순이익 또는 자기자본이 없습니다.",
        )

    if previous_equity is None:
        average_equity = current_equity
        warning = "전기 자본이 없어 당기말 자본을 사용했습니다."
    else:
        average_equity = (
            current_equity + previous_equity
        ) / 2
        warning = None

    if average_equity <= 0:
        return _result(
            None,
            "not_meaningful",
            formula,
            "평균 자기자본이 0 이하이므로 ROE 해석이 어렵습니다.",
        )

    return _result(
        net_income / average_equity,
        "valid",
        formula,
        warning,
    )


def calculate_roa(
    net_income: float | None,
    total_assets: float | None,
) -> dict[str, object]:
    formula = "당기순이익 ÷ 자산총계"

    if net_income is None or total_assets is None:
        return _result(
            None,
            "missing",
            formula,
            "당기순이익 또는 자산총계가 없습니다.",
        )

    if total_assets <= 0:
        return _result(
            None,
            "invalid",
            formula,
            "자산총계는 0보다 커야 합니다.",
        )

    return _result(
        net_income / total_assets,
        "valid",
        formula,
    )


def calculate_debt_ratio(
    liabilities: float | None,
    equity: float | None,
) -> dict[str, object]:
    formula = "부채총계 ÷ 자본총계"

    if liabilities is None or equity is None:
        return _result(
            None,
            "missing",
            formula,
            "부채총계 또는 자본총계가 없습니다.",
        )

    if liabilities < 0:
        return _result(
            None,
            "invalid",
            formula,
            "부채총계는 음수가 될 수 없습니다.",
        )

    if equity <= 0:
        return _result(
            None,
            "not_meaningful",
            formula,
            "자본총계가 0 이하이므로 부채비율 해석이 어렵습니다.",
        )

    return _result(
        liabilities / equity,
        "valid",
        formula,
    )


def calculate_margin(
    profit: float | None,
    revenue: float | None,
    profit_name: str,
) -> dict[str, object]:
    formula = f"{profit_name} ÷ 매출액"

    if profit is None or revenue is None:
        return _result(
            None,
            "missing",
            formula,
            f"{profit_name} 또는 매출액이 없습니다.",
        )

    if revenue <= 0:
        return _result(
            None,
            "not_meaningful",
            formula,
            "매출액이 0 이하이므로 이익률을 계산할 수 없습니다.",
        )

    return _result(
        profit / revenue,
        "valid",
        formula,
    )


def calculate_growth(
    current_value: float | None,
    previous_value: float | None,
    item_name: str,
) -> dict[str, object]:
    formula = f"({item_name} 당기 - 전기) ÷ |전기|"

    if current_value is None or previous_value is None:
        return _result(
            None,
            "missing",
            formula,
            f"{item_name}의 당기 또는 전기 값이 없습니다.",
        )

    if previous_value == 0:
        return _result(
            None,
            "not_meaningful",
            formula,
            f"{item_name}의 전기 값이 0이라 성장률을 계산할 수 없습니다.",
        )

    return _result(
        (current_value - previous_value)
        / abs(previous_value),
        "valid",
        formula,
    )
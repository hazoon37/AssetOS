from __future__ import annotations

from typing import Any

import streamlit as st

from ui.common.formatters import (
    format_decimal_percentage,
    format_multiple,
)


STATUS_LABELS = {
    "valid": "정상",
    "missing": "자료 없음",
    "not_meaningful": "해석 불가",
    "invalid": "잘못된 자료",
}


def get_metric_value(
    metric_result: dict[str, Any] | None,
) -> float | None:
    """지표 결과에서 숫자 값을 안전하게 꺼냅니다."""

    if not isinstance(
        metric_result,
        dict,
    ):
        return None

    value = metric_result.get(
        "value"
    )

    if value is None:
        return None

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None


def build_metric_help(
    metric_result: dict[str, Any] | None,
) -> str | None:
    """지표의 계산식·상태·주의사항을 도움말로 만듭니다."""

    if not isinstance(
        metric_result,
        dict,
    ):
        return None

    parts: list[str] = []

    formula = metric_result.get(
        "formula"
    )

    if formula:
        parts.append(
            f"계산식: {formula}"
        )

    status = metric_result.get(
        "status"
    )

    if status:

        status_label = STATUS_LABELS.get(
            str(status),
            str(status),
        )

        parts.append(
            f"상태: {status_label}"
        )

    warning = metric_result.get(
        "warning"
    )

    if warning:
        parts.append(
            f"주의: {warning}"
        )

    if not parts:
        return None

    return "\n\n".join(parts)


def render_multiple_metric(
    label: str,
    metric_result: dict[str, Any] | None,
) -> None:
    """PER·PBR·PSR 등 배수형 지표를 표시합니다."""

    value = get_metric_value(
        metric_result
    )

    st.metric(
        label=label,
        value=format_multiple(
            value
        ),
        help=build_metric_help(
            metric_result
        ),
    )


def render_percentage_metric(
    label: str,
    metric_result: dict[str, Any] | None,
) -> None:
    """ROE·ROA·이익률 등 비율형 지표를 표시합니다."""

    value = get_metric_value(
        metric_result
    )

    st.metric(
        label=label,
        value=format_decimal_percentage(
            value
        ),
        help=build_metric_help(
            metric_result
        ),
    )


def render_valuation_metrics(
    metric_details: dict[str, Any],
) -> None:
    """PER·PBR·PSR 가치평가 영역을 표시합니다."""

    st.subheader(
        "AssetOS 직접 계산 가치평가"
    )

    col1, col2, col3 = (
        st.columns(3)
    )

    with col1:

        render_multiple_metric(
            "PER",
            metric_details.get(
                "per"
            ),
        )

    with col2:

        render_multiple_metric(
            "PBR",
            metric_details.get(
                "pbr"
            ),
        )

    with col3:

        render_multiple_metric(
            "PSR",
            metric_details.get(
                "psr"
            ),
        )


def render_profitability_metrics(
    metric_details: dict[str, Any],
) -> None:
    """수익성과 재무안정성 지표를 표시합니다."""

    st.subheader(
        "수익성·재무안정성"
    )

    col1, col2, col3 = (
        st.columns(3)
    )

    with col1:

        render_percentage_metric(
            "ROE",
            metric_details.get(
                "roe"
            ),
        )

    with col2:

        render_percentage_metric(
            "ROA",
            metric_details.get(
                "roa"
            ),
        )

    with col3:

        render_percentage_metric(
            "부채비율",
            metric_details.get(
                "debt_ratio"
            ),
        )

    col4, col5 = (
        st.columns(2)
    )

    with col4:

        render_percentage_metric(
            "영업이익률",
            metric_details.get(
                "operating_margin"
            ),
        )

    with col5:

        render_percentage_metric(
            "순이익률",
            metric_details.get(
                "net_margin"
            ),
        )


def render_growth_metrics(
    metric_details: dict[str, Any],
) -> None:
    """전기 대비 성장률 지표를 표시합니다."""

    st.subheader(
        "전기 대비 성장성"
    )

    col1, col2, col3 = (
        st.columns(3)
    )

    with col1:

        render_percentage_metric(
            "매출 성장률",
            metric_details.get(
                "revenue_growth"
            ),
        )

    with col2:

        render_percentage_metric(
            "영업이익 성장률",
            metric_details.get(
                "operating_income_growth"
            ),
        )

    with col3:

        render_percentage_metric(
            "순이익 성장률",
            metric_details.get(
                "net_income_growth"
            ),
        )


def render_metric_status_table(
    metric_details: dict[str, Any],
) -> None:
    """각 지표의 계산식·상태·주의사항을 표시합니다."""

    metric_labels = {
        "per": "PER",
        "pbr": "PBR",
        "psr": "PSR",
        "roe": "ROE",
        "roa": "ROA",
        "debt_ratio": "부채비율",
        "operating_margin": "영업이익률",
        "net_margin": "순이익률",
        "revenue_growth": "매출 성장률",
        "operating_income_growth": (
            "영업이익 성장률"
        ),
        "net_income_growth": (
            "순이익 성장률"
        ),
    }

    with st.expander(
        "지표 계산 기준과 상태 보기",
        expanded=False,
    ):

        for (
            key,
            label,
        ) in metric_labels.items():

            result = metric_details.get(
                key,
                {},
            )

            status = result.get(
                "status",
                "missing",
            )

            status_label = (
                STATUS_LABELS.get(
                    str(status),
                    str(status),
                )
            )

            formula = result.get(
                "formula",
                "계산식 정보 없음",
            )

            warning = result.get(
                "warning"
            )

            st.markdown(
                f"**{label} · "
                f"{status_label}**"
            )

            st.caption(
                formula
            )

            if warning:
                st.warning(
                    warning
                )

            st.divider()
from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from ui.common.formatters import (
    format_decimal_percentage,
    format_krw,
    format_large_currency,
    format_multiple,
    format_percent,
)


def _format_signed_krw(value: float | None) -> str:
    if value is None:
        return "정보 없음"
    return format_krw(value)


def _allocation_df(rows: list[dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "구분": row.get("label") or row.get("code") or "미분류",
                "평가금액": float(row.get("value_krw") or 0),
                "비중(%)": float(row.get("weight") or 0) * 100,
            }
            for row in rows
        ]
    )


def render_portfolio_summary(result: dict[str, Any]) -> None:
    summary = result.get("summary", {})
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("총 평가금액", format_large_currency(summary.get("total_value_krw"), "KRW"))
    col2.metric(
        "총 평가손익",
        _format_signed_krw(summary.get("profit_loss_krw")),
        delta=format_decimal_percentage(summary.get("return_rate")),
    )
    col3.metric("현금성 자산", format_decimal_percentage(summary.get("cash_weight")))
    col4.metric("레버리지 자산", format_decimal_percentage(summary.get("leveraged_weight")))

    col5, col6, col7, col8 = st.columns(4)
    col5.metric("투자원금", format_large_currency(summary.get("total_cost_krw"), "KRW"))
    col6.metric(
        "단순 총 노출",
        format_decimal_percentage(summary.get("gross_exposure")),
        help="일반 자산은 1배, 레버리지·인버스 상품은 목표 일일 배수를 적용한 단순 명목 노출입니다.",
    )
    col7.metric(
        "단순 순 노출",
        format_decimal_percentage(summary.get("net_exposure")),
        help="인버스 상품은 음(-)의 배수로 반영한 방향성 참고값입니다.",
    )
    col8.metric("분석 자산 수", f"{int(summary.get('asset_count') or 0):,}개")


def render_allocation_section(title: str, rows: list[dict[str, Any]], caption: str | None = None) -> None:
    st.subheader(title)
    if not rows:
        st.info("표시할 분석 데이터가 없습니다.")
        return
    df = _allocation_df(rows)
    left, right = st.columns([1, 1.7])
    with left:
        display = df.copy()
        display["평가금액"] = display["평가금액"].map(format_krw)
        display["비중(%)"] = display["비중(%)"].map(format_percent)
        st.dataframe(display, width="stretch", hide_index=True)
    with right:
        chart = df.set_index("구분")[["비중(%)"]]
        st.bar_chart(chart, width="stretch")
    if caption:
        st.caption(caption)


def build_asset_dataframe(assets: list[dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for index, asset in enumerate(assets, start=1):
        leverage = float(asset.get("leverage_multiple") or 1.0)
        rows.append(
            {
                "번호": index,
                "자산명": asset.get("name") or "-",
                "티커": asset.get("symbol") or "-",
                "자산군": asset.get("asset_class") or "-",
                "국가": asset.get("country") or "-",
                "통화": asset.get("currency") or "-",
                "섹터": asset.get("sector") or "-",
                "평가금액": float(asset.get("value_krw") or 0),
                "평가손익": float(asset.get("profit_loss_krw") or 0),
                "수익률": asset.get("return_rate"),
                "비중": float(asset.get("weight") or 0),
                "레버리지": format_multiple(leverage) if asset.get("is_leverage") else "일반",
            }
        )
    return pd.DataFrame(rows)


def render_asset_allocation(assets: list[dict[str, Any]]) -> None:
    st.subheader("보유자산 구성")
    if not assets:
        st.info("표시할 자산이 없습니다.")
        return
    df = build_asset_dataframe(assets)
    display = df.copy()
    display["평가금액"] = display["평가금액"].map(format_krw)
    display["평가손익"] = display["평가손익"].map(format_krw)
    display["수익률"] = display["수익률"].map(
        lambda v: format_decimal_percentage(v) if v is not None else "계산 불가"
    )
    display["비중"] = display["비중"].map(format_decimal_percentage)
    st.dataframe(display, width="stretch", hide_index=True)


def render_concentration(concentration: dict[str, Any]) -> None:
    st.subheader("집중도 진단")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("최대 자산", format_decimal_percentage(concentration.get("top_1_weight")))
    col2.metric("상위 3개", format_decimal_percentage(concentration.get("top_3_weight")))
    col3.metric("상위 5개", format_decimal_percentage(concentration.get("top_5_weight")))
    col4.metric("HHI", f"{float(concentration.get('hhi') or 0):,.4f}")
    col5.metric("집중도", concentration.get("level") or "정보 없음")
    st.caption(
        "유효 자산 수: "
        f"{float(concentration.get('effective_asset_count') or 0):,.2f}개 · "
        "HHI는 각 자산 비중의 제곱합이며 높을수록 특정 자산에 집중되어 있습니다."
    )


def render_portfolio_warnings(warnings: list[str]) -> None:
    st.subheader("위험 및 점검사항")
    if not warnings:
        st.success("현재 기본 분석 기준에서 특별한 경고가 없습니다.")
        return
    for warning in warnings:
        st.warning(warning)


def render_data_status(result: dict[str, Any]) -> None:
    with st.expander("데이터 상태 및 원본 결과", expanded=False):
        col1, col2, col3 = st.columns(3)
        col1.metric("DB 등록 자산", f"{int(result.get('source_asset_count') or 0):,}개")
        col2.metric("분석 반영 자산", f"{int(result.get('analyzed_asset_count') or 0):,}개")
        col3.metric("환율 조회", "정상" if result.get("exchange_rate_success") else "확인 필요")
        st.write("환율 기준일:", result.get("exchange_rate_date") or "정보 없음")
        st.json(result)


def render_portfolio_analysis(result: dict[str, Any]) -> None:
    if not result.get("success"):
        st.error(result.get("message") or "포트폴리오 분석에 실패했습니다.")
        render_data_status(result)
        return

    render_portfolio_summary(result)
    st.divider()
    render_portfolio_score(result.get("score", {}))
    render_insights(result.get("insights", []))
    st.divider()

    allocations = result.get("allocations", {})
    tabs = st.tabs(["자산군", "국가", "통화", "섹터"])
    with tabs[0]:
        render_allocation_section("자산군별 배분", allocations.get("asset_class", []))
    with tabs[1]:
        render_allocation_section("국가별 노출", allocations.get("country", []), "ETF는 상장시장 기준의 1차 분류이며 내부 보유종목 기준 분석은 후속 단계입니다.")
    with tabs[2]:
        render_allocation_section("통화별 노출", allocations.get("currency", []), "외화자산은 현재 환율로 원화 환산해 계산합니다.")
    with tabs[3]:
        render_allocation_section("섹터별 노출", allocations.get("sector", []), "미분류 자산은 자동조회 또는 자산 수정 후 정교화할 수 있습니다.")

    st.divider()
    render_concentration(result.get("concentration", {}))
    st.divider()
    render_stress_tests(result.get("stress_tests", []))
    st.divider()
    render_investment_dna(result.get("investment_dna", []))
    st.divider()
    render_asset_allocation(result.get("assets", []))
    st.divider()
    render_portfolio_warnings(result.get("warnings", []))
    render_data_status(result)


def render_portfolio_score(score: dict[str, Any]) -> None:
    st.subheader("AssetOS 포트폴리오 진단")
    left, right = st.columns([1, 3])
    with left:
        st.metric(
            "Portfolio Score",
            f"{float(score.get('total') or 0):.1f}점",
            delta=f"{score.get('grade') or '-'}등급 · {score.get('label') or '-'}",
            help=str(score.get("method") or ""),
        )
    labels = {
        "diversification": "분산",
        "cash_flexibility": "현금 유연성",
        "leverage_control": "레버리지 관리",
        "country_balance": "국가 분산",
        "currency_balance": "통화 분산",
    }
    rows = [
        {"항목": labels.get(key, key), "점수": float(value)}
        for key, value in (score.get("categories") or {}).items()
    ]
    with right:
        if rows:
            score_df = pd.DataFrame(rows).set_index("항목")
            st.bar_chart(score_df, width="stretch", horizontal=True)
    st.caption("이 점수는 수익률 예측이 아니라 현재 포트폴리오 구조의 분산·유동성·레버리지 위험을 규칙 기반으로 진단한 값입니다.")


def render_insights(insights: list[str]) -> None:
    st.subheader("핵심 해석")
    if not insights:
        st.info("표시할 해석이 없습니다.")
        return
    for insight in insights:
        st.write(f"• {insight}")


def render_stress_tests(rows: list[dict[str, Any]]) -> None:
    st.subheader("간이 스트레스 테스트")
    if not rows:
        st.info("표시할 시나리오가 없습니다.")
        return
    display_rows = []
    for row in rows:
        display_rows.append({
            "시나리오": row.get("label"),
            "예상 충격": format_decimal_percentage(row.get("impact_rate")),
            "예상 손익": _format_signed_krw(row.get("impact_krw")),
            "충격 후 자산": format_large_currency(row.get("after_value_krw"), "KRW"),
            "가정": row.get("description"),
        })
    st.dataframe(pd.DataFrame(display_rows), width="stretch", hide_index=True)
    st.caption("실제 예측값이 아닌 구조적 취약점 확인용 단순 시나리오입니다. 상관관계, 장중 재조정, 세금·수수료는 반영하지 않습니다.")


def render_investment_dna(rows: list[dict[str, Any]]) -> None:
    st.subheader("Investment DNA")
    if not rows:
        st.info("분류 태그가 부족해 투자 성향을 계산할 수 없습니다.")
        return
    dna_df = pd.DataFrame([
        {
            "테마": row.get("theme"),
            "노출 비중(%)": float(row.get("weight") or 0) * 100,
            "평가금액": float(row.get("value_krw") or 0),
        }
        for row in rows
    ])
    left, right = st.columns([1, 1.7])
    with left:
        display = dna_df.copy()
        display["노출 비중(%)"] = display["노출 비중(%)"].map(format_percent)
        display["평가금액"] = display["평가금액"].map(format_krw)
        st.dataframe(display, width="stretch", hide_index=True)
    with right:
        st.bar_chart(dna_df.set_index("테마")[["노출 비중(%)"]], width="stretch")
    st.caption("한 자산이 여러 테마에 동시에 포함될 수 있어 노출 비중 합계는 100%를 초과할 수 있습니다.")

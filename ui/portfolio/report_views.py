from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from services.portfolio_pdf_service import (
    build_portfolio_pdf,
    build_portfolio_pdf_filename,
)
from services.portfolio_service import get_portfolio_analysis
from ui.common.formatters import (
    format_decimal_percentage,
    format_large_currency,
)


def _first_label(rows: list[dict[str, Any]]) -> tuple[str, float]:
    if not rows:
        return "정보 없음", 0.0
    first = rows[0]
    return str(first.get("label") or first.get("code") or "정보 없음"), float(first.get("weight") or 0.0)


def _render_pdf_preview(result: dict[str, Any]) -> None:
    """Render a compact portrait-style preview using the same report result."""

    summary = result.get("summary", {})
    allocations = result.get("allocations", {})
    assets = result.get("assets", [])
    insights = [str(item) for item in result.get("insights", [])]
    warnings = [str(item) for item in result.get("warnings", [])]
    score = result.get("score", {})
    concentration = result.get("concentration", {})

    mode = "부동산 제외" if result.get("exclude_real_estate") else "전체 자산"

    st.markdown(
        f"""
        <div style="max-width:760px;margin:0 auto 12px auto;padding:18px 20px;background:#fff;
                    border:1px solid #dce4ef;border-radius:14px;box-shadow:0 8px 24px rgba(15,23,42,.04);">
          <div style="color:#2563eb;font-size:12px;font-weight:800;letter-spacing:.08em;">ASSETOS · PORTFOLIO REPORT</div>
          <div style="display:flex;justify-content:space-between;align-items:end;gap:12px;">
            <div style="font-size:25px;font-weight:800;color:#0f172a;">포트폴리오 한눈 요약</div>
            <div style="font-size:12px;color:#64748b;">분석 기준: <b>{mode}</b></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("총 평가금액", format_large_currency(summary.get("total_value_krw"), "KRW"))
    k2.metric("총 평가손익", format_large_currency(summary.get("profit_loss_krw"), "KRW"), format_decimal_percentage(summary.get("return_rate")))
    k3.metric("현금성 비중", format_decimal_percentage(summary.get("cash_weight")))
    k4.metric("진단 점수", f"{float(score.get('total') or 0):.1f}점", f"{score.get('grade') or '-'}등급")

    chart_col, holdings_col = st.columns([1, 1])
    with chart_col:
        rows = allocations.get("asset_class", [])
        if rows:
            chart_df = pd.DataFrame(
                {
                    "자산군": [str(row.get("label") or row.get("code") or "미분류") for row in rows[:6]],
                    "비중": [float(row.get("weight") or 0) * 100 for row in rows[:6]],
                }
            )
            fig = px.pie(chart_df, names="자산군", values="비중", hole=0.58)
            fig.update_layout(
                height=300,
                margin=dict(l=10, r=10, t=35, b=10),
                title="자산군 구성",
                legend_title_text="",
            )
            fig.update_traces(textposition="inside", textinfo="percent")
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("자산군 데이터가 없습니다.")

    with holdings_col:
        st.markdown("#### 상위 보유자산")
        top_rows = []
        for index, asset in enumerate(assets[:5], start=1):
            top_rows.append(
                {
                    "순위": index,
                    "자산": str(asset.get("name") or asset.get("symbol") or "-"),
                    "비중": f"{float(asset.get('weight') or 0) * 100:.1f}%",
                    "평가금액": format_large_currency(asset.get("value_krw"), "KRW"),
                }
            )
        if top_rows:
            st.dataframe(pd.DataFrame(top_rows), width="stretch", hide_index=True, height=300)
        else:
            st.info("표시할 보유자산이 없습니다.")

    text_col, risk_col = st.columns([1.2, 1])
    with text_col:
        st.markdown("#### 핵심 요점")
        if insights:
            for item in insights[:5]:
                st.write(f"• {item}")
        else:
            st.info("표시할 핵심 요점이 없습니다.")

    with risk_col:
        st.markdown("#### 주요 점검사항")
        if warnings:
            for item in warnings[:4]:
                st.warning(item)
        else:
            st.success("현재 기본 진단 규칙에서 특별한 경고가 없습니다.")

        st.caption(
            f"최대 자산 {float(concentration.get('top_1_weight') or 0) * 100:.1f}% · "
            f"상위 3개 {float(concentration.get('top_3_weight') or 0) * 100:.1f}% · "
            f"HHI {float(concentration.get('hhi') or 0):.3f}"
        )


def render_portfolio_report(result: dict[str, Any]) -> None:
    """현재 구조화 데이터로 포트폴리오 요약 보고서를 표시합니다."""

    if not result.get("success"):
        st.error(result.get("message") or "보고서를 생성할 수 없습니다.")
        return

    # PDF와 미리보기는 포트폴리오 상단의 현재 선택 기준을 다시 읽어 동일한 결과를 사용합니다.
    current_mode = st.session_state.get("portfolio_view_mode", "부동산 제외")
    exclude_real_estate = current_mode == "부동산 제외"
    report_result = get_portfolio_analysis(exclude_real_estate=exclude_real_estate)

    if not report_result.get("success"):
        st.error(report_result.get("message") or "보고서를 생성할 수 없습니다.")
        return

    mode_label = "부동산 제외" if exclude_real_estate else "전체 자산"

    st.subheader("1페이지 포트폴리오 PDF")
    st.caption(
        "현재 포트폴리오 표시 기준과 동일한 데이터로 세로형 A4 한 페이지 보고서를 생성합니다. "
        "아래 미리보기를 확인한 뒤 다운로드하세요."
    )
    st.info(f"현재 PDF 분석 기준: **{mode_label}**")

    with st.expander("🔎 PDF 미리보기", expanded=True):
        _render_pdf_preview(report_result)

    try:
        pdf_bytes = build_portfolio_pdf(report_result)
        st.download_button(
            "📄 세로형 1페이지 PDF 다운로드",
            data=pdf_bytes,
            file_name=build_portfolio_pdf_filename(report_result),
            mime="application/pdf",
            type="primary",
            width="content",
        )
    except Exception as error:
        st.error(f"PDF 생성 중 오류가 발생했습니다: {error}")

    st.divider()

    summary = report_result.get("summary", {})
    allocations = report_result.get("allocations", {})
    concentration = report_result.get("concentration", {})
    score = report_result.get("score", {})
    warnings = report_result.get("warnings", [])
    insights = report_result.get("insights", [])

    country_name, country_weight = _first_label(allocations.get("country", []))
    currency_name, currency_weight = _first_label(allocations.get("currency", []))
    asset_class_name, asset_class_weight = _first_label(allocations.get("asset_class", []))

    st.subheader("포트폴리오 개요")
    st.write(
        f"현재 총 평가금액은 **{format_large_currency(summary.get('total_value_krw'), 'KRW')}**이며, "
        f"총수익률은 **{format_decimal_percentage(summary.get('return_rate'))}**입니다. "
        f"가장 큰 자산군은 **{asset_class_name} {asset_class_weight * 100:.1f}%**, "
        f"가장 큰 국가 노출은 **{country_name} {country_weight * 100:.1f}%**, "
        f"가장 큰 통화 노출은 **{currency_name} {currency_weight * 100:.1f}%**입니다."
    )

    st.subheader("구조 진단")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Portfolio Score", f"{float(score.get('total') or 0):.1f}점")
    col2.metric("등급", f"{score.get('grade') or '-'} · {score.get('label') or '-'}")
    col3.metric("최대 자산 비중", format_decimal_percentage(concentration.get("top_1_weight")))
    col4.metric("레버리지 비중", format_decimal_percentage(summary.get("leveraged_weight")))

    st.subheader("핵심 해석")
    if insights:
        for insight in insights:
            st.write(f"• {insight}")
    else:
        st.info("표시할 핵심 해석이 없습니다.")

    st.subheader("주요 위험")
    if warnings:
        for warning in warnings:
            st.warning(warning)
    else:
        st.success("현재 기본 진단 규칙에서 특별한 경고가 없습니다.")

    st.subheader("운용 점검 원칙")
    st.markdown(
        """
        - 자산 가격보다 **보유 비중과 투자 논리의 변화**를 우선 점검합니다.
        - 레버리지 자산은 단순 보유기간보다 **추세와 변동성 환경**을 함께 확인합니다.
        - 현금성 자산은 수익률이 아니라 **급락 대응과 선택권 확보** 관점에서 관리합니다.
        - 집중도가 높을수록 상위 자산의 투자 가설이 훼손되는지 정기적으로 재검토합니다.
        """
    )

    st.caption(
        "현재 보고서는 DB 보유자산과 규칙 기반 구조 분석으로 생성됩니다. "
        "향후 ETF 내부 보유종목, 시장 시계열, AI 해석을 추가할 수 있습니다."
    )

from __future__ import annotations

import streamlit as st

from components.asset_management.add_asset_tab import render_add_asset_tab
from components.asset_management.excel_import_panel import render_excel_import_panel
from components.asset_management.helpers import prepare_assets_dataframe
from database.db import create_tables, get_assets
from services.exchange_rate_service import get_exchange_rates_to_krw
from services.portfolio_service import (
    clear_portfolio_analysis_cache,
    get_portfolio_analysis,
)
from ui.asset_table import render_asset_management_view
from ui.layout import render_exchange_panel
from ui.portfolio.portfolio_views import (
    render_allocation_section,
    render_asset_allocation,
    render_concentration,
    render_data_status,
    render_insights,
    render_investment_dna,
    render_portfolio_score,
    render_portfolio_summary,
    render_portfolio_warnings,
    render_stress_tests,
)
from ui.portfolio.report_views import render_portfolio_report
from ui.theme import apply_theme


st.set_page_config(
    page_title="AssetOS 포트폴리오",
    page_icon="💼",
    layout="wide",
)

apply_theme()
create_tables()

st.title("💼 포트폴리오")
st.write(
    "보유자산 등록·수정·삭제와 구성·위험 분석을 한 화면에서 관리합니다. "
    "자산 정보가 변경되면 포트폴리오 분석도 함께 갱신됩니다."
)

exchange_data = get_exchange_rates_to_krw()
exchange_rates: dict[str, float] = exchange_data.get("rates") or {"KRW": 1.0}
assets_df = prepare_assets_dataframe(get_assets())

refresh_col, status_col = st.columns([1, 4])
with refresh_col:
    if st.button("전체 데이터 새로고침", type="primary", use_container_width=True):
        clear_portfolio_analysis_cache()
        st.rerun()
with status_col:
    st.caption(
        f"환율 기준일: {exchange_data.get('date') or '정보 없음'} · "
        f"등록 자산: {len(assets_df):,}개"
    )

view_mode = st.radio(
    "포트폴리오 표시 기준",
    ["전체 자산", "부동산 제외"],
    horizontal=True,
    key="portfolio_view_mode",
    help="부동산 제외를 선택하면 구성·위험·보고서 계산에서 부동산만 제외합니다. 보유자산 목록과 DB는 변경되지 않습니다.",
)
exclude_real_estate = view_mode == "부동산 제외"

result = get_portfolio_analysis(exclude_real_estate=exclude_real_estate)

if exclude_real_estate:
    st.info("현재 분석은 부동산을 제외한 유동·금융자산 기준입니다. 실제 DB와 전체 자산은 변경되지 않습니다.")

st.divider()
if result.get("success"):
    render_portfolio_summary(result)
else:
    st.info("분석 가능한 보유자산이 없습니다. 보유자산 탭에서 자산을 먼저 등록하세요.")

st.divider()
holdings_tab, allocation_tab, risk_tab, report_tab = st.tabs(
    ["보유자산", "구성 분석", "위험 분석", "보고서"]
)

with holdings_tab:
    st.subheader("보유자산 관리")
    st.caption("자산을 등록하거나 목록에서 바로 수정·삭제할 수 있습니다.")

    action_col1, action_col2 = st.columns(2)
    with action_col1:
        with st.expander("➕ 새 자산 등록", expanded=assets_df.empty):
            render_add_asset_tab(exchange_rates)
    with action_col2:
        with st.expander("📥 Excel 자산 DB 업데이트", expanded=False):
            render_excel_import_panel()

    st.divider()
    render_asset_management_view(
        assets_df=assets_df,
        exchange_rates=exchange_rates,
        exchange_rate_date=exchange_data.get("date") or "정보 없음",
        show_summary=False,
    )

    st.divider()
    render_exchange_panel(exchange_data)

with allocation_tab:
    if not result.get("success"):
        st.info("구성 분석을 위해 자산을 등록해 주세요.")
    else:
        allocations = result.get("allocations", {})
        sub_tabs = st.tabs(["자산군", "국가", "통화", "섹터", "자산별"])
        with sub_tabs[0]:
            render_allocation_section("자산군별 배분", allocations.get("asset_class", []))
        with sub_tabs[1]:
            render_allocation_section(
                "국가별 노출",
                allocations.get("country", []),
                "ETF는 현재 상장시장 기준의 1차 분류입니다.",
            )
        with sub_tabs[2]:
            render_allocation_section(
                "통화별 노출",
                allocations.get("currency", []),
                "외화자산은 현재 환율로 원화 환산해 계산합니다.",
            )
        with sub_tabs[3]:
            render_allocation_section(
                "섹터별 노출",
                allocations.get("sector", []),
                "미분류 자산은 자동조회 또는 수정 후 정교화할 수 있습니다.",
            )
        with sub_tabs[4]:
            render_asset_allocation(result.get("assets", []))

with risk_tab:
    if not result.get("success"):
        st.info("위험 분석을 위해 자산을 등록해 주세요.")
    else:
        render_portfolio_score(result.get("score", {}))
        render_insights(result.get("insights", []))
        st.divider()
        render_concentration(result.get("concentration", {}))
        st.divider()
        render_stress_tests(result.get("stress_tests", []))
        st.divider()
        render_investment_dna(result.get("investment_dna", []))
        st.divider()
        render_portfolio_warnings(result.get("warnings", []))
        render_data_status(result)

with report_tab:
    render_portfolio_report(result)

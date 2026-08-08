from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from components.asset_management.asset_manager_panel import render_asset_manager_panel
from database.db import (
    create_tables,
    get_accounts,
    get_assets,
    update_asset_current_price,
)
from services.exchange_rate_service import (
    get_exchange_rates_to_krw,
)
from services.market_price_service import (
    get_market_price,
)
from services.portfolio_ai_service import diagnose_portfolio
from services.portfolio_service import get_portfolio_analysis
from services.quick_analysis_export_service import (
    export_quick_analysis_json,
    export_quick_analysis_pdf,
    export_quick_analysis_png,
)
from ui.common.formatters import (
    CURRENCY_SYMBOLS,
    format_asset_type,
    format_currency,
    format_number,
    format_percent,
)
from ui.components.ai_advisor_card import (
    render_ai_advisor_diagnosis,
    render_ai_advisor_summary,
)
from ui.components.metric_card import (
    render_ai_card,
    render_metric_grid,
    render_page_header,
)
from ui.theme import ASSET_COLORS, apply_theme, theme_text_color

apply_theme()
create_tables()

st.markdown("""
<style>

[data-testid="stDataFrame"] table {
    font-size:13px !important;
}

[data-testid="stDataFrame"] th {
    font-size:13px !important;
}

</style>
""", unsafe_allow_html=True)

# ==================================================
# 공통 설정
# ==================================================

AUTO_UPDATE_ASSET_TYPES = [
    "국내주식",
    "미국주식",
    "국내ETF",
    "미국ETF",
    "코인",
]

# ==================================================
# 공통 함수
# ==================================================

def format_original_currency(
    value: float,
    currency: str,
) -> str:
    """원래 통화로 금액을 표시합니다."""

    return format_currency(value, currency)


def format_quantity(
    value: float,
    asset_type: str,
) -> str:
    """자산 종류에 따라 수량 자릿수를 표시합니다."""

    if asset_type == "코인":
        return format_number(value, decimal_places=8)

    if asset_type in [
        "미국주식",
        "미국ETF",
    ]:
        return format_number(value, decimal_places=4)

    return format_number(value)


def render_allocation_chart(
    assets: pd.DataFrame,
    dimension: str,
    label: str,
) -> None:
    """Render one consistent portfolio allocation view."""
    if dimension not in assets.columns:
        st.info(f"{label} 메타데이터가 없습니다.")
        return
    summary = pd.DataFrame(assets.assign(
        _allocation_label=(
            assets[dimension].fillna("").astype(str).replace("", "Unclassified")
        )
    ).groupby("_allocation_label", as_index=False)[["원화 평가금액"]].sum())
    if dimension == "asset_type":
        summary["_allocation_label"] = pd.Series(
            summary["_allocation_label"], index=summary.index
        ).map(
            format_asset_type
        )
    positive = pd.Series(summary["원화 평가금액"], index=summary.index) > 0
    summary = pd.DataFrame(summary.loc[positive]).sort_values(
        "원화 평가금액", ascending=False
    )
    if summary.empty:
        st.info(f"표시할 {label} 배분 데이터가 없습니다.")
        return
    chart = px.pie(
        summary,
        names="_allocation_label",
        values="원화 평가금액",
        hole=0.62,
        color="_allocation_label",
        color_discrete_map=ASSET_COLORS if dimension == "asset_type" else None,
    )
    chart.update_traces(
        textposition="inside",
        texttemplate="%{label}<br>%{percent}",
        hovertemplate=(
            f"%{{label}}<br>평가금액: "
            f"{CURRENCY_SYMBOLS.get(base_currency, base_currency + ' ')}"
            "%{value:,.0f}<br>"
            "비중: %{percent}<extra></extra>"
        ),
    )
    chart.update_layout(
        margin={"l": 10, "r": 10, "t": 18, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend_title_text="",
        font={"color": theme_text_color(), "size": 12},
    )
    st.plotly_chart(chart, width="stretch")
    table = pd.DataFrame(summary.loc[:, ["_allocation_label", "원화 평가금액"]]).rename(
        columns={"_allocation_label": label, "원화 평가금액": "평가금액"}
    )
    table["평가금액"] = pd.Series(table["평가금액"], index=table.index).map(
        lambda value: format_currency(value, base_currency)
    )
    st.dataframe(table, width="stretch", hide_index=True)


# ==================================================
# 페이지 제목
# ==================================================

@st.dialog("➕ 자산관리", width="large")
def open_asset_manager() -> None:
    render_asset_manager_panel()


header_column, advisor_column, action_column = st.columns(
    [4.2, 1.4, 1], vertical_alignment="center"
)
with header_column:
    render_page_header(
        title="총 자산 현황",
        subtitle=(
            "전체 자산을 원화 기준으로 요약하고, "
            "금융자산 구성과 손익을 한눈에 확인합니다."
        ),
    )
with advisor_column:
    if st.button("🤖 AI 포트폴리오 진단", width="stretch"):
        st.session_state["show_portfolio_ai_diagnosis"] = not st.session_state.get(
            "show_portfolio_ai_diagnosis", False
        )
with action_column:
    if st.button("➕ 자산관리", width="stretch"):
        open_asset_manager()


# ==================================================
# 환율 및 자산 불러오기
# ==================================================

with st.spinner("계정과 환율 정보를 불러오는 중입니다..."):
    exchange_data = get_exchange_rates_to_krw()
    exchange_rates: dict[str, float] = exchange_data["rates"]
    exchange_rate_date = exchange_data["date"]
    accounts_df = get_accounts()
account_options: dict[str, int | None] = {"전체 계정": None}
for _, account in accounts_df.iterrows():
    label = f"{account['account_name']} · {account['account_type']}"
    account_options[label] = int(account["id"])

selected_account_label = st.selectbox(
    "계정 필터",
    options=list(account_options),
    key="dashboard_account_filter",
    help="선택한 투자계정의 자산만 대시보드에 표시합니다.",
)
selected_account_id = account_options[selected_account_label]

assets_df = get_assets(account_id=selected_account_id)


if assets_df.empty:

    st.divider()

    st.info(
        "아직 등록된 자산이 없습니다. "
        "상단의 자산관리 버튼에서 Excel 데이터를 가져와 주세요."
    )

    st.stop()


# ==================================================
# 새로고침 제어 영역
# ==================================================

refresh_col1, refresh_col2, refresh_col3 = (
    st.columns([2, 2, 3])
)

with refresh_col1:

    refresh_market_prices = st.button(
        "📈 전체 시세 새로고침",
        type="primary",
        width="stretch",
    )


with refresh_col2:

    refresh_exchange_rates = st.button(
        "💱 환율 새로고침",
        width="stretch",
    )


with refresh_col3:

    st.caption(
        f"환율 기준일: {exchange_rate_date} · "
        "주식·ETF·코인은 가격 API 조회값을 사용합니다."
    )


# ==================================================
# 환율 새로고침
# ==================================================

if refresh_exchange_rates:

    get_exchange_rates_to_krw.clear()

    st.success(
        "환율 캐시를 초기화했습니다."
    )

    st.rerun()


# ==================================================
# 전체 시세 새로고침
# ==================================================

if refresh_market_prices:

    refresh_targets = assets_df[
        assets_df["asset_type"].isin(
            AUTO_UPDATE_ASSET_TYPES
        )
        & assets_df["symbol"].fillna("").str.strip().ne("")
    ].copy()

    if refresh_targets.empty:

        st.warning(
            "자동 시세 갱신이 가능한 자산이 없습니다. "
            "주식·ETF·코인의 티커를 확인해 주세요."
        )

    else:

        # 기존 캐시를 비워 최신 조회를 시도합니다.
        try:
            from services.market_price_service import (
                get_crypto_price,
                get_stock_price,
            )

            get_crypto_price.clear()
            get_stock_price.clear()

        except (ImportError, AttributeError):
            pass

        total_targets = len(
            refresh_targets
        )

        progress_bar = st.progress(
            0,
            text="시세 갱신을 준비하고 있습니다.",
        )

        status_placeholder = st.empty()

        refresh_results: list[dict[str, object]] = []

        for index, (_, asset_row) in enumerate(
            refresh_targets.iterrows(),
            start=1,
        ):

            asset_id = int(
                asset_row["id"]
            )

            asset_type = str(
                asset_row["asset_type"]
            )

            asset_name = str(
                asset_row["asset_name"]
            )

            symbol = str(
                asset_row["symbol"]
            ).strip()

            currency = str(
                asset_row["currency"]
            )

            status_placeholder.info(
                f"{asset_name} ({symbol}) 시세를 조회하고 있습니다."
            )

            result = get_market_price(
                asset_type=asset_type,
                symbol=symbol,
                currency=currency,
            )

            if result["success"]:

                new_price = float(
                    result["price"]
                )

                update_asset_current_price(
                    asset_id=asset_id,
                    current_price=new_price,
                )

                refresh_results.append(
                    {
                        "자산명": asset_name,
                        "티커": symbol,
                        "결과": "성공",
                        "이전 현재가": float(
                            asset_row["current_price"]
                        ),
                        "새 현재가": new_price,
                        "통화": currency,
                        "메시지": "",
                    }
                )

            else:

                refresh_results.append(
                    {
                        "자산명": asset_name,
                        "티커": symbol,
                        "결과": "실패",
                        "이전 현재가": float(
                            asset_row["current_price"]
                        ),
                        "새 현재가": None,
                        "통화": currency,
                        "메시지": str(
                            result.get(
                                "message",
                                "조회 실패",
                            )
                        ),
                    }
                )

            progress_percent = int(
                index
                / total_targets
                * 100
            )

            progress_bar.progress(
                progress_percent,
                text=(
                    f"시세 갱신 중 "
                    f"{index}/{total_targets}"
                ),
            )

        progress_bar.empty()
        status_placeholder.empty()

        refresh_result_df = pd.DataFrame(
            refresh_results
        )

        success_count = int(
            (
                refresh_result_df["결과"]
                == "성공"
            ).sum()
        )

        failure_count = int(
            (
                refresh_result_df["결과"]
                == "실패"
            ).sum()
        )

        st.session_state[
            "last_refresh_results"
        ] = refresh_results

        st.success(
            f"전체 시세 갱신 완료: "
            f"성공 {success_count}건, "
            f"실패 {failure_count}건"
        )

        # DB에 저장된 새 현재가를 다시 불러옵니다.
        assets_df = get_assets(account_id=selected_account_id)


# ==================================================
# 최근 갱신 결과 표시
# ==================================================

last_refresh_results = st.session_state.get(
    "last_refresh_results"
)

if last_refresh_results:

    with st.expander(
        "최근 전체 시세 갱신 결과",
        expanded=False,
    ):

        result_display_df = pd.DataFrame(
            last_refresh_results
        )

        if not result_display_df.empty:

            result_display_df[
                "이전 현재가"
            ] = result_display_df.apply(
                lambda row: format_original_currency(
                    value=float(
                        row["이전 현재가"]
                    ),
                    currency=str(
                        row["통화"]
                    ),
                ),
                axis=1,
            )

            result_display_df[
                "새 현재가"
            ] = result_display_df.apply(
                lambda row: (
                    format_original_currency(
                        value=float(
                            row["새 현재가"]
                        ),
                        currency=str(
                            row["통화"]
                        ),
                    )
                    if pd.notna(
                        row["새 현재가"]
                    )
                    else "-"
                ),
                axis=1,
            )

            st.dataframe(
                result_display_df,
                width="stretch",
                hide_index=True,
            )


# ==================================================
# 포트폴리오 표시 기준
# ==================================================

base_currency = str(st.session_state.get("assetos_base_currency") or "KRW")
base_rate = exchange_rates.get(base_currency)
if base_rate is None or base_rate <= 0:
    st.warning(
        f"{base_currency} 환율을 가져오지 못해 이번 화면은 KRW 기준으로 표시합니다."
    )
    base_currency = "KRW"
    base_rate = 1.0
if "dashboard_view_mode" not in st.session_state:
    st.session_state["dashboard_view_mode"] = "부동산 제외"

view_mode = st.radio(
    "대시보드 표시 기준",
    ["전체 자산", "부동산 제외"],
    horizontal=True,
    key="dashboard_view_mode",
    help="부동산 제외를 선택하면 지표와 차트에서 부동산만 제외합니다. DB의 자산정보는 변경되지 않습니다.",
)

exclude_real_estate = view_mode == "부동산 제외"

if exclude_real_estate:
    st.info(
        "현재 대시보드는 부동산을 제외한 유동·금융자산 기준입니다. "
        "등록된 부동산 자산과 전체 DB는 그대로 유지됩니다."
    )

dashboard_analysis = get_portfolio_analysis(
    exclude_real_estate=exclude_real_estate,
    account_id=selected_account_id,
)
valid_assets_df = pd.DataFrame(dashboard_analysis.get("assets") or [])
if not valid_assets_df.empty:
    valid_assets_df["asset_name"] = valid_assets_df["name"]
    valid_assets_df["원화 매입금액"] = valid_assets_df["cost_value_krw"]
    valid_assets_df["원화 평가금액"] = valid_assets_df["value_krw"]
    valid_assets_df["원화 평가손익"] = valid_assets_df["profit_loss_krw"]
    valid_assets_df["수익률"] = valid_assets_df["return_rate"].fillna(0.0) * 100
    if base_currency != "KRW":
        for monetary_column in ("원화 매입금액", "원화 평가금액", "원화 평가손익"):
            valid_assets_df[monetary_column] /= float(base_rate)
else:
    valid_assets_df = pd.DataFrame(columns=pd.Index([
        "asset_name", "symbol", "asset_type", "asset_class", "country",
        "currency", "sector", "account_name", "quantity", "average_price",
        "current_price", "원화 매입금액", "원화 평가금액",
        "원화 평가손익", "수익률",
    ]))
dashboard_diagnosis = None
if dashboard_analysis.get("success"):
    dashboard_diagnosis = diagnose_portfolio(dashboard_analysis)
    render_ai_advisor_summary(dashboard_diagnosis)
    dashboard_export_columns = st.columns(3)
    dashboard_export_columns[0].download_button(
        "Export PDF",
        data=export_quick_analysis_pdf(dashboard_analysis, dashboard_diagnosis),
        file_name=f"AssetOS_Dashboard_{datetime.now().astimezone():%Y%m%d}.pdf",
        mime="application/pdf",
        width="stretch",
        key="dashboard_export_pdf",
    )
    dashboard_export_columns[1].download_button(
        "Export PNG",
        data=export_quick_analysis_png(dashboard_analysis, dashboard_diagnosis),
        file_name=f"AssetOS_Dashboard_{datetime.now().astimezone():%Y%m%d}.png",
        mime="image/png",
        width="stretch",
        key="dashboard_export_png",
    )
    dashboard_export_columns[2].download_button(
        "Export JSON",
        data=export_quick_analysis_json(dashboard_analysis, dashboard_diagnosis),
        file_name=f"AssetOS_Dashboard_{datetime.now().astimezone():%Y%m%d}.json",
        mime="application/json",
        width="stretch",
        key="dashboard_export_json",
    )
else:
    render_ai_card("🤖 AI Portfolio Advisor", "분석 가능한 자산이 생기면 포트폴리오 진단을 표시합니다.")
    st.caption("분석 가능한 평가금액이 생기면 PDF·PNG·JSON export를 사용할 수 있습니다.")
st.divider()

if st.session_state.get("show_portfolio_ai_diagnosis", False):
    st.subheader("🤖 AI 포트폴리오 진단")
    with st.spinner("포트폴리오 구조를 진단하고 있습니다..."):
        if dashboard_diagnosis is None:
            st.info("분석 가능한 포트폴리오 데이터가 없습니다.")
        else:
            render_ai_advisor_diagnosis(dashboard_diagnosis)
            st.caption("현재 보유구조를 설명하는 Rule Engine 결과이며 투자 권유가 아닙니다.")
    st.divider()


# ==================================================
# 핵심 지표
# ==================================================

total_purchase_krw = float(
    valid_assets_df[
        "원화 매입금액"
    ].sum()
)

total_value_krw = float(
    valid_assets_df[
        "원화 평가금액"
    ].sum()
)

total_profit_krw = (
    total_value_krw
    - total_purchase_krw
)

total_return_rate = (
    total_profit_krw
    / total_purchase_krw
    * 100
    if total_purchase_krw > 0
    else 0.0
)

asset_count = len(
    valid_assets_df
)


profit_tone = (
    "positive" if total_profit_krw > 0
    else "negative" if total_profit_krw < 0
    else "neutral"
)

render_metric_grid(
    [
        {
            "label": "Total Asset",
            "value": format_currency(total_value_krw, base_currency),
            "note": f"{asset_count:,}개 자산",
        },
        {
            "label": "Investment Principal",
            "value": format_currency(total_purchase_krw, base_currency),
            "note": "현재 표시 기준 투자원금",
        },
        {
            "label": "Total Profit",
            "value": format_currency(total_profit_krw, base_currency),
            "note": f"{base_currency} 기준 누적 손익",
            "tone": profit_tone,
        },
        {
            "label": "Total Return %",
            "value": format_percent(total_return_rate, signed=True),
            "note": "투자원금 대비 누적 수익률",
            "tone": profit_tone,
        },
    ]
)

st.divider()


# ==================================================
# 포트폴리오 배분
# ==================================================

st.subheader("Portfolio Allocation")
allocation_tabs = st.tabs(["자산 유형", "국가", "통화", "섹터", "계정"])
for tab, dimension, label in zip(
    allocation_tabs,
    ["asset_type", "country", "currency", "sector", "account_name"],
    ["자산 유형", "국가", "통화", "섹터", "계정"],
):
    with tab:
        render_allocation_chart(valid_assets_df, dimension, label)


st.divider()


# ==================================================
# 자산별 손익 현황
# ==================================================

st.subheader(
    "자산별 손익 현황"
)

profit_assets_df = valid_assets_df[
    [
        "asset_name",
        "symbol",
        "asset_type",
        "원화 평가금액",
        "원화 평가손익",
        "수익률",
    ]
].copy()

profit_assets_df = pd.DataFrame(profit_assets_df).sort_values(
    "원화 평가손익",
    ascending=False,
)

top_profit_df = (
    profit_assets_df.loc[
        profit_assets_df["원화 평가손익"] > 0
    ]
    .head(10)
    .copy()
)

top_loss_df = (
    profit_assets_df.loc[
        profit_assets_df["원화 평가손익"] < 0
    ]
    .sort_values(
        by="원화 평가손익",
        ascending=True,
        kind="stable",
    )
    .head(10)
    .copy()
)


def make_profit_loss_display(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """대시보드용 손익 표를 간결하게 가공합니다."""

    display = pd.DataFrame(dataframe.loc[:,
        [
            "asset_name",
            "symbol",
            "원화 평가손익",
            "수익률",
        ]
    ]).copy()

    display.columns = [
        "자산명",
        "티커",
        "손익",
        "수익률",
    ]

    display["자산명"] = pd.Series(display["자산명"], index=display.index).map(
        lambda value: (
            str(value)
            if len(str(value)) <= 15
            else f"{str(value)[:15]}…"
        )
    )

    display["손익"] = pd.Series(display["손익"], index=display.index).map(
        lambda value: format_currency(value, base_currency)
    )

    display["수익률"] = pd.Series(display["수익률"], index=display.index).map(
        lambda value: format_percent(value, signed=True)
    )

    return pd.DataFrame(display.reset_index(drop=True))


profit_table = make_profit_loss_display(
    top_profit_df
)

loss_table = make_profit_loss_display(
    top_loss_df
)


with st.container(border=True):

    profit_column1, profit_column2 = st.columns(
        2,
        gap="medium",
    )

    with profit_column1:

        st.markdown(
            "#### 📈 평가이익 TOP 10"
        )

        if profit_table.empty:

            st.info(
                "평가이익 자산이 없습니다."
            )

        else:

            st.dataframe(
                profit_table,
                width="stretch",
                hide_index=True,
                height=235,
                column_config={
                    "자산명": st.column_config.TextColumn(
                        "자산명",
                        width="small",
                    ),
                    "티커": st.column_config.TextColumn(
                        "티커",
                        width="small",
                    ),
                    "손익": st.column_config.TextColumn(
                        "손익",
                        width="small",
                    ),
                    "수익률": st.column_config.TextColumn(
                        "수익률",
                        width="small",
                    ),
                },
            )

    with profit_column2:

        st.markdown(
            "#### 📉 평가손실 TOP 10"
        )

        if loss_table.empty:

            st.info(
                "평가손실 자산이 없습니다."
            )

        else:

            st.dataframe(
                loss_table,
                width="stretch",
                hide_index=True,
                height=235,
                column_config={
                    "자산명": st.column_config.TextColumn(
                        "자산명",
                        width="small",
                    ),
                    "티커": st.column_config.TextColumn(
                        "티커",
                        width="small",
                    ),
                    "손익": st.column_config.TextColumn(
                        "손익",
                        width="small",
                    ),
                    "수익률": st.column_config.TextColumn(
                        "수익률",
                        width="small",
                    ),
                },
            )

# ==================================================
# 전체 보유자산 현황
# ==================================================

st.subheader(
    "전체 보유자산 현황"
)

holdings_display_df = valid_assets_df[
    [
        "asset_name",
        "symbol",
        "asset_type",
        "quantity",
        "currency",
        "average_price",
        "current_price",
        "원화 평가금액",
        "원화 평가손익",
        "수익률",
    ]
].copy()

holdings_display_df.columns = [
    "자산명",
    "티커·구분",
    "자산 종류",
    "수량",
    "통화",
    "평균단가",
    "현재가",
    f"{base_currency} 평가금액",
    f"{base_currency} 평가손익",
    "수익률",
]
holdings_display_df["자산 종류"] = pd.Series(
    holdings_display_df["자산 종류"], index=holdings_display_df.index
).map(
    format_asset_type
)


holdings_display_df[
    "수량"
] = holdings_display_df.apply(
    lambda row: format_quantity(
        value=float(
            row["수량"]
        ),
        asset_type=str(
            row["자산 종류"]
        ),
    ),
    axis=1,
)


for price_column in [
    "평균단가",
    "현재가",
]:

    holdings_display_df[
        price_column
    ] = holdings_display_df.apply(
        lambda row, price_column=price_column: format_original_currency(
            value=float(
                row[price_column]
            ),
            currency=str(
                row["통화"]
            ),
        ),
        axis=1,
    )


value_column_label = f"{base_currency} 평가금액"
profit_column_label = f"{base_currency} 평가손익"

holdings_display_df[value_column_label] = pd.Series(
    holdings_display_df[value_column_label], index=holdings_display_df.index
).map(
    lambda value: format_currency(value, base_currency)
)
holdings_display_df[profit_column_label] = pd.Series(
    holdings_display_df[profit_column_label], index=holdings_display_df.index
).map(
    lambda value: format_currency(value, base_currency)
)


holdings_display_df[
    "수익률"
] = pd.Series(
    holdings_display_df["수익률"], index=holdings_display_df.index
).map(
    lambda value: (
        format_percent(value, signed=True)
    )
)


st.dataframe(
    holdings_display_df,
    width="stretch",
    hide_index=True,
)


st.caption(
    "전체 시세 새로고침은 주식·ETF·코인만 갱신합니다. "
    "현금·예금, 부동산, 연금계좌, 기타 자산은 입력값을 유지합니다."
)

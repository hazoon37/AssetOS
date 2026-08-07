from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from components.asset_management.asset_manager_panel import render_asset_manager_panel
from database.db import (
    create_tables,
    get_assets,
    update_asset_current_price,
)
from services.exchange_rate_service import (
    convert_to_krw,
    get_exchange_rates_to_krw,
)
from services.market_price_service import (
    get_market_price,
)
from ui.components.metric_card import (
    render_ai_card,
    render_metric_grid,
    render_page_header,
)
from ui.theme import ASSET_COLORS, apply_theme


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

CURRENCY_NAMES = {
    "KRW": "대한민국 원",
    "USD": "미국 달러",
    "JPY": "일본 엔",
    "HKD": "홍콩 달러",
    "EUR": "유로",
    "GBP": "영국 파운드",
}

CURRENCY_SYMBOLS = {
    "KRW": "₩",
    "USD": "$",
    "JPY": "¥",
    "HKD": "HK$",
    "EUR": "€",
    "GBP": "£",
}


# ==================================================
# 공통 함수
# ==================================================

def format_krw(value: float) -> str:
    """원화 금액을 보기 좋게 표시합니다."""

    return f"₩ {value:,.0f}"


def format_original_currency(
    value: float,
    currency: str,
) -> str:
    """원래 통화로 금액을 표시합니다."""

    symbol = CURRENCY_SYMBOLS.get(
        currency,
        currency,
    )

    return f"{symbol} {value:,.0f}"


def format_quantity(
    value: float,
    asset_type: str,
) -> str:
    """자산 종류에 따라 수량 자릿수를 표시합니다."""

    if asset_type == "코인":
        return f"{value:,.8f}"

    if asset_type in [
        "미국주식",
        "미국ETF",
    ]:
        return f"{value:,.4f}"

    return f"{value:,.0f}"


def convert_row_value_to_krw(
    row: pd.Series,
    column_name: str,
    exchange_rates: dict[str, float],
) -> float | None:
    """데이터프레임 행의 금액을 원화로 환산합니다."""

    return convert_to_krw(
        amount=float(row[column_name]),
        currency=str(row["currency"]),
        rates=exchange_rates,
    )


def calculate_portfolio(
    assets_dataframe: pd.DataFrame,
    exchange_rates: dict[str, float],
) -> pd.DataFrame:
    """자산 손익과 원화 환산금액을 계산합니다."""

    dataframe = assets_dataframe.copy()

    numeric_columns = [
        "quantity",
        "average_price",
        "current_price",
    ]

    for column in numeric_columns:

        dataframe[column] = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        ).fillna(0.0)

    dataframe["매입금액"] = (
        dataframe["quantity"]
        * dataframe["average_price"]
    )

    dataframe["평가금액"] = (
        dataframe["quantity"]
        * dataframe["current_price"]
    )

    dataframe["평가손익"] = (
        dataframe["평가금액"]
        - dataframe["매입금액"]
    )

    dataframe["수익률"] = 0.0

    valid_purchase_rows = (
        dataframe["매입금액"] > 0
    )

    dataframe.loc[
        valid_purchase_rows,
        "수익률",
    ] = (
        dataframe.loc[
            valid_purchase_rows,
            "평가손익",
        ]
        / dataframe.loc[
            valid_purchase_rows,
            "매입금액",
        ]
        * 100
    )

    dataframe["원화 매입금액"] = dataframe.apply(
        lambda row: convert_row_value_to_krw(
            row=row,
            column_name="매입금액",
            exchange_rates=exchange_rates,
        ),
        axis=1,
    )

    dataframe["원화 평가금액"] = dataframe.apply(
        lambda row: convert_row_value_to_krw(
            row=row,
            column_name="평가금액",
            exchange_rates=exchange_rates,
        ),
        axis=1,
    )

    dataframe["원화 평가손익"] = (
        dataframe["원화 평가금액"]
        - dataframe["원화 매입금액"]
    )

    return dataframe


# ==================================================
# 페이지 제목
# ==================================================

@st.dialog("➕ 자산관리", width="large")
def open_asset_manager() -> None:
    render_asset_manager_panel()


header_column, action_column = st.columns([5, 1], vertical_alignment="center")
with header_column:
    render_page_header(
        title="총 자산 현황",
        subtitle=(
            "전체 자산을 원화 기준으로 요약하고, "
            "금융자산 구성과 손익을 한눈에 확인합니다."
        ),
    )
with action_column:
    if st.button("➕ 자산관리", use_container_width=True):
        open_asset_manager()


# ==================================================
# 환율 및 자산 불러오기
# ==================================================

exchange_data = get_exchange_rates_to_krw()

exchange_rates: dict[str, float] = (
    exchange_data["rates"]
)

exchange_rate_date = exchange_data["date"]

assets_df = get_assets()


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
        use_container_width=True,
    )


with refresh_col2:

    refresh_exchange_rates = st.button(
        "💱 환율 새로고침",
        use_container_width=True,
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
        assets_df = get_assets()


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
                use_container_width=True,
                hide_index=True,
            )


# ==================================================
# 포트폴리오 계산
# ==================================================

assets_df = calculate_portfolio(
    assets_dataframe=assets_df,
    exchange_rates=exchange_rates,
)


valid_assets_df = assets_df.dropna(
    subset=[
        "원화 매입금액",
        "원화 평가금액",
    ]
).copy()


# ==================================================
# 대시보드 표시 기준
# ==================================================

if "dashboard_view_mode" not in st.session_state:
    st.session_state["dashboard_view_mode"] = "부동산 제외"

view_mode = st.radio(
    "대시보드 표시 기준",
    ["전체 자산", "부동산 제외"],
    index=1,
    horizontal=True,
    key="dashboard_view_mode",
    help="부동산 제외를 선택하면 지표와 차트에서 부동산만 제외합니다. DB의 자산정보는 변경되지 않습니다.",
)

exclude_real_estate = view_mode == "부동산 제외"

if exclude_real_estate:
    real_estate_mask = (
        valid_assets_df["asset_type"].fillna("").eq("부동산")
    )

    if "asset_class" in valid_assets_df.columns:
        real_estate_mask = real_estate_mask | (
            valid_assets_df["asset_class"].fillna("").eq("REAL_ESTATE")
        )

    valid_assets_df = valid_assets_df.loc[~real_estate_mask].copy()

    st.info(
        "현재 대시보드는 부동산을 제외한 유동·금융자산 기준입니다. "
        "등록된 부동산 자산과 전체 DB는 그대로 유지됩니다."
    )


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
            "value": format_krw(total_value_krw),
            "note": f"{asset_count:,}개 자산",
        },
        {
            "label": "Investment Principal",
            "value": format_krw(total_purchase_krw),
            "note": "현재 표시 기준 투자원금",
        },
        {
            "label": "Total Profit",
            "value": format_krw(total_profit_krw),
            "note": f"{total_profit_krw:+,.0f}원",
            "tone": profit_tone,
        },
        {
            "label": "Total Return %",
            "value": f"{total_return_rate:+.2f}%",
            "note": "투자원금 대비 누적 수익률",
            "tone": profit_tone,
        },
    ]
)

st.divider()


# ==================================================
# 자산 종류별 요약
# ==================================================

asset_type_summary = (
    valid_assets_df.groupby(
        "asset_type",
        as_index=False,
    )["원화 평가금액"]
    .sum()
    .sort_values(
        "원화 평가금액",
        ascending=False,
    )
)

if not asset_type_summary.empty:

    asset_type_summary["비중"] = (
        asset_type_summary["원화 평가금액"]
        / asset_type_summary[
            "원화 평가금액"
        ].sum()
        * 100
    )


# ==================================================
# 포트폴리오 배분
# ==================================================

st.subheader("Portfolio Allocation")

if asset_type_summary.empty:
    st.info("표시할 자산 데이터가 없습니다.")
else:
    asset_pie_chart = px.pie(
        asset_type_summary,
        names="asset_type",
        values="원화 평가금액",
        hole=0.62,
        color="asset_type",
        color_discrete_map=ASSET_COLORS,
    )
    asset_pie_chart.update_traces(
        textposition="inside",
        texttemplate="%{label}<br>%{percent}",
        hovertemplate=(
            "%{label}<br>평가금액: ₩ %{value:,.0f}<br>"
            "비중: %{percent}<extra></extra>"
        ),
    )
    asset_pie_chart.update_layout(
        margin={"l": 10, "r": 10, "t": 18, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend_title_text="",
        font={"color": "#334155", "size": 12},
    )
    st.plotly_chart(asset_pie_chart, use_container_width=True)


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

profit_assets_df = profit_assets_df.sort_values(
    "원화 평가손익",
    ascending=False,
)

top_profit_df = (
    profit_assets_df.loc[
        profit_assets_df["원화 평가손익"] > 0
    ]
    .head(5)
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
    .head(5)
    .copy()
)


def make_profit_loss_display(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """대시보드용 손익 표를 간결하게 가공합니다."""

    display = dataframe[
        [
            "asset_name",
            "symbol",
            "원화 평가손익",
            "수익률",
        ]
    ].copy()

    display.columns = [
        "자산명",
        "티커",
        "손익",
        "수익률",
    ]

    display["자산명"] = display["자산명"].map(
        lambda value: (
            str(value)
            if len(str(value)) <= 15
            else f"{str(value)[:15]}…"
        )
    )

    display["손익"] = display["손익"].map(
        lambda value: f"₩ {value:+,.0f}"
    )

    display["수익률"] = display["수익률"].map(
        lambda value: f"{value:+,.2f}%"
    )

    return display.reset_index(drop=True)


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
            "#### 📈 평가이익 TOP 5"
        )

        if profit_table.empty:

            st.info(
                "평가이익 자산이 없습니다."
            )

        else:

            st.dataframe(
                profit_table,
                use_container_width=True,
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
            "#### 📉 평가손실 TOP 5"
        )

        if loss_table.empty:

            st.info(
                "평가손실 자산이 없습니다."
            )

        else:

            st.dataframe(
                loss_table,
                use_container_width=True,
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

st.markdown("### AI Summary")
render_ai_card(
    "✨ AI Summary",
    "포트폴리오 변화와 주요 리스크를 요약하는 AI 브리핑이 이곳에 표시될 예정입니다.",
)

st.divider()


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
    "원화 평가금액",
    "원화 평가손익",
    "수익률",
]


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
        lambda row: format_original_currency(
            value=float(
                row[price_column]
            ),
            currency=str(
                row["통화"]
            ),
        ),
        axis=1,
    )


holdings_display_df[
    "원화 평가금액"
] = holdings_display_df[
    "원화 평가금액"
].map(
    lambda value: (
        f"₩ {value:,.0f}"
    )
)


holdings_display_df[
    "원화 평가손익"
] = holdings_display_df[
    "원화 평가손익"
].map(
    lambda value: (
        f"₩ {value:+,.0f}"
    )
)


holdings_display_df[
    "수익률"
] = holdings_display_df[
    "수익률"
].map(
    lambda value: (
        f"{value:+,.2f}%"
    )
)


st.dataframe(
    holdings_display_df,
    use_container_width=True,
    hide_index=True,
)


st.caption(
    "전체 시세 새로고침은 주식·ETF·코인만 갱신합니다. "
    "현금·예금, 부동산, 연금계좌, 기타 자산은 입력값을 유지합니다."
)

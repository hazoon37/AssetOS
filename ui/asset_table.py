from __future__ import annotations

import pandas as pd
import streamlit as st

from components.asset_management.calculations import calculate_assets, calculate_summary
from components.asset_management.controller import remove_assets
from components.asset_management.helpers import (
    format_currency_value,
    format_quantity_value,
)
from components.asset_management.state import open_delete, open_edit
from ui.asset_cards import render_portfolio_summary
from ui.asset_forms import render_inline_edit_form
from ui.common.formatters import format_asset_type, format_currency, format_percent
from ui.dialogs import render_inline_delete_confirm


def _filter_assets(df: pd.DataFrame) -> pd.DataFrame:
    filter_col1, filter_col2 = st.columns([2, 1])
    with filter_col1:
        search_text = st.text_input(
            "보유자산 검색", placeholder="자산명 또는 티커를 입력하세요.",
            key="asset_list_search",
        ).strip().lower()
    with filter_col2:
        types = ["전체"] + sorted(df["asset_type"].dropna().astype(str).unique().tolist())
        selected_type = st.selectbox(
            "자산 종류 필터",
            types,
            format_func=format_asset_type,
            key="asset_list_type_filter",
        )

    filtered = df.copy()
    if search_text:
        names = filtered["asset_name"].fillna("").astype(str).str.lower()
        symbols = filtered["symbol"].fillna("").astype(str).str.lower()
        filtered = filtered[
            names.str.contains(search_text, regex=False)
            | symbols.str.contains(search_text, regex=False)
        ]
    if selected_type != "전체":
        filtered = filtered[filtered["asset_type"] == selected_type]
    return filtered


def _render_action_rows(df: pd.DataFrame) -> None:
    st.markdown('<div class="assetos-section-title">보유자산 목록</div>', unsafe_allow_html=True)
    st.caption("각 자산 오른쪽의 수정·삭제 버튼으로 바로 관리할 수 있습니다.")

    header = st.columns([0.5, 2.0, 1.1, 1.0, 1.3, 1.2, 0.65, 0.65])
    for column, label in zip(
        header, ["번호", "자산명", "종류", "수량", "평가금액", "평가손익", "수정", "삭제"]
    ):
        column.markdown(f"**{label}**")
    st.divider()

    if df.empty:
        st.info("검색 조건에 맞는 자산이 없습니다.")
        return

    for _, row in df.iterrows():
        asset_id = int(row["id"])
        columns = st.columns([0.5, 2.0, 1.1, 1.0, 1.3, 1.2, 0.65, 0.65])
        columns[0].write(int(row["표시번호"]))
        symbol = str(row["symbol"] or "").strip()
        columns[1].markdown(
            f"**{row['asset_name']}**" + (f"  \n`{symbol}`" if symbol else "")
        )
        columns[2].write(format_asset_type(row["asset_type"]))
        columns[3].write(format_quantity_value(float(row["quantity"]), str(row["asset_type"])))
        krw_value = row["원화 평가금액"]
        krw_profit = row["원화 평가손익"]
        columns[4].write(format_currency(krw_value) if pd.notna(krw_value) else "환율 오류")
        columns[5].write(format_currency(krw_profit) if pd.notna(krw_profit) else "-")

        if columns[6].button("수정", key=f"asset_row_edit_{asset_id}", width="stretch"):
            open_edit(asset_id)
            st.rerun()
        if columns[7].button("삭제", key=f"asset_row_delete_{asset_id}", width="stretch"):
            open_delete(asset_id)
            st.rerun()

        render_inline_edit_form(row)
        render_inline_delete_confirm(row)
        st.divider()


def _render_detail_table(df: pd.DataFrame) -> None:
    with st.expander("전체 자산 상세표 보기", expanded=False):
        display = df[[
            "표시번호", "asset_type", "asset_name", "symbol", "quantity",
            "average_price", "current_price", "평가금액", "평가손익",
            "수익률", "currency", "원화 평가금액",
        ]].copy()
        display.columns = [
            "번호", "자산 종류", "자산명", "티커·구분", "수량", "평균단가",
            "현재가", "평가금액", "평가손익", "수익률", "통화", "원화 환산금액",
        ]
        display["자산 종류"] = display["자산 종류"].map(format_asset_type)
        display["번호"] = display["번호"].astype(int)
        display["수량"] = display.apply(
            lambda row: format_quantity_value(float(row["수량"]), str(row["자산 종류"])), axis=1
        )
        for column in ["평균단가", "현재가", "평가금액", "평가손익"]:
            display[column] = display.apply(
                lambda row, column=column: format_currency_value(
                    float(row[column]), str(row["통화"])
                ),
                axis=1,
            )
        display["원화 환산금액"] = display["원화 환산금액"].map(
            lambda value: format_currency(value) if pd.notna(value) else "환율 조회 실패"
        )
        display["수익률"] = display["수익률"].map(
            lambda value: format_percent(value, signed=True)
        )
        st.dataframe(display, width="stretch", hide_index=True)


def _render_bulk_delete(df: pd.DataFrame) -> None:
    """Render a deliberate, user-confirmed bulk deletion control."""
    if df.empty:
        return
    labels = {
        int(row["id"]): f"{row['asset_name']} · {row.get('symbol') or '티커 없음'}"
        for _, row in df.iterrows()
    }
    with st.expander("여러 자산 삭제", expanded=False):
        selected = st.multiselect(
            "삭제할 자산",
            options=list(labels),
            format_func=lambda asset_id: labels[asset_id],
            key="asset_bulk_delete_selection",
        )
        confirmed = st.checkbox(
            f"선택한 {len(selected):,}개 자산을 삭제합니다.",
            key="asset_bulk_delete_confirm",
            disabled=not selected,
        )
        if st.button(
            "선택 자산 삭제",
            type="primary",
            width="stretch",
            disabled=not selected or not confirmed,
            key="asset_bulk_delete_button",
        ):
            deleted = remove_assets([int(asset_id) for asset_id in selected])
            st.success(f"{deleted:,}개 자산을 삭제했습니다.")
            st.rerun()


def render_asset_management_view(
    assets_df: pd.DataFrame,
    exchange_rates: dict[str, float],
    exchange_rate_date: str,
    *,
    show_summary: bool = True,
) -> None:
    st.subheader("보유자산 현황")
    if assets_df.empty:
        st.info("현재 등록된 자산이 없습니다.")
        return

    calculated = calculate_assets(assets_df, exchange_rates)
    if show_summary:
        render_portfolio_summary(calculate_summary(calculated), exchange_rate_date)
        st.divider()
    filtered = _filter_assets(calculated)
    _render_action_rows(filtered)
    _render_bulk_delete(filtered)
    _render_detail_table(filtered)
    st.caption("번호는 화면 표시용입니다. 자산 삭제 후 남은 자산에 1번부터 자동으로 다시 부여됩니다.")

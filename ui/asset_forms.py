from __future__ import annotations

import pandas as pd
import streamlit as st

from components.asset_management.constants import ASSET_TYPES, CURRENCY_NAMES, SUPPORTED_CURRENCIES
from components.asset_management.controller import save_asset_changes
from components.asset_management.helpers import get_quantity_format, get_quantity_step, safe_text
from components.asset_management.state import clear_action_state, is_editing


def render_inline_edit_form(row: pd.Series) -> None:
    asset_id = int(row["id"])
    if not is_editing(asset_id):
        return

    st.markdown("##### ✏️ 선택 자산 수정")
    current_type = str(row["asset_type"])
    current_currency = str(row["currency"])
    currency_options = SUPPORTED_CURRENCIES.copy()
    if current_currency not in currency_options:
        currency_options.append(current_currency)

    with st.form(f"inline_edit_form_{asset_id}"):
        left, right = st.columns(2)
        with left:
            asset_type = st.selectbox(
                "자산 종류", ASSET_TYPES, index=ASSET_TYPES.index(current_type),
                key=f"inline_edit_type_{asset_id}",
            )
            name = st.text_input(
                "자산명 또는 계좌명", value=safe_text(row["asset_name"]),
                key=f"inline_edit_name_{asset_id}",
            )
            symbol = st.text_input(
                "종목코드·티커·구분명", value=safe_text(row["symbol"]),
                key=f"inline_edit_symbol_{asset_id}",
            )
            currency = st.selectbox(
                "기준 통화", currency_options, index=currency_options.index(current_currency),
                format_func=lambda code: f"{code} · {CURRENCY_NAMES.get(code, code)}",
                key=f"inline_edit_currency_{asset_id}",
            )

        with right:
            quantity = st.number_input(
                "보유수량", min_value=0.0, value=float(row["quantity"]),
                step=get_quantity_step(asset_type), format=get_quantity_format(asset_type),
                key=f"inline_edit_quantity_{asset_id}",
            )
            average_price = st.number_input(
                f"평균 매입단가 ({currency})", min_value=0.0,
                value=float(row["average_price"]), step=1.0, format="%.0f",
                key=f"inline_edit_average_{asset_id}",
            )
            current_price = st.number_input(
                f"현재 가격 ({currency})", min_value=0.0,
                value=float(row["current_price"]), step=1.0, format="%.0f",
                key=f"inline_edit_current_{asset_id}",
            )
            memo = st.text_area(
                "메모", value=safe_text(row["memo"]), key=f"inline_edit_memo_{asset_id}",
            )

        save_col, cancel_col = st.columns(2)
        save_clicked = save_col.form_submit_button("수정 내용 저장", type="primary", width="stretch")
        cancel_clicked = cancel_col.form_submit_button("취소", width="stretch")

        if cancel_clicked:
            clear_action_state()
            st.rerun()

        if save_clicked:
            if not name.strip():
                st.error("자산명을 입력해 주세요.")
            elif quantity <= 0:
                st.error("수량은 0보다 커야 합니다.")
            else:
                save_asset_changes(
                    asset_id=asset_id,
                    asset_type=asset_type,
                    asset_name=name.strip(),
                    symbol=symbol.strip().upper(),
                    quantity=float(quantity),
                    average_price=float(average_price),
                    current_price=float(current_price),
                    currency=currency,
                    memo=memo.strip(),
                )
                clear_action_state()
                st.success("자산 정보가 수정되었습니다.")
                st.rerun()

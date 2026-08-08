from __future__ import annotations

import pandas as pd
import streamlit as st

from components.asset_management.controller import remove_asset
from components.asset_management.helpers import safe_text
from components.asset_management.state import clear_action_state, is_deleting


def render_inline_delete_confirm(row: pd.Series) -> None:
    asset_id = int(row["id"])
    if not is_deleting(asset_id):
        return

    asset_name = safe_text(row["asset_name"])
    st.warning(f"‘{asset_name}’ 자산을 삭제하시겠습니까? 삭제 후에는 되돌릴 수 없습니다.")
    delete_col, cancel_col = st.columns(2)
    if delete_col.button(
        "삭제 확정", type="primary", width="stretch",
        key=f"inline_delete_confirm_{asset_id}",
    ):
        remove_asset(asset_id)
        clear_action_state()
        st.success("선택한 자산이 삭제되었습니다.")
        st.rerun()
    if cancel_col.button(
        "취소", width="stretch", key=f"inline_delete_cancel_{asset_id}",
    ):
        clear_action_state()
        st.rerun()

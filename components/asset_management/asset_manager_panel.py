from __future__ import annotations

from datetime import date

import streamlit as st

from components.asset_management.excel_import_panel import render_excel_import_panel
from components.asset_management.add_asset_tab import render_add_asset_tab
from components.asset_management.helpers import prepare_assets_dataframe
from database.db import get_accounts, get_assets
from services.asset_export_service import export_assets_json
from services.exchange_rate_service import get_exchange_rates_to_krw
from services.excel_asset_service import build_asset_template_excel, export_assets_excel
from ui.asset_table import render_asset_management_view


def render_asset_manager_panel() -> None:
    """Render the reusable Excel asset-management workspace."""
    accounts = get_accounts()
    account_options: dict[str, int | None] = {"전체 계정": None}
    for _, account in accounts.iterrows():
        account_options[f"{account['account_name']} · {account['account_type']}"] = int(account["id"])
    selected_label = st.selectbox(
        "관리할 계정",
        options=list(account_options),
        key="asset_manager_account_filter",
    )
    assets = get_assets(account_id=account_options[selected_label])
    st.caption(f"선택 범위: {len(assets):,}개 자산")

    manage_tab, template_tab, export_tab, import_tab = st.tabs(
        ["자산 목록", "템플릿", "내보내기", "가져오기"]
    )
    with manage_tab:
        exchange_data = get_exchange_rates_to_krw()
        exchange_rates = exchange_data.get("rates") or {"KRW": 1.0}
        with st.expander("➕ 새 자산 등록", expanded=assets.empty):
            render_add_asset_tab(
                exchange_rates,
                account_id=account_options[selected_label],
            )
        render_asset_management_view(
            prepare_assets_dataframe(assets),
            exchange_rates,
            exchange_data.get("date") or "정보 없음",
            show_summary=False,
        )
    with template_tab:
        st.caption("현재 Import 형식과 호환되는 AssetOS Excel 템플릿입니다.")
        st.download_button(
            "Excel Template 다운로드",
            data=build_asset_template_excel(),
            file_name="AssetOS_Template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    with export_tab:
        st.caption("선택한 계정 범위의 자산을 Excel 또는 JSON으로 내보냅니다.")
        st.download_button(
            "현재 Asset DB 다운로드",
            data=export_assets_excel(assets),
            file_name=f"AssetOS_Assets_{date.today():%Y%m%d}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
        st.download_button(
            "현재 Asset DB JSON 다운로드",
            data=export_assets_json(assets),
            file_name=f"AssetOS_Assets_{date.today():%Y%m%d}.json",
            mime="application/json",
            width="stretch",
        )
    with import_tab:
        render_excel_import_panel()

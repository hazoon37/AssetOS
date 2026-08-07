from __future__ import annotations

from datetime import date

import streamlit as st

from components.asset_management.excel_import_panel import render_excel_import_panel
from database.db import get_assets
from services.excel_asset_service import build_asset_template_excel, export_assets_excel


def render_asset_manager_panel() -> None:
    """Render the reusable Excel asset-management workspace."""
    assets = get_assets()
    st.caption(f"현재 데이터베이스: {len(assets):,}개 자산")

    template_tab, export_tab, import_tab = st.tabs(["템플릿", "내보내기", "가져오기"])
    with template_tab:
        st.caption("현재 Import 형식과 호환되는 AssetOS Excel 템플릿입니다.")
        st.download_button(
            "Excel Template 다운로드",
            data=build_asset_template_excel(),
            file_name="AssetOS_Template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with export_tab:
        st.caption("현재 DB의 모든 자산을 Excel로 내보냅니다.")
        st.download_button(
            "현재 Asset DB 다운로드",
            data=export_assets_excel(assets),
            file_name=f"AssetOS_Assets_{date.today():%Y%m%d}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with import_tab:
        render_excel_import_panel()

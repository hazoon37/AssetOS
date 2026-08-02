from __future__ import annotations

from datetime import date

import streamlit as st

from components.asset_management.excel_import_panel import render_excel_import_panel
from database.db import get_assets
from services.excel_asset_service import (
    build_asset_template_excel,
    export_assets_excel,
)
from ui.theme import apply_theme


st.set_page_config(
    page_title="AssetOS Asset Manager",
    page_icon="📂",
    layout="wide",
)

apply_theme()

st.title("📂 Asset Manager")
st.write(
    "AssetOS 표준 Excel 양식으로 자산 데이터를 내려받고, "
    "검증된 파일을 미리 본 뒤 안전하게 반영합니다."
)

assets = get_assets()
st.caption(f"현재 데이터베이스: {len(assets):,}개 자산")

st.divider()
st.subheader("다운로드")
template_column, export_column = st.columns(2)

with template_column:
    st.markdown("#### Excel 템플릿")
    st.caption("현재 자산 DB 스키마의 전체 열이 포함된 빈 Assets 시트입니다.")
    st.download_button(
        "Excel Template 다운로드",
        data=build_asset_template_excel(),
        file_name="AssetOS_Asset_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

with export_column:
    st.markdown("#### 현재 데이터 내보내기")
    st.caption("현재 DB의 모든 자산과 스키마 열을 Excel로 내보냅니다.")
    st.download_button(
        "현재 Asset DB 다운로드",
        data=export_assets_excel(assets),
        file_name=f"AssetOS_Assets_{date.today():%Y%m%d}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

st.divider()
render_excel_import_panel()

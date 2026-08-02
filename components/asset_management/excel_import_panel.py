from __future__ import annotations

import streamlit as st

from services.excel_asset_service import import_asset_excel, validate_asset_excel
from services.portfolio_service import clear_portfolio_analysis_cache


def render_excel_import_panel() -> None:
    """AssetOS 표준 Excel 파일을 검증하고 SQLite DB로 가져옵니다."""

    st.markdown("#### 📥 Excel 자산 DB 가져오기")
    st.caption(
        "AssetOS 표준 양식의 `Assets` 시트를 읽습니다. "
        "파일을 선택해도 DB는 변경되지 않습니다. 미리보기와 검증을 확인한 뒤 "
        "'Apply Changes'를 눌러야 현재 자산 목록 전체가 Excel 내용으로 교체됩니다."
    )

    uploaded_file = st.file_uploader(
        "자산 DB Excel 파일",
        type=["xlsx"],
        accept_multiple_files=False,
        key="asset_excel_uploader",
        help="AssetOS_개인자산_DB_*.xlsx 파일을 선택하세요.",
    )

    if uploaded_file is None:
        return

    file_bytes = uploaded_file.getvalue()
    validation = validate_asset_excel(file_bytes)

    if validation.preview.empty is False:
        st.write("**가져오기 미리보기**")
        st.dataframe(validation.preview, use_container_width=True, hide_index=True)

    if validation.errors:
        for error in validation.errors:
            st.error(error)
        return

    st.success(f"검증 완료: {len(validation.rows):,}개 자산을 가져올 수 있습니다.")

    for warning in validation.warnings[:10]:
        st.warning(warning)
    if len(validation.warnings) > 10:
        st.caption(f"추가 경고 {len(validation.warnings) - 10:,}건이 있습니다.")

    confirmed = st.checkbox(
        "현재 DB를 백업한 뒤 미리보기 내용으로 전체 교체하는 것에 동의합니다.",
        key="asset_excel_replace_confirm",
    )

    if st.button(
        "Apply Changes",
        type="primary",
        use_container_width=True,
        disabled=not confirmed,
        key="asset_excel_import_button",
        help="현재 DB를 먼저 백업한 뒤, 미리보기의 데이터로 전체 교체합니다.",
    ):
        with st.spinner("기존 DB를 백업하고 Excel 데이터를 반영하고 있습니다..."):
            result = import_asset_excel(file_bytes)

        if result.get("success"):
            clear_portfolio_analysis_cache()
            st.session_state.pop("asset_excel_replace_confirm", None)
            st.success(
                f"완료: {result['imported_count']:,}개 자산을 업데이트했습니다."
            )
            if result.get("backup_path"):
                st.caption(f"기존 DB 백업: {result['backup_path']}")
            st.rerun()
        else:
            for error in result.get("errors", []):
                st.error(error)

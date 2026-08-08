from __future__ import annotations

import hashlib

import streamlit as st

from database.db import get_accounts
from services.excel_asset_service import (
    build_validation_error_report,
    import_asset_rows,
    validate_asset_excel,
)
from services.portfolio_service import clear_portfolio_analysis_cache
from services.smart_import_service import (
    enrich_import_rows_cached,
    finalize_import_rows,
    resolution_state,
)
from components.asset_management.import_candidate_picker import render_candidate_pickers


def render_excel_import_panel() -> None:
    """Excel 파일을 감지·검증하고 기존 import service로 가져옵니다."""

    st.markdown("#### 📥 Excel 자산 DB 가져오기")
    st.caption(
        "AssetOS 양식과 일반 Excel 파일을 자동으로 인식합니다. "
        "파일을 선택해도 DB는 변경되지 않습니다. 미리보기와 검증을 확인한 뒤 "
        "'Apply Changes'를 눌러야 현재 자산 목록 전체가 Excel 내용으로 교체됩니다."
    )

    accounts = get_accounts()
    if accounts.empty:
        st.error("가져올 대상 계정을 찾지 못했습니다.")
        return
    account_records = accounts.to_dict(orient="records")
    default_index = next(
        (
            index
            for index, account in enumerate(account_records)
            if account["account_name"] == "My Portfolio"
        ),
        0,
    )
    target_account = st.selectbox(
        "가져올 대상 계정",
        options=account_records,
        index=default_index,
        format_func=lambda account: (
            f"{account['account_name']} · {account['account_type']}"
        ),
        key="asset_excel_target_account",
        help="Apply Changes를 누르면 선택한 계정의 자산만 교체됩니다.",
    )
    target_account_id = int(target_account["id"])
    target_account_name = str(target_account["account_name"])

    uploaded_file = st.file_uploader(
        "자산 DB Excel 파일",
        type=["xlsx"],
        accept_multiple_files=False,
        key="asset_excel_uploader",
        help="AssetOS 양식 또는 자산명과 수량이 포함된 .xlsx 파일을 선택하세요.",
    )

    if uploaded_file is None:
        return

    file_bytes = uploaded_file.getvalue()
    validation = validate_asset_excel(file_bytes)

    if validation.file_type is not None:
        st.caption(f"감지된 파일 형식: {validation.file_type.value}")
    changed_mappings = {
        source: target
        for source, target in validation.mapped_columns.items()
        if source != target
    }
    if changed_mappings:
        mapping_text = ", ".join(
            f"{source} → {target}" for source, target in changed_mappings.items()
        )
        st.caption(f"자동 열 매핑: {mapping_text}")

    if validation.errors:
        if validation.preview.empty is False:
            st.write("**파일 내용 미리보기**")
            st.dataframe(validation.preview, width="stretch", hide_index=True)
        for error in validation.errors:
            st.error(error)
        if not validation.source_dataframe.empty:
            st.download_button(
                "Download Error Report",
                data=build_validation_error_report(validation),
                file_name="Import_Error.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="asset_excel_validation_error_report",
            )
        return

    st.success(f"기본 검증 완료: {len(validation.rows):,}개 자산을 확인했습니다.")

    if validation.warnings:
        st.caption("파일 검증: " + " · ".join(validation.warnings))

    preview_key = hashlib.sha256(file_bytes).hexdigest()[:16]
    with st.spinner("자산 정보와 현재가를 자동 조회하고 있습니다..."):
        batch_results = enrich_import_rows_cached(validation.rows)
        batch_results = render_candidate_pickers(
            validation.rows,
            batch_results,
            key_prefix=f"asset_candidate_{preview_key}",
            source_dataframe=validation.source_dataframe,
        )
    import_rows = finalize_import_rows(batch_results)
    has_blocking_rows = any(
        resolution_state(result) in {"needs_selection", "failed"}
        for result in batch_results
    )
    if has_blocking_rows:
        st.caption("Select 또는 Fail 행은 Apply Changes에서 저장 전에 다시 검증됩니다.")

    confirmed = st.checkbox(
        f"현재 DB를 백업한 뒤 '{target_account_name}' 계정을 미리보기 내용으로 전체 교체하는 것에 동의합니다.",
        key="asset_excel_replace_confirm",
    )

    if st.button(
        "Apply Changes",
        type="primary",
        width="stretch",
        disabled=not confirmed,
        key="asset_excel_import_button",
        help="현재 DB를 먼저 백업한 뒤, 미리보기의 데이터로 전체 교체합니다.",
    ):
        unresolved_states = [resolution_state(result) for result in batch_results]
        select_count = unresolved_states.count("needs_selection")
        fail_count = unresolved_states.count("failed")
        if fail_count:
            st.warning(f"Fail 상태 {fail_count:,}개 행의 Ticker를 먼저 수정해 주세요.")
        if select_count:
            st.warning(f"Select 상태 {select_count:,}개 행의 후보를 먼저 선택해 주세요.")
        if fail_count or select_count:
            return
        with st.spinner("기존 DB를 백업하고 Excel 데이터를 반영하고 있습니다..."):
            result = import_asset_rows(
                import_rows,
                validation.warnings,
                account_id=target_account_id,
            )

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

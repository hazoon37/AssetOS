from __future__ import annotations

import hashlib
from datetime import datetime

import pandas as pd
import streamlit as st

from components.asset_management.import_candidate_picker import render_candidate_pickers
from database.db import get_accounts
from services.excel_asset_service import (
    build_validation_error_report,
    validate_asset_excel,
)
from services.exchange_rate_service import get_exchange_rates_to_krw
from services.portfolio_service import clear_portfolio_analysis_cache
from services.quick_analysis_export_service import (
    export_quick_analysis_json,
    export_quick_analysis_pdf,
    export_quick_analysis_png,
)
from services.quick_analysis_service import run_quick_analysis, save_quick_analysis
from services.smart_import_service import (
    SmartImportResolution,
    enrich_import_rows_cached,
    finalize_import_rows,
    resolution_state,
)
from ui.common.formatters import format_currency
from ui.components.ai_advisor_card import render_ai_advisor_diagnosis
from ui.components.metric_card import render_metric_grid

_RESULT_KEYS = (
    "quick_analysis_result",
    "quick_analysis_diagnosis",
    "quick_analysis_rows",
    "quick_analysis_resolved_rows",
    "quick_analysis_resolver_warnings",
    "quick_analysis_exports",
    "quick_analysis_warnings",
)


def _clear_result() -> None:
    for key in _RESULT_KEYS:
        st.session_state.pop(key, None)


def _resolved_results(
    rows: list[dict[str, object]], *, key_prefix: str,
    source_dataframe: pd.DataFrame | None = None,
) -> tuple[list[SmartImportResolution], list[str]]:
    warnings: list[str] = []
    results = render_candidate_pickers(
        rows, enrich_import_rows_cached(rows), key_prefix=key_prefix,
        source_dataframe=source_dataframe,
    )
    for index, (source, result) in enumerate(zip(rows, results), start=2):
        row_number = int(source.get("_excel_row_number") or index)
        warnings.extend(f"{row_number}행 '{source['asset_name']}': {item}" for item in result.warnings)
    return results, warnings


def _render_analysis_summary(result: dict[str, object]) -> None:
    summary = result.get("summary", {})
    render_metric_grid([
        {"label": "총 평가금액", "value": format_currency(summary.get("total_value_krw"))},
        {"label": "투자원금", "value": format_currency(summary.get("total_cost_krw"))},
        {"label": "평가손익", "value": format_currency(summary.get("profit_loss_krw"))},
        {"label": "분석 자산", "value": f"{int(summary.get('asset_count') or 0):,}개"},
    ])


def render_quick_analysis_panel() -> None:
    """Run an Excel-to-report workflow entirely in Streamlit session memory."""
    st.caption(
        "Excel을 임시 분석합니다. 업로드 데이터와 결과는 SQLite에 저장되지 않으며 "
        "현재 브라우저 세션이 끝나면 사라집니다."
    )
    uploaded = st.file_uploader(
        "분석할 Excel 파일",
        type=["xlsx"],
        key="quick_analysis_uploader",
    )
    if uploaded is None:
        st.info("AssetOS 템플릿 또는 자산명·수량이 포함된 Excel 파일을 선택하세요.")
        return

    mode = st.radio(
        "분석 후 처리",
        ["Analyze Only", "Save into AssetOS"],
        horizontal=True,
        key="quick_analysis_mode",
        help="Analyze Only는 SQLite를 변경하지 않습니다. 저장은 분석 완료 후 별도 확인이 필요합니다.",
    )

    file_bytes = uploaded.getvalue()
    file_hash = hashlib.sha256(file_bytes).hexdigest()[:16]
    if st.session_state.get("quick_analysis_file_hash") != file_hash:
        _clear_result()
        st.session_state["quick_analysis_file_hash"] = file_hash

    validation = validate_asset_excel(file_bytes)
    if validation.errors:
        for error in validation.errors:
            st.error(error)
        if not validation.preview.empty:
            st.dataframe(validation.preview, width="stretch", hide_index=True)
        if not validation.source_dataframe.empty:
            st.download_button(
                "Download Error Report",
                data=build_validation_error_report(validation),
                file_name="Import_Error.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="quick_validation_error_report",
            )
        return
    st.success(f"Excel 검증 완료: {len(validation.rows):,}개 자산")
    with st.spinner("Smart Import가 자산과 현재가를 확인하고 있습니다..."):
        resolution_results, resolver_warnings = _resolved_results(
            validation.rows,
            key_prefix=f"quick_candidate_{file_hash}",
            source_dataframe=validation.source_dataframe,
        )
    import_rows = finalize_import_rows(resolution_results)
    st.session_state["quick_analysis_resolved_rows"] = import_rows
    st.session_state["quick_analysis_resolver_warnings"] = resolver_warnings
    has_blocking_rows = any(
        resolution_state(result) in {"needs_selection", "failed"}
        for result in resolution_results
    )
    warnings = validation.warnings + resolver_warnings
    if validation.warnings:
        st.caption("파일 검증: " + " · ".join(validation.warnings))

    if st.button(
        "포트폴리오 분석 실행",
        type="primary",
        width="stretch",
        disabled=has_blocking_rows,
        key="quick_analysis_run",
    ):
        exchange = get_exchange_rates_to_krw()
        try:
            quick_result = run_quick_analysis(
                import_rows,
                exchange.get("rates") or {"KRW": 1.0},
            )
        except ValueError as error:
            st.error(str(error))
            return
        analysis = quick_result.analysis
        diagnosis = quick_result.diagnosis
        analysis["exchange_rate_date"] = exchange.get("date")
        st.session_state["quick_analysis_result"] = analysis
        st.session_state["quick_analysis_diagnosis"] = diagnosis
        st.session_state["quick_analysis_rows"] = import_rows
        st.session_state["quick_analysis_warnings"] = warnings
        st.session_state["quick_analysis_exports"] = {
            "pdf": export_quick_analysis_pdf(analysis, diagnosis),
            "png": export_quick_analysis_png(analysis, diagnosis),
            "json": export_quick_analysis_json(analysis, diagnosis),
        }

    analysis = st.session_state.get("quick_analysis_result")
    diagnosis = st.session_state.get("quick_analysis_diagnosis")
    exports = st.session_state.get("quick_analysis_exports")
    if not analysis or diagnosis is None or not exports:
        return
    st.divider()
    st.subheader("Portfolio Analysis")
    _render_analysis_summary(analysis)
    st.subheader("AI Advisor")
    render_ai_advisor_diagnosis(diagnosis)
    st.info(f"다음 행동: {diagnosis.next_action}")

    if mode == "Save into AssetOS":
        accounts = get_accounts()
        account_records = accounts.to_dict(orient="records")
        target = st.selectbox(
            "저장할 계정",
            options=account_records,
            format_func=lambda account: f"{account['account_name']} · {account['account_type']}",
            key="quick_analysis_target_account",
        )
        confirmed = st.checkbox(
            f"'{target['account_name']}' 계정을 백업한 뒤 현재 분석 자산으로 전체 교체합니다.",
            key="quick_analysis_save_confirmed",
        )
        if st.button(
            "Save into AssetOS",
            type="primary",
            width="stretch",
            disabled=not confirmed,
            key="quick_analysis_save",
        ):
            save_result = save_quick_analysis(
                st.session_state["quick_analysis_rows"],
                account_id=int(target["id"]),
                warnings=st.session_state.get("quick_analysis_warnings") or [],
            )
            if save_result.get("success"):
                clear_portfolio_analysis_cache()
                st.success(f"AssetOS에 {save_result['imported_count']:,}개 자산을 저장했습니다.")
            else:
                for error in save_result.get("errors", []):
                    st.error(error)

    export_columns = st.columns(3)
    export_columns[0].download_button(
        "Export PDF",
        data=exports["pdf"],
        file_name=f"AssetOS_Quick_Analysis_{datetime.now().astimezone():%Y%m%d}.pdf",
        mime="application/pdf",
        width="stretch",
    )
    export_columns[1].download_button(
        "Export PNG",
        data=exports["png"],
        file_name=f"AssetOS_Quick_Analysis_{datetime.now().astimezone():%Y%m%d}.png",
        mime="image/png",
        width="stretch",
    )
    export_columns[2].download_button(
        "Export JSON",
        data=exports["json"],
        file_name=f"AssetOS_Quick_Analysis_{datetime.now().astimezone():%Y%m%d}.json",
        mime="application/json",
        width="stretch",
    )
    st.success("분석이 완료되었습니다. 필요한 형식으로 결과를 내려받으세요.")

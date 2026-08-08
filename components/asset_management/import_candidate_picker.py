from __future__ import annotations

import html
from typing import Any

import pandas as pd
import streamlit as st

from services.asset_resolver import ResolvedAsset, learn_asset_alias
from services.smart_import_service import (
    SmartImportResolution,
    apply_manual_ticker,
    apply_resolution_candidate,
    build_import_error_report,
    build_resolution_table,
    candidate_label,
    resolution_state,
    resolution_summary,
)
from ui.common.formatters import format_asset_type

MANUAL_OPTION = "✏ 직접 입력..."


def build_ticker_dropdown_options(
    candidates: tuple[Any, ...],
) -> list[Any]:
    """Preserve every resolver candidate and append manual input last."""
    return [None, *candidates, MANUAL_OPTION]


def render_candidate_pickers(
    source_rows: list[dict[str, Any]],
    results: list[SmartImportResolution],
    *,
    key_prefix: str,
    source_dataframe: pd.DataFrame | None = None,
) -> list[SmartImportResolution]:
    """Render one compact resolution table and apply explicit ticker choices."""
    selected_results = list(results)
    selection_key = f"{key_prefix}_selections"
    manual_key = f"{key_prefix}_manual_tickers"
    manual_mode_key = f"{key_prefix}_manual_modes"
    selections = dict(st.session_state.get(selection_key, {}))
    manual_tickers = dict(st.session_state.get(manual_key, {}))
    manual_modes = dict(st.session_state.get(manual_mode_key, {}))
    for index, result in enumerate(results):
        row_number = int(source_rows[index].get("_excel_row_number") or index + 2)
        selected_value = selections.get(row_number, {})
        selected_ticker = (
            selected_value.get("ticker")
            if isinstance(selected_value, dict) else selected_value
        )
        selected_exchange = (
            selected_value.get("exchange", "")
            if isinstance(selected_value, dict) else ""
        )
        candidate = next(
            (
                item for item in result.candidates
                if item.ticker == selected_ticker
                and (not selected_exchange or item.exchange == selected_exchange)
            ),
            None,
        )
        if candidate is not None:
            selected_results[index] = apply_resolution_candidate(source_rows[index], candidate)
        elif selected_ticker:
            selected_results[index] = apply_manual_ticker(
                source_rows[index], str(selected_ticker)
            )
        elif manual_tickers.get(row_number):
            selected_results[index] = apply_manual_ticker(
                source_rows[index], manual_tickers[row_number]
            )

    summary = resolution_summary(selected_results)
    summary_columns = st.columns(5)
    for column, (label, value) in zip(summary_columns, summary.items()):
        column.metric(label, value)

    st.caption("Status: 🟢 Auto · 🟡 Select · ⚪ Skip · 🔴 Fail")

    status_filter = st.selectbox(
        "Status filter",
        ["All", "Auto", "Select", "Skip", "Fail"],
        key=f"{key_prefix}_filter",
    )
    table = build_resolution_table(source_rows, selected_results)
    if status_filter != "All":
        marker = {
            "Auto": "🟢 Auto", "Select": "🟡 Select",
            "Skip": "⚪ Skip", "Fail": "🔴 Fail",
        }[status_filter]
        table = table.loc[table["Status"] == marker].copy()

    st.markdown(
        """
        <style>
        [data-testid="stHorizontalBlock"] {gap: 0.35rem;}
        [data-testid="stSelectbox"] div, [data-testid="stTextInput"] input {
            font-size: 0.86rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
        }
        [data-baseweb="popover"] [role="option"] {white-space: nowrap !important;
            overflow: hidden; text-overflow: ellipsis; font-size: 0.86rem;}
        .assetos-import-cell {font-size: 0.86rem; padding: 0.32rem 0.15rem;
            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}
        </style>
        """,
        unsafe_allow_html=True,
    )
    header = st.columns([0.45, 1.0, 2.0, 3.8, 0.9])
    for column, label in zip(header, ["Row", "Type", "Asset", "Ticker", "Status"]):
        column.markdown(f"**{label}**")

    visible_rows = set(table["Row"].astype(int).tolist())
    changed = False
    for index, (source, result) in enumerate(zip(source_rows, selected_results)):
        row_number = int(source.get("_excel_row_number") or index + 2)
        if row_number not in visible_rows:
            continue
        row = build_resolution_table([source], [result]).iloc[0]
        columns = st.columns([0.45, 1.0, 2.0, 3.8, 0.9], vertical_alignment="center")
        columns[0].markdown(f'<div class="assetos-import-cell">{row_number}</div>', unsafe_allow_html=True)
        columns[1].markdown(
            f'<div class="assetos-import-cell">'
            f'{html.escape(format_asset_type(row["Type"]))}</div>',
            unsafe_allow_html=True,
        )
        columns[2].markdown(
            f'<div class="assetos-import-cell">{html.escape(str(row["Asset"]))}</div>',
            unsafe_allow_html=True,
        )
        state = resolution_state(result)
        if state in {"needs_selection", "failed"}:
            chosen_candidate = None
            candidates = tuple(result.candidates)
            selected = columns[3].selectbox(
                "Ticker candidates",
                options=build_ticker_dropdown_options(candidates),
                index=0,
                format_func=lambda option, values=candidates: (
                    "Select ticker"
                    if option is None
                    else option
                    if option == MANUAL_OPTION
                    else candidate_label(option, values)
                ),
                key=f"{key_prefix}_ticker_{row_number}",
                label_visibility="collapsed",
            )
            if isinstance(selected, str) and selected == MANUAL_OPTION:
                manual_modes[row_number] = True
            elif selected is not None:
                manual_modes[row_number] = False
                chosen_candidate = selected

            manual = ""
            if manual_modes.get(row_number):
                manual = columns[3].text_input(
                    "Manual input",
                    value=str(manual_tickers.get(row_number) or ""),
                    placeholder="Ticker or company name",
                    key=f"{key_prefix}_manual_{row_number}",
                    label_visibility="collapsed",
                ).strip()
                if manual_tickers.get(row_number) != manual:
                    manual_tickers[row_number] = manual
                    changed = True

            if isinstance(chosen_candidate, ResolvedAsset):
                value = {
                    "ticker": chosen_candidate.ticker,
                    "exchange": chosen_candidate.exchange,
                }
                if selections.get(row_number) != value:
                    selections[row_number] = value
                    changed = True
                    learn_asset_alias(
                        str(source.get("asset_name") or ""), chosen_candidate.ticker
                    )
                selected_results[index] = apply_resolution_candidate(source, chosen_candidate)
            elif manual:
                selected_results[index] = apply_manual_ticker(source, manual)
                if resolution_state(selected_results[index]) == "resolved":
                    resolved_ticker = str(selected_results[index].row.get("symbol") or "")
                    value = {"ticker": resolved_ticker, "exchange": ""}
                    if selections.get(row_number) != value:
                        selections[row_number] = value
                        changed = True
                        learn_asset_alias(str(source.get("asset_name") or ""), resolved_ticker)
            elif row_number in selections:
                selections.pop(row_number, None)
                changed = True
        else:
            columns[3].markdown(
                f'<div class="assetos-import-cell">{html.escape(str(row["Ticker"] or "—"))}</div>',
                unsafe_allow_html=True,
            )
        row = build_resolution_table([source], [selected_results[index]]).iloc[0]
        columns[4].markdown(
            f'<div class="assetos-import-cell">{row["Status"]}</div>', unsafe_allow_html=True
        )
    if changed:
        st.session_state[selection_key] = selections
        st.session_state[manual_key] = manual_tickers
        st.session_state[manual_mode_key] = manual_modes

    if source_dataframe is not None:
        st.download_button(
            "Download Error Report",
            data=build_import_error_report(
                source_dataframe, source_rows, selected_results
            ),
            file_name="Import_Error.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"{key_prefix}_error_report",
        )
    return selected_results

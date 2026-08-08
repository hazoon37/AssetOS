from __future__ import annotations

from datetime import datetime

import streamlit as st

from database.db import get_accounts
from models.account import ACCOUNT_TYPES
from models.preferences import SUPPORTED_BASE_CURRENCIES, SUPPORTED_THEMES, UserPreferences
from services.portfolio_service import clear_portfolio_analysis_cache
from services.settings_service import (
    create_investment_account,
    export_database_backup,
    get_user_preferences,
    restore_database_backup,
    update_user_preferences,
)


def load_preferences() -> UserPreferences:
    preferences = get_user_preferences()
    st.session_state["assetos_base_currency"] = preferences.base_currency
    st.session_state["assetos_theme"] = preferences.theme
    return preferences


def render_settings_panel(preferences: UserPreferences) -> None:
    with st.sidebar.expander("⚙️ 설정", expanded=False):
        with st.form("assetos_preferences_form"):
            base_currency = st.selectbox(
                "기준통화",
                SUPPORTED_BASE_CURRENCIES,
                index=SUPPORTED_BASE_CURRENCIES.index(preferences.base_currency),
            )
            theme = st.selectbox(
                "테마",
                SUPPORTED_THEMES,
                index=SUPPORTED_THEMES.index(preferences.theme),
            )
            if st.form_submit_button("환경설정 저장", width="stretch"):
                updated = update_user_preferences(base_currency, theme)
                st.session_state["assetos_base_currency"] = updated.base_currency
                st.session_state["assetos_theme"] = updated.theme
                st.success("환경설정을 저장했습니다.")
                st.rerun()

        st.divider()
        st.markdown("##### 투자계정")
        accounts = get_accounts()
        for account in accounts.to_dict(orient="records"):
            st.caption(f"{account['account_name']} · {account['account_type']}")
        with st.form("assetos_account_form", clear_on_submit=True):
            account_name = st.text_input("새 계정 이름", max_chars=80)
            account_type = st.selectbox("계정 유형", ACCOUNT_TYPES)
            if st.form_submit_button("계정 추가", width="stretch"):
                try:
                    create_investment_account(account_name, account_type)
                except ValueError as error:
                    st.error(str(error))
                else:
                    st.success("투자계정을 추가했습니다.")
                    st.rerun()

        st.divider()
        st.markdown("##### 백업 및 복구")
        if st.button("백업 파일 생성", width="stretch"):
            st.session_state["assetos_backup_bytes"] = export_database_backup()
            st.session_state["assetos_backup_name"] = (
                f"AssetOS_Backup_{datetime.now():%Y%m%d_%H%M%S}.db"
            )
        backup_bytes = st.session_state.get("assetos_backup_bytes")
        if backup_bytes:
            st.download_button(
                "백업 다운로드",
                data=backup_bytes,
                file_name=st.session_state["assetos_backup_name"],
                mime="application/vnd.sqlite3",
                width="stretch",
            )

        restore_file = st.file_uploader(
            "AssetOS 백업 파일",
            type=["db", "sqlite", "sqlite3"],
            key="assetos_restore_file",
        )
        restore_confirmed = st.checkbox(
            "현재 DB를 안전 백업한 뒤 업로드 파일로 복구합니다.",
            disabled=restore_file is None,
            key="assetos_restore_confirmed",
        )
        if st.button(
            "백업 복구",
            disabled=restore_file is None or not restore_confirmed,
            width="stretch",
        ):
            try:
                restore_database_backup(restore_file.getvalue())
            except ValueError as error:
                st.error(str(error))
            else:
                clear_portfolio_analysis_cache()
                for key in (
                    "assetos_backup_bytes",
                    "assetos_restore_confirmed",
                    "dashboard_account_filter",
                ):
                    st.session_state.pop(key, None)
                st.success("백업을 검증하고 복구했습니다.")
                st.rerun()

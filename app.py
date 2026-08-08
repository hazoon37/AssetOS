import streamlit as st

from components.quick_analysis_panel import render_quick_analysis_panel
from components.settings_panel import load_preferences, render_settings_panel
from services.auth import current_google_user, login_with_google, logout_google
from services.auth.user_service import UserService
from services.local_user_service import get_browser_local_user_id, initialize_local_user

st.set_page_config(
    page_title="AssetOS",
    page_icon="📊",
    layout="wide",
)

local_user_id = get_browser_local_user_id()
if local_user_id is None:
    st.markdown("## AssetOS")
    st.markdown("내 자산을 불러오는 중...")
    st.caption("✓ 자산 데이터 확인")
    st.caption("✓ 현재가 업데이트")
    st.caption("✓ 포트폴리오 준비")
    st.caption("잠시만 기다려주세요...")
    st.stop()
initialize_local_user(local_user_id)
st.session_state["assetos_user_id"] = local_user_id


def render_login_screen() -> None:
    st.markdown("# AssetOS")
    st.markdown("자산을 한눈에 보고, 더 나은 투자 결정을 시작하세요.")
    google_column, guest_column, developer_column = st.columns(3)
    with google_column:
        if st.button("Google로 로그인", type="primary", width="stretch"):
            try:
                login_with_google()
            except RuntimeError as error:
                st.error(str(error))
    with guest_column:
        if st.button("체험하기", width="stretch"):
            UserService().start_guest()
            st.rerun()
    with developer_column:
        if st.button("Developer Login", width="stretch"):
            UserService().start_developer(local_user_id)
            st.rerun()


user_service = UserService()
authenticated_user = current_google_user(user_service) or user_service.current()
if authenticated_user is None:
    render_login_screen()
    st.stop()

preferences = load_preferences()


def render_auth_sidebar() -> None:
    user = authenticated_user
    with st.sidebar:
        if user.avatar_url:
            st.image(user.avatar_url, width=48)
        else:
            st.markdown("### 👤")
        st.markdown(f"**{user.name}**")
        st.caption(user.email)
        if st.button("로그아웃", width="stretch"):
            logout_google()


render_auth_sidebar()
render_settings_panel(preferences)


@st.dialog("📄 Quick Analysis", width="large")
def open_quick_analysis() -> None:
    render_quick_analysis_panel()


with st.sidebar:
    if st.button("📄 Quick Analysis", type="primary", width="stretch"):
        open_quick_analysis()

navigation = st.navigation(
    [
        st.Page("pages/1_총_자산_현황.py", title="🏠 총 자산 현황", default=True),
        st.Page("pages/2_포트폴리오_분석.py", title="📊 포트폴리오 분석"),
        st.Page("pages/3_종목_분석.py", title="🔎 종목 분석"),
    ]
)
navigation.run()

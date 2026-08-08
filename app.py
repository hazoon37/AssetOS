import streamlit as st

from components.quick_analysis_panel import render_quick_analysis_panel
from components.settings_panel import load_preferences, render_settings_panel
from services.auth import (
    AuthenticatedUser,
    current_google_user,
    login_as_developer,
    login_as_guest,
    login_with_google,
    logout_google,
)
from services.auth.session import (
    consume_guest_fallback,
    request_guest_fallback,
)
from services.auth.user_service import UserService
from services.local_user_service import get_browser_local_user_id, initialize_local_user
from services.pilot_support_service import (
    FEEDBACK_CATEGORIES,
    get_release_info,
    install_exception_logging,
    submit_feedback,
)
from services.user_context import current_user

st.set_page_config(
    page_title="AssetOS",
    page_icon="📊",
    layout="wide",
)
install_exception_logging()

local_user_id = get_browser_local_user_id()
print(f"[STARTUP 1] local_user_id={local_user_id!r}")
if local_user_id is None:
    st.markdown("## AssetOS")
    st.markdown("내 자산을 불러오는 중...")
    st.caption("✓ 자산 데이터 확인")
    st.caption("✓ 현재가 업데이트")
    st.caption("✓ 포트폴리오 준비")
    st.caption("잠시만 기다려주세요...")
    st.stop()
assert local_user_id is not None
initialize_local_user(local_user_id)
st.session_state["assetos_user_id"] = local_user_id


def render_login_screen(developer_user_id: str) -> None:
    st.markdown("# AssetOS")
    st.markdown("자산을 한눈에 보고, 더 나은 투자 결정을 시작하세요.")
    google_column, guest_column, developer_column = st.columns(3)
    with google_column:
        if st.button("Google로 로그인", type="primary", width="stretch"):
            try:
                login_with_google()
            except RuntimeError as error:
                request_guest_fallback(str(error))
                login_as_guest()
                print("[STARTUP 7] st.rerun() executed=True")
                st.rerun()
    with guest_column:
        if st.button("체험하기", width="stretch"):
            login_as_guest()
            print("[STARTUP 7] st.rerun() executed=True")
            st.rerun()
    with developer_column:
        if st.button("Developer Login", width="stretch"):
            login_as_developer(developer_user_id)
            print("[STARTUP 7] st.rerun() executed=True")
            st.rerun()


user_service = UserService()
google_user = current_google_user(user_service)
print(f"[STARTUP 2] current_google_user()={google_user!r}")
print("[STARTUP 3] restore_browser_local_session()=NOT_CALLED")
authenticated_user = google_user
if authenticated_user is None:
    current_session_user = user_service.current()
else:
    current_session_user = authenticated_user
print(f"[STARTUP 4] user_service.current()={current_session_user!r}")
authenticated_user = current_session_user
print(f"[STARTUP 5] authenticated_user={authenticated_user!r}")
if authenticated_user is None:
    startup_branch = "LOGIN_SCREEN"
    print(f"[STARTUP 6] branch={startup_branch}")
    fallback_message = consume_guest_fallback()
    if fallback_message:
        st.info(fallback_message)
    render_login_screen(local_user_id)
    print("[STARTUP 7] st.rerun() executed=False")
    print("[STARTUP 8] navigation.run() reached=False")
    st.stop()
assert authenticated_user is not None
startup_branch = {
    "guest": "GUEST_AUTO",
    "local": "DEVELOPER",
    "google": "GOOGLE",
}.get(authenticated_user.provider.lower(), authenticated_user.provider.upper())
print(f"[STARTUP 6] branch={startup_branch}")
print("[STARTUP 7] st.rerun() executed=False")

navigation = st.navigation(
    [
        st.Page("pages/1_총_자산_현황.py", title="🏠 총 자산 현황", default=True),
        st.Page("pages/2_포트폴리오_분석.py", title="📊 포트폴리오 분석"),
        st.Page("pages/3_종목_분석.py", title="🔎 종목 분석"),
    ]
)
preferences = load_preferences()


@st.dialog("AssetOS 정보")
def open_about_dialog() -> None:
    release = get_release_info()
    st.markdown("### AssetOS")
    st.write(f"Version: {release.version}")
    st.write(f"Build: {release.build}")
    st.write(f"Git Tag: {release.git_tag}")


@st.dialog("피드백 보내기")
def open_feedback_dialog(user_id: str) -> None:
    with st.form("pilot_feedback", clear_on_submit=True):
        category = st.selectbox("유형", FEEDBACK_CATEGORIES)
        comment = st.text_area("내용", max_chars=2000)
        if st.form_submit_button("보내기", type="primary", width="stretch"):
            try:
                submit_feedback(user_id, category, comment)
                st.success("피드백이 저장되었습니다. 감사합니다.")
            except ValueError as error:
                st.warning(str(error))


def render_auth_sidebar(user: AuthenticatedUser) -> None:
    with st.sidebar:
        provider = user.provider.lower()
        account_label = {
            "guest": "Guest",
            "local": "Developer",
            "google": "Google",
        }.get(provider, user.provider.title())
        st.caption("Current User")
        st.markdown(f"**{account_label}**")
        if user.avatar_url:
            st.image(user.avatar_url, width=48)
        display_name = user.name or user.email or "Guest"
        st.markdown(f"**👤 {display_name}**")
        st.caption(user.email)
        about_column, feedback_column = st.columns(2)
        with about_column:
            if st.button("정보", width="stretch"):
                open_about_dialog()
        with feedback_column:
            if st.button("피드백", width="stretch"):
                open_feedback_dialog(current_user().id)
        if st.button("로그아웃", width="stretch"):
            logout_google()


render_auth_sidebar(authenticated_user)
render_settings_panel(preferences)


@st.dialog("📄 Quick Analysis", width="large")
def open_quick_analysis() -> None:
    render_quick_analysis_panel()


with st.sidebar:
    if st.button("📄 Quick Analysis", type="primary", width="stretch"):
        open_quick_analysis()

print("[STARTUP 8] navigation.run() reached=True")
navigation.run()

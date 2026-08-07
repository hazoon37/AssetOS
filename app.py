import streamlit as st

st.set_page_config(
    page_title="AssetOS",
    page_icon="📊",
    layout="wide",
)

navigation = st.navigation(
    [
        st.Page("pages/1_총_자산_현황.py", title="총 자산 현황", icon="📊", default=True),
        st.Page("pages/2_포트폴리오_분석.py", title="포트폴리오 분석", icon="💼"),
        st.Page("pages/3_종목_분석.py", title="종목 분석", icon="🔍"),
    ]
)
navigation.run()

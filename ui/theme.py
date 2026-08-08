from __future__ import annotations

import streamlit as st

LIGHT_COLORS = {
    "background": "#F4F7FB",
    "surface": "#FFFFFF",
    "surface_alt": "#F8FAFC",
    "border": "#E2E8F0",
    "text": "#0F172A",
    "muted": "#64748B",
    "primary": "#2563EB",
    "success": "#15803D",
    "danger": "#DC2626",
    "warning": "#D97706",
}

DARK_COLORS = {
    "background": "#0B1220",
    "surface": "#111827",
    "surface_alt": "#172033",
    "border": "#2B364A",
    "text": "#F8FAFC",
    "muted": "#A7B2C3",
    "primary": "#60A5FA",
    "success": "#4ADE80",
    "danger": "#FB7185",
    "warning": "#FBBF24",
}

# Backward-compatible token name.
COLORS = LIGHT_COLORS

ASSET_COLORS = {
    "부동산": "#8B5E3C",
    "국내주식": "#2563EB",
    "미국주식": "#0EA5E9",
    "국내ETF": "#16A34A",
    "미국ETF": "#059669",
    "현금·예금": "#94A3B8",
    "코인": "#F59E0B",
    "연금": "#7C3AED",
    "기타": "#64748B",
}


def apply_theme() -> None:
    """Apply a lightweight, shared AssetOS visual theme."""

    selected_theme = str(st.session_state.get("assetos_theme") or "System")
    colors = DARK_COLORS if selected_theme == "Dark" else LIGHT_COLORS
    system_dark_css = ""
    if selected_theme == "System":
        system_dark_css = f"""
        @media (prefers-color-scheme: dark) {{
            :root {{
                --assetos-bg: {DARK_COLORS['background']};
                --assetos-surface: {DARK_COLORS['surface']};
                --assetos-border: {DARK_COLORS['border']};
                --assetos-text: {DARK_COLORS['text']};
                --assetos-muted: {DARK_COLORS['muted']};
                --assetos-primary: {DARK_COLORS['primary']};
                --assetos-success: {DARK_COLORS['success']};
                --assetos-danger: {DARK_COLORS['danger']};
            }}
        }}
        """

    st.markdown(
        f"""
        <style>
        :root {{
            --assetos-bg: {colors['background']};
            --assetos-surface: {colors['surface']};
            --assetos-border: {colors['border']};
            --assetos-text: {colors['text']};
            --assetos-muted: {colors['muted']};
            --assetos-primary: {colors['primary']};
            --assetos-success: {colors['success']};
            --assetos-danger: {colors['danger']};
        }}

        {system_dark_css}

        .stApp {{
            background: var(--assetos-bg);
        }}

        .block-container {{
            max-width: 1480px;
            padding-top: 1.35rem;
            padding-bottom: 3rem;
        }}

        h1, h2, h3 {{
            color: var(--assetos-text);
            letter-spacing: -0.025em;
        }}

        .stApp, .stApp p, .stApp label {{
            color: var(--assetos-text);
        }}

        .assetos-page-header {{
            display: flex;
            align-items: flex-end;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1.15rem;
        }}

        .assetos-eyebrow {{
            color: var(--assetos-primary);
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            margin-bottom: 0.25rem;
        }}

        .assetos-page-title {{
            color: var(--assetos-text);
            font-size: 2rem;
            line-height: 1.15;
            font-weight: 800;
            margin: 0;
        }}

        .assetos-page-subtitle {{
            color: var(--assetos-muted);
            font-size: 0.94rem;
            margin-top: 0.45rem;
        }}

        .assetos-card {{
            background: var(--assetos-surface);
            border: 1px solid var(--assetos-border);
            border-radius: 16px;
            padding: 1.05rem 1.1rem;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.045);
            min-height: 132px;
            height: 100%;
            box-sizing: border-box;
        }}

        .assetos-kpi-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 1.15rem;
            margin: 1.25rem 0 1.75rem;
        }}

        .assetos-metric-label {{
            color: var(--assetos-muted);
            font-size: 0.82rem;
            font-weight: 700;
            margin-bottom: 0.42rem;
        }}

        .assetos-metric-value {{
            color: var(--assetos-text);
            font-size: clamp(1.44rem, 2.05vw, 2.05rem);
            font-weight: 800;
            line-height: 1.15;
            letter-spacing: -0.035em;
        }}

        .assetos-metric-note {{
            color: var(--assetos-muted);
            font-size: 0.78rem;
            margin-top: 0.42rem;
        }}

        .assetos-positive {{ color: var(--assetos-success); }}
        .assetos-negative {{ color: var(--assetos-danger); }}
        .assetos-neutral {{ color: var(--assetos-muted); }}

        .assetos-section-title {{
            color: var(--assetos-text);
            font-size: 1.08rem;
            font-weight: 800;
            margin: 0.25rem 0 0.7rem;
        }}

        div[data-testid="stPlotlyChart"],
        div[data-testid="stDataFrame"],
        div[data-testid="stExpander"] {{
            background: var(--assetos-surface);
            border: 1px solid var(--assetos-border);
            border-radius: 16px;
            overflow: hidden;
        }}

        div[data-testid="stDataFrame"] {{
            padding: 0.25rem;
        }}
        
        div[data-testid="stDataFrame"] div[role="gridcell"] {{
            font-size: 13px !important;
        }}

        div[data-testid="stDataFrame"] div[role="columnheader"] {{
            font-size: 13px !important;
        }}

        div[data-testid="stButton"] > button {{
            border-radius: 10px;
            min-height: 2.55rem;
            font-weight: 700;
        }}

        div[role="radiogroup"] {{
            background: var(--assetos-surface);
            border: 1px solid var(--assetos-border);
            border-radius: 12px;
            padding: 0.22rem 0.5rem;
            width: fit-content;
        }}

        [data-testid="stSidebar"] {{
            border-right: 1px solid var(--assetos-border);
            background: var(--assetos-surface);
        }}

        hr {{
            border-color: var(--assetos-border) !important;
            margin: 1.25rem 0 !important;
        }}

        @media (max-width: 1024px) {{
            .assetos-kpi-grid {{
                grid-template-columns: repeat(2, minmax(0, 1fr));
            }}
            .block-container {{
                padding-left: 1.25rem;
                padding-right: 1.25rem;
            }}
        }}

        @media (max-width: 640px) {{
            .assetos-kpi-grid {{
                grid-template-columns: 1fr;
                gap: 0.8rem;
            }}
            .assetos-card {{ min-height: 116px; }}
            .assetos-page-title {{ font-size: 1.65rem; }}
            .block-container {{
                padding-left: 0.8rem;
                padding-right: 0.8rem;
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def theme_text_color() -> str:
    return (
        DARK_COLORS["text"]
        if st.session_state.get("assetos_theme") == "Dark"
        else LIGHT_COLORS["text"]
    )

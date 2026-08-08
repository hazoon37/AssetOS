from __future__ import annotations

import html

import streamlit as st

from services.portfolio_ai_service import PortfolioAIDiagnosis
from ui.components.metric_card import render_metric_grid


def _render_list_card(title: str, icon: str, items: tuple[str, ...]) -> None:
    entries = "".join(f"<li>{html.escape(item)}</li>" for item in items)
    st.markdown(
        '<div class="assetos-card">'
        f'<div class="assetos-section-title">{icon} {html.escape(title)}</div>'
        f'<ul class="assetos-page-subtitle">{entries}</ul>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_ai_advisor_diagnosis(diagnosis: PortfolioAIDiagnosis) -> None:
    """Render diagnosis metrics and rule cards with the shared AssetOS theme."""
    metrics = diagnosis.metrics
    render_metric_grid([
        {"label": "Portfolio Score", "value": f"{metrics.portfolio_score:.1f}", "note": "0~100"},
        {"label": "Diversification Score", "value": f"{metrics.diversification_score:.1f}", "note": "높을수록 분산"},
        {"label": "Risk Score", "value": f"{metrics.risk_score:.1f}", "note": "높을수록 위험관리 양호"},
        {"label": "Cash Ratio", "value": f"{metrics.cash_ratio:.1%}"},
        {"label": "US Ratio", "value": f"{metrics.us_ratio:.1%}"},
        {"label": "KR Ratio", "value": f"{metrics.kr_ratio:.1%}"},
        {"label": "ETF Ratio", "value": f"{metrics.etf_ratio:.1%}"},
        {"label": "Stock Ratio", "value": f"{metrics.stock_ratio:.1%}"},
        {"label": "Crypto Ratio", "value": f"{metrics.crypto_ratio:.1%}"},
        {"label": "Real Estate Ratio", "value": f"{metrics.real_estate_ratio:.1%}"},
    ])
    columns = st.columns(3)
    with columns[0]:
        _render_list_card("장점", "✅", diagnosis.strengths)
    with columns[1]:
        _render_list_card("리스크", "⚠️", diagnosis.combined_risks)
    with columns[2]:
        _render_list_card("추천사항", "💡", diagnosis.recommendations)


def render_ai_advisor_summary(diagnosis: PortfolioAIDiagnosis) -> None:
    """Render the compact dashboard advisor with the existing card theme."""
    sections = (
        ("장점", diagnosis.top_strengths),
        ("리스크", diagnosis.top_risks),
        ("추천", diagnosis.recommended_actions),
    )
    body = "".join(
        f"<strong>{html.escape(title)}</strong><ul>"
        + "".join(f"<li>{html.escape(item)}</li>" for item in items)
        + "</ul>"
        for title, items in sections
    )
    st.markdown(
        '<div class="assetos-card">'
        '<div class="assetos-section-title">🤖 AI Portfolio Advisor</div>'
        f'<div class="assetos-page-subtitle"><strong>Portfolio Score</strong> '
        f'{diagnosis.overall_score:.1f}/100 · <strong>Risk</strong> '
        f'{html.escape(diagnosis.risk_level)}</div>{body}</div>',
        unsafe_allow_html=True,
    )

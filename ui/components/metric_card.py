from __future__ import annotations

import html

import streamlit as st


def _metric_card_html(
    label: str,
    value: str,
    note: str = "",
    tone: str = "neutral",
) -> str:
    tone_class = {
        "positive": "assetos-positive",
        "negative": "assetos-negative",
        "neutral": "assetos-neutral",
    }.get(tone, "assetos-neutral")
    note_html = (
        f'<div class="assetos-metric-note {tone_class}">{html.escape(note)}</div>'
        if note
        else ""
    )
    return (
        '<div class="assetos-card">'
        f'<div class="assetos-metric-label">{html.escape(label)}</div>'
        f'<div class="assetos-metric-value">{html.escape(value)}</div>'
        f'{note_html}</div>'
    )


def render_metric_card(
    label: str,
    value: str,
    *,
    note: str = "",
    tone: str = "neutral",
) -> None:
    """Render a compact metric card without external UI dependencies."""

    st.markdown(
        _metric_card_html(label, value, note, tone),
        unsafe_allow_html=True,
    )


def render_metric_grid(metrics: list[dict[str, str]]) -> None:
    """Render KPI cards in a responsive 4/2/1-column grid."""
    cards = "".join(
        _metric_card_html(
            metric["label"],
            metric["value"],
            metric.get("note", ""),
            metric.get("tone", "neutral"),
        )
        for metric in metrics
    )
    st.markdown(f'<div class="assetos-kpi-grid">{cards}</div>', unsafe_allow_html=True)


def render_ai_card(title: str, text: str) -> None:
    """Render a shared insight card with safely escaped content."""
    st.markdown(
        '<div class="assetos-card">'
        f'<div class="assetos-section-title">{html.escape(title)}</div>'
        f'<div class="assetos-page-subtitle">{html.escape(text)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


def render_page_header(title: str, subtitle: str, eyebrow: str = "AssetOS") -> None:
    """Render the standard AssetOS page header."""

    st.markdown(
        f"""
        <div class="assetos-page-header">
            <div>
                <div class="assetos-eyebrow">{html.escape(eyebrow)}</div>
                <h1 class="assetos-page-title">{html.escape(title)}</h1>
                <div class="assetos-page-subtitle">{html.escape(subtitle)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

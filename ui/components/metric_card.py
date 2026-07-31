from __future__ import annotations

import html

import streamlit as st


def render_metric_card(
    label: str,
    value: str,
    *,
    note: str = "",
    tone: str = "neutral",
) -> None:
    """Render a compact metric card without external UI dependencies."""

    tone_class = {
        "positive": "assetos-positive",
        "negative": "assetos-negative",
        "neutral": "assetos-neutral",
    }.get(tone, "assetos-neutral")

    safe_label = html.escape(label)
    safe_value = html.escape(value)
    safe_note = html.escape(note)

    note_html = (
        f'<div class="assetos-metric-note {tone_class}">{safe_note}</div>'
        if safe_note
        else ""
    )

    st.markdown(
        f"""
        <div class="assetos-card">
            <div class="assetos-metric-label">{safe_label}</div>
            <div class="assetos-metric-value">{safe_value}</div>
            {note_html}
        </div>
        """,
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

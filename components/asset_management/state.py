from __future__ import annotations

import streamlit as st

EDIT_KEY = "inline_edit_asset_id"
DELETE_KEY = "inline_delete_asset_id"


def clear_action_state() -> None:
    st.session_state.pop(EDIT_KEY, None)
    st.session_state.pop(DELETE_KEY, None)


def open_edit(asset_id: int) -> None:
    st.session_state[EDIT_KEY] = int(asset_id)
    st.session_state.pop(DELETE_KEY, None)


def open_delete(asset_id: int) -> None:
    st.session_state[DELETE_KEY] = int(asset_id)
    st.session_state.pop(EDIT_KEY, None)


def is_editing(asset_id: int) -> bool:
    return st.session_state.get(EDIT_KEY) == int(asset_id)


def is_deleting(asset_id: int) -> bool:
    return st.session_state.get(DELETE_KEY) == int(asset_id)

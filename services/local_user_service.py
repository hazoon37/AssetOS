from __future__ import annotations

import re
from uuid import UUID, uuid4

import streamlit as st
import streamlit.components.v2 as components_v2

from repositories import get_asset_repository
from repositories.asset_repository import AssetRepository
from repositories.sqlite_asset_repository import DEFAULT_USER_ID
from services.user_context import CurrentUser, set_current_user

LOCAL_USER_PREFIX = "local:"
LOCAL_STORAGE_KEY = "assetos.local_user_id"
_UUID_PATTERN = re.compile(
    r"^local:[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)


def generate_local_user_id() -> str:
    return f"{LOCAL_USER_PREFIX}{uuid4()}"


def is_valid_local_user_id(user_id: object) -> bool:
    value = str(user_id or "").strip().lower()
    if not _UUID_PATTERN.fullmatch(value):
        return False
    try:
        UUID(value.removeprefix(LOCAL_USER_PREFIX))
        return True
    except ValueError:
        return False


_LOCAL_USER_COMPONENT = components_v2.component(
    "assetos_local_user",
    js="""
    export default function(component) {
        const { data, setStateValue } = component;
        let value = window.localStorage.getItem(data.storageKey);
        const pattern = new RegExp(data.pattern);
        if (!pattern.test(value || '')) {
            value = data.candidate;
            window.localStorage.setItem(data.storageKey, value);
        }
        if (data.currentValue !== value) {
            setStateValue('user_id', value);
        }
    }
    """,
)


def get_browser_local_user_id() -> str | None:
    """Read or create the stable browser UUID through localStorage."""
    candidate = st.session_state.setdefault("assetos_local_user_candidate", generate_local_user_id())
    component_state = st.session_state.get("assetos_local_user_component", {})
    current_value = component_state.get("user_id") if isinstance(component_state, dict) else None
    result = _LOCAL_USER_COMPONENT(
        data={
            "storageKey": LOCAL_STORAGE_KEY,
            "candidate": candidate,
            "pattern": _UUID_PATTERN.pattern,
            "currentValue": current_value,
        },
        default={"user_id": None},
        on_user_id_change=lambda: None,
        key="assetos_local_user_component",
        height=0,
    )
    return str(result.user_id) if is_valid_local_user_id(result.user_id) else None


def initialize_local_user(
    user_id: str,
    repository: AssetRepository | None = None,
) -> str:
    """Provision the browser user and claim legacy default_user data once."""
    if not is_valid_local_user_id(user_id):
        raise ValueError("올바르지 않은 로컬 사용자 ID입니다.")
    target = repository or get_asset_repository()
    suffix = user_id.removeprefix(LOCAL_USER_PREFIX)
    user = target.ensure_user(user_id, f"{suffix}@local.assetos", "Local User")
    target.migrate_user_scope(DEFAULT_USER_ID, user_id)
    set_current_user(CurrentUser(user.id, user.name, user.email))
    return user_id

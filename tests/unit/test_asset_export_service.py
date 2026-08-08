from __future__ import annotations

import json

import pandas as pd

from services.asset_export_service import export_assets_json


def test_json_export_is_versioned_and_handles_missing_values() -> None:
    payload = json.loads(
        export_assets_json(pd.DataFrame([{"id": 1, "asset_name": "Apple", "memo": float("nan")}]))
    )
    assert payload["format"] == "AssetOS Assets"
    assert payload["schema_version"] == 1
    assert payload["asset_count"] == 1
    assert payload["assets"][0]["memo"] is None

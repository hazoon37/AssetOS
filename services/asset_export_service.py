from __future__ import annotations

import json
import math
from datetime import date, datetime
from typing import Any

import pandas as pd


def _json_value(value: Any) -> Any:
    """Convert pandas and SQLite values into portable JSON values."""
    if value is None or value is pd.NA:
        return None
    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (datetime, date, pd.Timestamp)):
        return value.isoformat()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    item_method = getattr(value, "item", None)
    if callable(item_method):
        return item_method()
    return value


def export_assets_json(assets: pd.DataFrame) -> bytes:
    """Export user-owned asset records as a versioned UTF-8 JSON document."""
    records = [
        {str(key): _json_value(value) for key, value in row.items()}
        for row in assets.to_dict(orient="records")
    ]
    document = {
        "format": "AssetOS Assets",
        "schema_version": 1,
        "exported_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "asset_count": len(records),
        "assets": records,
    }
    return json.dumps(document, ensure_ascii=False, indent=2).encode("utf-8")

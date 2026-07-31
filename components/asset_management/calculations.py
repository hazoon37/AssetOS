from __future__ import annotations

import pandas as pd

from services.exchange_rate_service import convert_to_krw


def calculate_assets(
    assets_df: pd.DataFrame,
    exchange_rates: dict[str, float],
) -> pd.DataFrame:
    """Add portfolio calculations without rendering any UI."""
    df = assets_df.copy()
    for column in ["quantity", "average_price", "current_price"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0)

    df["매입금액"] = df["quantity"] * df["average_price"]
    df["평가금액"] = df["quantity"] * df["current_price"]
    df["평가손익"] = df["평가금액"] - df["매입금액"]
    df["수익률"] = 0.0
    valid = df["매입금액"] > 0
    df.loc[valid, "수익률"] = (
        df.loc[valid, "평가손익"] / df.loc[valid, "매입금액"] * 100
    )

    df["원화 매입금액"] = df.apply(
        lambda row: convert_to_krw(
            float(row["매입금액"]), str(row["currency"]), exchange_rates
        ),
        axis=1,
    )
    df["원화 평가금액"] = df.apply(
        lambda row: convert_to_krw(
            float(row["평가금액"]), str(row["currency"]), exchange_rates
        ),
        axis=1,
    )
    df["원화 평가손익"] = df["원화 평가금액"] - df["원화 매입금액"]
    return df


def calculate_summary(df: pd.DataFrame) -> dict[str, float]:
    valid = df.dropna(subset=["원화 매입금액", "원화 평가금액"])
    purchase = float(valid["원화 매입금액"].sum())
    value = float(valid["원화 평가금액"].sum())
    profit = value - purchase
    return_rate = profit / purchase * 100 if purchase > 0 else 0.0
    return {
        "purchase": purchase,
        "value": value,
        "profit": profit,
        "return_rate": return_rate,
    }

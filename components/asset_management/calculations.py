from __future__ import annotations

import pandas as pd

from services.portfolio_service import calculate_asset_values


def calculate_assets(
    assets_df: pd.DataFrame,
    exchange_rates: dict[str, float],
) -> pd.DataFrame:
    """Add portfolio calculations without rendering any UI."""
    df = assets_df.copy()
    for column in ["quantity", "average_price", "current_price"]:
        source = pd.Series(df[column], index=df.index)
        numeric = pd.Series(pd.to_numeric(source, errors="coerce"), index=df.index)
        df[column] = numeric.fillna(0.0)

    calculated = df.apply(
        lambda row: calculate_asset_values(
            row["quantity"], row["average_price"], row["current_price"],
            str(row["currency"]), exchange_rates,
        ),
        axis=1,
    )
    df["매입금액"] = df["quantity"] * df["average_price"]
    df["평가금액"] = df["quantity"] * df["current_price"]
    df["평가손익"] = df["평가금액"] - df["매입금액"]
    df["원화 매입금액"] = calculated.map(
        lambda values: values["cost_value_krw"] if values else float("nan")
    )
    df["원화 평가금액"] = calculated.map(
        lambda values: values["value_krw"] if values else float("nan")
    )
    df["원화 평가손익"] = calculated.map(
        lambda values: values["profit_loss_krw"] if values else float("nan")
    )
    df["수익률"] = calculated.map(
        lambda values: values["return_rate_percent"] if values else 0.0
    )
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

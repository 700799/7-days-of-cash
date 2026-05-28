"""Configurable vectorized filters operating on the metric DataFrame."""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd


def apply_filters(records: List[Dict[str, Any]], config: Dict[str, Any]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame()

    df = pd.DataFrame(records)
    active = config.get("active_filters", set())
    if not active:
        active = {
            "min_price",
            "min_gain_7d",
            "min_avg_volume",
            "max_rsi",
            "market_cap",
            "exclude_volatility",
            "min_dollar_vol",
        }

    mask = pd.Series([True] * len(df), index=df.index)

    if "min_price" in active:
        mask &= df["price"] >= config.get("min_price", 2.0)

    if "min_gain_7d" in active:
        mask &= df["change_7d"] >= config.get("min_gain_7d", 8.0)

    if "min_avg_volume" in active:
        mask &= df["avg_vol_20d"] >= config.get("min_avg_volume", 500_000)

    if "max_rsi" in active:
        mask &= df["rsi_14"] <= config.get("max_rsi", 80)

    if "exclude_volatility" in active and config.get("exclude_extreme_volatility", True):
        mask &= df["avg_range_pct"] <= config.get("max_avg_range_pct", 50.0)

    if "min_dollar_vol" in active and "dollar_vol_20d" in df.columns:
        mask &= df["dollar_vol_20d"] >= config.get("min_dollar_vol", 5_000_000)

    if "near_52w_high" in active and "pct_from_52w_high" in df.columns:
        mask &= df["pct_from_52w_high"] >= config.get("min_pct_52w_high", -15.0)

    if "market_cap" in active:
        cap_filter = config.get("market_cap", "all")
        if cap_filter != "all" and "market_cap_val" in df.columns:
            if cap_filter == "small":
                mask &= df["market_cap_val"] < 2e9
            elif cap_filter == "mid":
                mask &= (df["market_cap_val"] >= 2e9) & (df["market_cap_val"] < 10e9)
            elif cap_filter == "large":
                mask &= df["market_cap_val"] >= 10e9

    filtered = df[mask].copy()
    sort_col = "composite_score" if "composite_score" in filtered.columns else "change_7d"
    filtered = filtered.sort_values(sort_col, ascending=False)
    top_n = config.get("top_n", 25)
    return filtered.head(top_n).reset_index(drop=True)

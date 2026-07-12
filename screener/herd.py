"""Herd/crowd dynamics: classify where the crowd is in a stock's move.

The strategy agents answer "is this attractive?"; this module answers
"is the crowd still arriving or already leaving?" — the input an add/trim
decision actually needs. Output is deliberately descriptive (states and
mechanical levels), never imperative advice.
"""

from __future__ import annotations

import statistics
from typing import Any, Dict, List

# Precedence order: risk-facing states first. A stock that is both crowded
# and under distribution should warn "crowd leaving" over "crowd large".
STATES = ("DISTRIBUTION", "CROWDED", "ACCELERATING", "EARLY", "NEUTRAL")


def _clip01(x: float) -> float:
    return min(max(x, 0.0), 1.0)


def classify_herd(m: Dict[str, Any]) -> Dict[str, Any]:
    """Classify one ticker's crowd state from its compute_metrics dict.

    Pure function; tolerates sparse dicts (every read has a neutral default)
    and never raises. Returns herd_state, herd_score (0-100 crowd
    temperature, independent of state: state carries direction, score
    carries magnitude), up to 4 human-readable reasons, mechanical
    stop/trim levels, and the raw inputs for persistence.
    """
    price = float(m.get("price", 0.0) or 0.0)
    ma_20 = float(m.get("ma_20", 0.0) or 0.0)
    atr_14 = float(m.get("atr_14", 0.0) or 0.0)
    rsi = float(m.get("rsi_14", 50.0) or 50.0)
    mfi = float(m.get("mfi_14", 50.0) or 50.0)
    cmf = float(m.get("cmf_20", 0.0) or 0.0)
    rel_vol = float(m.get("rel_vol", 1.0) or 1.0)
    updown = float(m.get("updown_vol_ratio_10d", 1.0) or 1.0)
    obv_slope = float(m.get("obv_slope_10d", 0.0) or 0.0)
    obv_div = bool(m.get("obv_divergence", False))
    climax = bool(m.get("vol_climax", False))
    acc_days = int(m.get("acc_days_25d", 0) or 0)
    dist_days = int(m.get("dist_days_25d", 0) or 0)
    ext_atr = float(m.get("ext_atr", 0.0) or 0.0)
    change_3d = float(m.get("change_3d", 0.0) or 0.0)
    change_7d = float(m.get("change_7d", 0.0) or 0.0)
    vol_trend_7d = float(m.get("vol_trend_7d", 0.0) or 0.0)
    pct_from_ma20 = float(m.get("pct_from_ma20", 0.0) or 0.0)
    pct_from_ma50 = float(m.get("pct_from_ma50", 0.0) or 0.0)

    # Momentum pace halved while the week is still materially up.
    mom_decel = change_7d > 4.0 and (change_3d / 3.0) < 0.5 * (change_7d / 7.0)

    reasons: List[str] = []
    state = "NEUTRAL"

    dist_signals = []
    if obv_div:
        dist_signals.append("OBV divergence: price higher-high, flow isn't")
    if dist_days >= 4 and dist_days > acc_days:
        dist_signals.append(f"{dist_days} distribution vs {acc_days} accumulation days (25d)")
    if updown < 0.8:
        dist_signals.append(f"down-day volume dominating (u/d {updown:.2f})")
    if cmf < -0.05:
        dist_signals.append(f"CMF {cmf:.2f}: money flowing out")
    if obv_slope < -0.10:
        dist_signals.append("OBV falling")

    if len(dist_signals) >= 2:
        state = "DISTRIBUTION"
        reasons = dist_signals
    elif ext_atr >= 3.0 or rsi >= 78 or mfi >= 85 or climax:
        state = "CROWDED"
        if ext_atr >= 3.0:
            reasons.append(f"{ext_atr:.1f} ATRs above 20-MA")
        if rsi >= 78:
            reasons.append(f"RSI {rsi:.0f}")
        if mfi >= 85:
            reasons.append(f"MFI {mfi:.0f}: money flow running hot")
        if climax:
            reasons.append("climax volume day")
    elif (
        change_7d >= 5.0
        and ext_atr >= 1.0
        and (cmf > 0.05 or updown >= 1.5)
        and (rel_vol >= 1.2 or vol_trend_7d > 0)
        and not mom_decel
    ):
        state = "ACCELERATING"
        reasons.append(f"+{change_7d:.1f}% week with flow confirmation")
        if cmf > 0.05:
            reasons.append(f"CMF {cmf:.2f}: money flowing in")
        if updown >= 1.5:
            reasons.append(f"up-day volume dominating (u/d {updown:.2f})")
        if rel_vol >= 1.2:
            reasons.append(f"{rel_vol:.1f}x average volume")
    elif (
        pct_from_ma20 > 0
        and pct_from_ma50 > 0
        and ext_atr < 1.5
        and cmf > 0
        and acc_days > dist_days
        and rel_vol < 2.0
        and change_7d > -2.0
    ):
        state = "EARLY"
        reasons.append("uptrend forming without stretch")
        reasons.append(f"{acc_days} accumulation vs {dist_days} distribution days (25d)")
        if cmf > 0:
            reasons.append(f"CMF {cmf:.2f}: quiet accumulation")
    else:
        reasons.append("no dominant crowd signal")

    if mom_decel and state in ("ACCELERATING", "EARLY", "NEUTRAL"):
        reasons.append("momentum pace halved vs the week")

    herd_score = round(
        30 * _clip01(ext_atr / 4.0)
        + 20 * _clip01((rsi - 30.0) / 55.0)
        + 15 * _clip01(mfi / 100.0)
        + 20 * _clip01(rel_vol / 4.0)
        + 15 * _clip01((cmf + 0.25) / 0.5),
        1,
    )

    # Mechanical levels: stop candidates must sit strictly below price
    # (a "stop" above price is nonsense when price is under its 20-MA).
    stop_candidates = [c for c in (ma_20, price - 2 * atr_14) if 0 < c < price]
    stop_suggest = round(max(stop_candidates), 2) if stop_candidates else None
    # Price at trim_zone <=> ext_atr == 3, the CROWDED line.
    trim_zone = round(ma_20 + 3 * atr_14, 2) if atr_14 > 0 and ma_20 > 0 else None

    return {
        "herd_state": state,
        "herd_score": herd_score,
        "herd_reasons": reasons[:4],
        "stop_suggest": stop_suggest,
        "trim_zone": trim_zone,
        "inputs": {
            "obv_slope_10d": obv_slope,
            "obv_divergence": obv_div,
            "mfi_14": mfi,
            "cmf_20": cmf,
            "updown_vol_ratio_10d": updown,
            "acc_days_25d": acc_days,
            "dist_days_25d": dist_days,
            "ext_atr": ext_atr,
            "vol_climax": climax,
            "mom_decel": mom_decel,
            "rel_vol": rel_vol,
            "rsi_14": rsi,
            "change_3d": change_3d,
        },
    }


def attach_herd(records: List[Dict[str, Any]]) -> None:
    """Mutate each metric record in place with herd_state/herd_score/herd."""
    for rec in records:
        herd = classify_herd(rec)
        rec["herd_state"] = herd["herd_state"]
        rec["herd_score"] = herd["herd_score"]
        rec["herd"] = herd


def compute_breadth(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Universe-wide crowd gauge. Call after attach_herd for herd_counts."""
    n = len(records)
    if n == 0:
        return {"n": 0}

    def pct(pred) -> float:
        return round(100.0 * sum(1 for r in records if pred(r)) / n, 1)

    herd_counts: Dict[str, int] = {}
    for r in records:
        state = r.get("herd_state")
        if state:
            herd_counts[state] = herd_counts.get(state, 0) + 1

    return {
        "n": n,
        "pct_above_ma20": pct(lambda r: (r.get("pct_from_ma20") or 0) > 0),
        "pct_above_ma50": pct(lambda r: (r.get("pct_from_ma50") or 0) > 0),
        "pct_pos_7d": pct(lambda r: (r.get("change_7d") or 0) > 0),
        "median_rel_vol": round(
            statistics.median(float(r.get("rel_vol") or 0) for r in records), 2
        ),
        "pct_rsi_hot": pct(lambda r: (r.get("rsi_14") or 0) > 70),
        "new_52w_highs": sum(
            1
            for r in records
            if (r.get("pct_from_52w_high") if r.get("pct_from_52w_high") is not None else -100)
            >= -2.0
        ),
        "herd_counts": herd_counts,
    }

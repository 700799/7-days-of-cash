#!/usr/bin/env python3
"""Generate engine-parity fixtures from the Python screener for the TS port.

Produces worker/test/fixtures/engine_parity.json: a set of deterministic
synthetic OHLCV series plus the Python engine's outputs (compute_metrics,
per-agent scores, composite ranking, filters). The TypeScript engine tests
assert bit-comparable results (within rounding tolerance).

Usage:
    python scripts/gen_parity_fixtures.py
"""
from __future__ import annotations

import json
import math
import os
import random
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from screener.agents import build_agents  # noqa: E402
from screener.metrics import compute_metrics  # noqa: E402
from screener.orchestrator import score_records  # noqa: E402
from screener.filters import apply_filters  # noqa: E402


def synth_series(seed: int, n: int, trend: float, vol: float, vol_trend: float) -> dict:
    """Deterministic synthetic OHLCV series (no numpy RNG differences)."""
    rng = random.Random(seed)
    close = [100.0]
    for _ in range(n - 1):
        drift = trend + rng.gauss(0, vol)
        close.append(max(1.0, close[-1] * (1 + drift / 100)))
    opens, highs, lows, volumes = [], [], [], []
    base_vol = 1_000_000
    for i, c in enumerate(close):
        o = c * (1 + rng.gauss(0, 0.3) / 100)
        h = max(o, c) * (1 + abs(rng.gauss(0, 0.5)) / 100)
        low = min(o, c) * (1 - abs(rng.gauss(0, 0.5)) / 100)
        v = base_vol * (1 + vol_trend * i / n) * (1 + abs(rng.gauss(0, 0.2)))
        opens.append(o)
        highs.append(h)
        lows.append(low)
        volumes.append(v)
    return {
        "open": opens,
        "high": highs,
        "low": lows,
        "close": close,
        "volume": volumes,
    }


CASES = [
    # (name, seed, bars, trend%/bar, noise, volume trend)
    ("uptrend_strong", 1, 35, 1.2, 0.8, 0.5),
    ("uptrend_mild", 2, 35, 0.4, 0.6, 0.2),
    ("downtrend", 3, 35, -0.9, 0.7, -0.3),
    ("flat_quiet", 4, 35, 0.0, 0.3, 0.0),
    ("volatile_chop", 5, 35, 0.1, 2.5, 0.1),
    ("short_history_12", 6, 12, 0.8, 0.5, 0.3),
    ("min_history_10", 7, 10, 0.5, 0.4, 0.0),
    ("long_history_260", 8, 260, 0.15, 0.9, 0.1),
    ("gap_up", 9, 35, 0.6, 0.5, 0.4),
    ("crash", 10, 35, -2.5, 1.5, 0.8),
]

BENCHMARKS = {
    "VOO": {"change_7d": 1.5, "change_20d": 3.0},
    "VXF": {"change_7d": 1.0, "change_20d": 2.0},
    "QQQ": {"change_7d": 2.0, "change_20d": 4.5},
    "IWM": {"change_7d": 0.5, "change_20d": 1.0},
    "GLD": {"change_7d": -0.5, "change_20d": 1.5},
    "TLT": {"change_7d": -1.0, "change_20d": -2.0},
}
REGIMES = [
    {"trend": "bullish", "risk": "on", "leadership": "growth"},
    {"trend": "bearish", "risk": "off", "leadership": "defensive"},
]


def main() -> int:
    fixtures = {"cases": [], "too_short": None, "orchestrator": None, "filters": None}

    metrics_records = []
    for name, seed, n, trend, vol, vt in CASES:
        bars = synth_series(seed, n, trend, vol, vt)
        df = pd.DataFrame(
            {
                "Open": bars["open"],
                "High": bars["high"],
                "Low": bars["low"],
                "Close": bars["close"],
                "Volume": bars["volume"],
            }
        )
        m = compute_metrics(name.upper(), df)
        assert m is not None, name

        agents = build_agents(None)
        agent_out = {}
        for regime_idx, regime in enumerate(REGIMES):
            ctx = {"benchmarks": BENCHMARKS, "regime": regime}
            agent_out[f"regime_{regime_idx}"] = {
                a.name: {
                    "score": r.score,
                    "tier": r.tier,
                    "reasons": r.reasons,
                    "flags": r.flags,
                }
                for a in agents
                for r in [a.evaluate(m, ctx)]
            }

        fixtures["cases"].append(
            {"name": name, "bars": bars, "metrics": m, "agents": agent_out}
        )
        metrics_records.append(m)

    # < 10 bars → None
    short = synth_series(99, 8, 0.5, 0.5, 0.0)
    short_df = pd.DataFrame(
        {
            "Open": short["open"],
            "High": short["high"],
            "Low": short["low"],
            "Close": short["close"],
            "Volume": short["volume"],
        }
    )
    assert compute_metrics("SHORT", short_df) is None
    fixtures["too_short"] = {"bars": short, "expected": None}

    # Orchestrator: full composite ranking under regime 0
    scored = score_records(
        metrics_records, benchmarks=BENCHMARKS, regime=REGIMES[0]
    )
    fixtures["orchestrator"] = {
        "benchmarks": BENCHMARKS,
        "regime": REGIMES[0],
        "expected": scored.to_dict(orient="records"),
    }

    # Filters: defaults over the scored set
    filtered = apply_filters(scored.to_dict(orient="records"), {})
    fixtures["filters"] = {
        "config": {},
        "expected_tickers": filtered["ticker"].tolist() if not filtered.empty else [],
    }
    # Filters: custom thresholds
    custom_cfg = {"min_gain_7d": 2.0, "max_rsi": 90, "min_dollar_vol": 100_000, "top_n": 5}
    filtered2 = apply_filters(scored.to_dict(orient="records"), custom_cfg)
    fixtures["filters_custom"] = {
        "config": custom_cfg,
        "expected_tickers": filtered2["ticker"].tolist() if not filtered2.empty else [],
    }

    out_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "worker",
        "test",
        "fixtures",
        "engine_parity.json",
    )
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(fixtures, f, indent=1, default=float)
    print(f"Wrote {out_path} ({len(fixtures['cases'])} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

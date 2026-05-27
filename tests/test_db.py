"""Offline tests for the Postgres writer's pure helpers (no DB required)."""
import json

import numpy as np
import pandas as pd

from screener.db import _CORE_COLUMNS, _build_rows, _clean, _jsonable


def test_clean_converts_numpy_and_nan():
    assert _clean(np.int64(7)) == 7 and isinstance(_clean(np.int64(7)), int)
    assert _clean(np.float64(1.5)) == 1.5
    assert _clean(np.float64(np.nan)) is None
    assert _clean(float("nan")) is None
    assert _clean(np.bool_(True)) is True
    assert _clean(None) is None
    assert _clean("momentum") == "momentum"


def test_jsonable_handles_sets_and_numpy():
    cfg = {"active_filters": {"min_price", "max_rsi"}, "top_n": np.int64(25),
           "min_gain_7d": np.float64(8.0), "agent_names": ["momentum"]}
    out = _jsonable(cfg)
    assert out["active_filters"] == ["max_rsi", "min_price"]  # set -> sorted list
    assert out["top_n"] == 25 and isinstance(out["top_n"], int)
    json.dumps(out)  # must be serializable


def _scored_df() -> pd.DataFrame:
    return pd.DataFrame([
        {"ticker": "AAA", "price": 12.5, "change_5d": 4.0, "change_7d": 11.0,
         "avg_vol_20d": np.int64(2_000_000), "dollar_vol_20d": np.int64(25_000_000),
         "rsi_14": 61.0, "composite_score": 88.0, "best_strategy": "momentum",
         "top_reasons": "strong volume", "flags": "",
         "score_momentum": 90.0, "tier_momentum": "strong"},
        {"ticker": "BBB", "price": 30.0, "change_5d": np.float64(np.nan), "change_7d": 9.0,
         "avg_vol_20d": np.int64(800_000), "dollar_vol_20d": np.int64(24_000_000),
         "rsi_14": 55.0, "composite_score": 72.0, "best_strategy": "breakout",
         "top_reasons": "", "flags": "thin",
         "score_momentum": 70.0, "tier_momentum": "moderate"},
    ])


def test_build_rows_shape_and_rank():
    rows = _build_rows(_scored_df(), run_id=42)
    assert len(rows) == 2
    assert rows[0][0] == 42 and rows[0][1] == 1   # run_id, rank
    assert rows[1][1] == 2
    assert len(rows[0]) == len(_CORE_COLUMNS) + 3  # run_id, rank, *core, agent_scores


def test_build_rows_emits_plain_python_scalars():
    rows = _build_rows(_scored_df(), run_id=1)
    for row in rows:
        for value in row[:-1]:                     # everything but agent_scores dict
            assert not isinstance(value, np.generic), f"numpy leaked: {value!r}"
            assert value is None or isinstance(value, (int, float, str))
        assert isinstance(row[-1], dict)


def test_build_rows_nan_becomes_none_and_agent_scores_captured():
    rows = _build_rows(_scored_df(), run_id=1)
    change_5d_idx = 2 + _CORE_COLUMNS.index("change_5d")
    assert rows[1][change_5d_idx] is None          # NaN -> None
    agent_scores = rows[0][-1]
    assert agent_scores["score_momentum"] == 90.0
    assert agent_scores["tier_momentum"] == "strong"


def test_build_rows_tolerates_missing_optional_columns():
    df = pd.DataFrame([{"ticker": "CCC", "price": 5.0, "change_7d": 10.0}])
    rows = _build_rows(df, run_id=1)
    composite_idx = 2 + _CORE_COLUMNS.index("composite_score")
    assert rows[0][composite_idx] is None          # absent column -> None
    assert rows[0][-1] == {}                        # no agent columns present

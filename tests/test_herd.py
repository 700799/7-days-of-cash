"""Unit tests for the herd/crowd-state classifier, levels, and breadth."""

import pytest

from screener.herd import STATES, attach_herd, classify_herd, compute_breadth


def _metrics(**overrides) -> dict:
    """A quiet, mid-trend baseline that classifies as NEUTRAL."""
    base = {
        "ticker": "TEST",
        "price": 100.0,
        "ma_20": 98.0,
        "ma_50": 95.0,
        "atr_14": 2.0,
        "rsi_14": 55.0,
        "mfi_14": 55.0,
        "cmf_20": 0.0,
        "rel_vol": 1.0,
        "updown_vol_ratio_10d": 1.0,
        "obv_slope_10d": 0.0,
        "obv_divergence": False,
        "vol_climax": False,
        "acc_days_25d": 2,
        "dist_days_25d": 2,
        "ext_atr": 1.0,
        "change_3d": 1.0,
        "change_7d": 2.0,
        "vol_trend_7d": 0.0,
        "pct_from_ma20": 2.0,
        "pct_from_ma50": 5.0,
    }
    base.update(overrides)
    return base


def test_baseline_is_neutral():
    assert classify_herd(_metrics())["herd_state"] == "NEUTRAL"


def test_distribution_requires_two_signals():
    one = classify_herd(_metrics(cmf_20=-0.10))
    assert one["herd_state"] != "DISTRIBUTION"
    two = classify_herd(_metrics(cmf_20=-0.10, updown_vol_ratio_10d=0.5))
    assert two["herd_state"] == "DISTRIBUTION"
    assert len(two["herd_reasons"]) >= 2


@pytest.mark.parametrize(
    "overrides",
    [
        {"ext_atr": 3.5},
        {"rsi_14": 80.0},
        {"mfi_14": 90.0},
        {"vol_climax": True},
    ],
)
def test_each_crowded_trigger(overrides):
    assert classify_herd(_metrics(**overrides))["herd_state"] == "CROWDED"


def test_precedence_distribution_over_crowded():
    m = _metrics(ext_atr=3.5, rsi_14=85.0, obv_divergence=True, cmf_20=-0.10)
    assert classify_herd(m)["herd_state"] == "DISTRIBUTION"


def test_accelerating_full_conditions():
    m = _metrics(change_7d=8.0, change_3d=4.0, ext_atr=2.0, cmf_20=0.10, rel_vol=1.5)
    out = classify_herd(m)
    assert out["herd_state"] == "ACCELERATING"
    assert any("flow confirmation" in r for r in out["herd_reasons"])


def test_accelerating_blocked_by_mom_decel():
    # +8% week but the last 3 days contribute almost nothing.
    m = _metrics(change_7d=8.0, change_3d=0.5, ext_atr=2.0, cmf_20=0.10, rel_vol=1.5)
    assert classify_herd(m)["herd_state"] != "ACCELERATING"


def test_accelerating_dead_zone_regression():
    # ext_atr 1.2 with strong flow must land ACCELERATING, not fall through
    # to NEUTRAL (the dead zone a 1.5 lower bound would create).
    m = _metrics(change_7d=10.0, change_3d=5.0, ext_atr=1.2, cmf_20=0.10, rel_vol=2.5)
    assert classify_herd(m)["herd_state"] == "ACCELERATING"


def test_early_quiet_accumulation():
    m = _metrics(cmf_20=0.08, acc_days_25d=5, dist_days_25d=1, ext_atr=0.8, rel_vol=1.1)
    out = classify_herd(m)
    assert out["herd_state"] == "EARLY"
    assert any("accumulation" in r for r in out["herd_reasons"])


def test_early_rejected_when_stretched():
    m = _metrics(cmf_20=0.08, acc_days_25d=5, dist_days_25d=1, ext_atr=2.0, rel_vol=1.1)
    assert classify_herd(m)["herd_state"] != "EARLY"


def test_empty_dict_never_raises_and_is_neutral():
    out = classify_herd({})
    assert out["herd_state"] == "NEUTRAL"
    assert out["herd_state"] in STATES


def test_stop_suggest_always_below_price():
    out = classify_herd(_metrics())
    assert out["stop_suggest"] is not None
    assert out["stop_suggest"] < 100.0


def test_stop_suggest_none_when_no_candidate_below_price():
    # Price far below its 20-MA and ATR pushes the 2xATR stop negative.
    m = _metrics(price=10.0, ma_20=50.0, atr_14=6.0)
    assert classify_herd(m)["stop_suggest"] is None


def test_stop_prefers_tighter_of_ma20_and_2atr():
    # ma_20=98 vs price-2*atr=96 -> 98 is the higher (tighter) valid stop
    out = classify_herd(_metrics(price=100.0, ma_20=98.0, atr_14=2.0))
    assert out["stop_suggest"] == 98.0
    # With a wide ATR the 20-MA is still tighter; with ma above price, 2xATR wins
    out2 = classify_herd(_metrics(price=100.0, ma_20=101.0, atr_14=2.0))
    assert out2["stop_suggest"] == 96.0


def test_trim_zone_equals_crowded_line():
    out = classify_herd(_metrics(ma_20=98.0, atr_14=2.0))
    assert out["trim_zone"] == pytest.approx(98.0 + 3 * 2.0)


def test_trim_zone_none_without_atr():
    assert classify_herd(_metrics(atr_14=0.0))["trim_zone"] is None


def test_herd_score_bounds():
    cold = classify_herd(_metrics(ext_atr=0.0, rsi_14=20.0, mfi_14=0.0, rel_vol=0.1, cmf_20=-0.5))
    hot = classify_herd(_metrics(ext_atr=10.0, rsi_14=99.0, mfi_14=100.0, rel_vol=9.0, cmf_20=0.5))
    assert 0.0 <= cold["herd_score"] <= 100.0
    assert 0.0 <= hot["herd_score"] <= 100.0
    assert hot["herd_score"] > cold["herd_score"]


def test_reasons_capped_at_four():
    m = _metrics(
        obv_divergence=True,
        dist_days_25d=6,
        acc_days_25d=0,
        updown_vol_ratio_10d=0.5,
        cmf_20=-0.2,
        obv_slope_10d=-0.5,
    )
    assert len(classify_herd(m)["herd_reasons"]) <= 4


def test_attach_herd_mutates_records():
    records = [_metrics(), _metrics(ext_atr=3.5)]
    attach_herd(records)
    assert records[0]["herd_state"] == "NEUTRAL"
    assert records[1]["herd_state"] == "CROWDED"
    assert isinstance(records[0]["herd"], dict)
    assert records[0]["herd_score"] == records[0]["herd"]["herd_score"]


def test_breadth_counts():
    records = [
        _metrics(pct_from_ma20=5.0, change_7d=3.0, rsi_14=75.0, pct_from_52w_high=-1.0),
        _metrics(pct_from_ma20=-5.0, change_7d=-3.0, rsi_14=40.0, pct_from_52w_high=-20.0),
    ]
    attach_herd(records)
    b = compute_breadth(records)
    assert b["n"] == 2
    assert b["pct_above_ma20"] == 50.0
    assert b["pct_pos_7d"] == 50.0
    assert b["pct_rsi_hot"] == 50.0
    assert b["new_52w_highs"] == 1
    assert sum(b["herd_counts"].values()) == 2


def test_breadth_empty_records():
    assert compute_breadth([]) == {"n": 0}

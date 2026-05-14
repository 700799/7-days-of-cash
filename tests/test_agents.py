"""Unit tests for strategy agents."""
import pytest

from screener.agents import (
    MomentumAgent, BreakoutAgent, VolumeSurgeAgent,
    RelativeStrengthAgent, MeanReversionAgent, build_agents,
)
from screener.orchestrator import score_records


def _strong_momentum():
    return {
        "ticker": "MOM", "price": 50, "change_5d": 8, "change_7d": 12, "change_20d": 20,
        "rsi_14": 65, "vol_trend_5d": 1000, "vol_trend_7d": 1500, "macd_hist": 0.5,
        "pct_from_ma50": 8, "pct_from_52w_high": -3, "rel_vol": 1.8,
        "ma_50": 45, "ma_200": 40, "atr_pct": 3, "gap_pct": 0.5,
        "dollar_vol_20d": 50_000_000, "pct_from_ma20": 3,
    }


def _strong_breakout():
    return {
        "ticker": "BRK", "price": 50, "change_5d": 6, "change_7d": 8, "change_20d": 10,
        "rsi_14": 65, "vol_trend_5d": 500, "vol_trend_7d": 800, "macd_hist": 0.3,
        "pct_from_ma50": 5, "pct_from_52w_high": -1, "rel_vol": 2.5,
        "ma_50": 47, "ma_200": 42, "atr_pct": 4, "gap_pct": 3,
        "dollar_vol_20d": 20_000_000, "pct_from_ma20": 5,
    }


def _strong_meanrev():
    return {
        "ticker": "MR", "price": 100, "change_5d": 0, "change_7d": -2, "change_20d": 5,
        "rsi_14": 42, "vol_trend_5d": 0, "vol_trend_7d": 0, "macd_hist": -0.05,
        "pct_from_ma50": -2, "pct_from_52w_high": -6, "rel_vol": 1.0,
        "ma_50": 102, "ma_200": 95, "atr_pct": 2, "gap_pct": 0,
        "dollar_vol_20d": 10_000_000, "pct_from_ma20": -1,
    }


@pytest.mark.parametrize("agent_cls", [
    MomentumAgent, BreakoutAgent, VolumeSurgeAgent,
    RelativeStrengthAgent, MeanReversionAgent,
])
def test_agent_returns_valid_score_range(agent_cls):
    agent = agent_cls()
    result = agent.evaluate(_strong_momentum(), context={"benchmarks": {}})
    assert 0 <= result.score <= 100
    assert result.tier in {"strong", "moderate", "weak", "skip"}


def test_momentum_agent_scores_strong_setup_highly():
    result = MomentumAgent().evaluate(_strong_momentum())
    assert result.score >= 70


def test_breakout_agent_scores_strong_breakout_highly():
    result = BreakoutAgent().evaluate(_strong_breakout())
    assert result.score >= 65


def test_mean_reversion_skips_when_not_in_uptrend():
    rec = _strong_meanrev()
    rec["ma_50"] = 80  # below 200-MA
    rec["ma_200"] = 100
    result = MeanReversionAgent().evaluate(rec)
    assert result.tier == "skip"


def test_relative_strength_uses_benchmarks():
    rec = _strong_momentum()
    bench = {
        "VOO": {"change_7d": 0.5, "change_20d": 2},
        "VXF": {"change_7d": 0.0},
        "QQQ": {"change_7d": 1.0, "change_20d": 3},
    }
    result = RelativeStrengthAgent().evaluate(rec, context={"benchmarks": bench})
    assert result.score > 0
    assert any("VOO" in r or "VXF" in r or "QQQ" in r for r in result.reasons)


def test_build_agents_returns_all_by_default():
    agents = build_agents()
    assert len(agents) == 5


def test_build_agents_can_subset():
    agents = build_agents(["momentum", "breakout"])
    assert len(agents) == 2


def test_orchestrator_produces_composite_score():
    recs = [_strong_momentum(), _strong_breakout()]
    bench = {"VOO": {"change_7d": 0.5}, "VXF": {"change_7d": 0.2}, "QQQ": {"change_7d": 1.0}}
    df = score_records(recs, benchmarks=bench)
    assert "composite_score" in df.columns
    assert "score_momentum" in df.columns
    assert "best_strategy" in df.columns
    assert len(df) == 2

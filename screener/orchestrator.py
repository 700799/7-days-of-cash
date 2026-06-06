"""Multi-agent orchestrator that combines strategy agent scores into a composite ranking."""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from .agents import build_agents

DEFAULT_WEIGHTS = {
    "momentum": 1.0,
    "breakout": 0.9,
    "volume_surge": 0.9,
    "relative_strength": 1.0,
    "mean_reversion": 0.7,
}


def score_records(
    records: List[Dict[str, Any]],
    benchmarks: Dict[str, Dict[str, Any]] | None = None,
    regime: Dict[str, str] | None = None,
    agent_names: List[str] | None = None,
    weights: Dict[str, float] | None = None,
) -> pd.DataFrame:
    """Score every record with every agent and build a composite DataFrame."""
    if not records:
        return pd.DataFrame()

    agents = build_agents(agent_names)
    weights = weights or DEFAULT_WEIGHTS
    context = {"benchmarks": benchmarks or {}, "regime": regime or {}}

    rows: List[Dict[str, Any]] = []
    for rec in records:
        row = dict(rec)
        weighted_total = 0.0
        weight_sum = 0.0
        top_reasons: List[str] = []
        flag_set: List[str] = []
        for agent in agents:
            result = agent.evaluate(rec, context)
            row[f"score_{agent.name}"] = result.score
            row[f"tier_{agent.name}"] = result.tier
            w = weights.get(agent.name, 1.0)
            weighted_total += result.score * w
            weight_sum += w
            if result.tier in ("strong", "moderate"):
                top_reasons.extend(result.reasons[:2])
            flag_set.extend(result.flags)

        composite = weighted_total / weight_sum if weight_sum else 0.0
        row["composite_score"] = round(composite, 1)
        row["top_reasons"] = " | ".join(list(dict.fromkeys(top_reasons))[:4]) if top_reasons else ""
        row["flags"] = " | ".join(list(dict.fromkeys(flag_set))[:3]) if flag_set else ""
        row["best_strategy"] = _best_strategy(row, [a.name for a in agents])
        rows.append(row)

    df = pd.DataFrame(rows)
    df = df.sort_values("composite_score", ascending=False).reset_index(drop=True)
    return df


def _best_strategy(row: Dict[str, Any], names: List[str]) -> str:
    best, best_score = "", -1.0
    for n in names:
        s = row.get(f"score_{n}", 0.0)
        if s > best_score:
            best, best_score = n, s
    return best

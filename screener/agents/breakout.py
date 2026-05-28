"""Breakout agent — looks for high-volume breaks near 52-week highs."""

from __future__ import annotations

from typing import Any, Dict

from .base import AgentResult, BaseAgent


class BreakoutAgent(BaseAgent):
    name = "breakout"
    description = "High-volume break near 52w high, RSI crossing 60, healthy MACD"

    def evaluate(self, m: Dict[str, Any], context: Dict[str, Any] | None = None) -> AgentResult:
        reasons = []
        flags = []

        rel_vol = m.get("rel_vol", 1.0)
        rsi = m.get("rsi_14", 50.0)
        pct_52w = m.get("pct_from_52w_high", -50.0)
        gap = m.get("gap_pct", 0.0)
        c5 = m.get("change_5d", 0.0)
        macd = m.get("macd_hist", 0.0)

        # Score: rel_vol × proximity to 52w high × RSI in breakout zone
        rv_score = self.clip((rel_vol - 1.0) * 25, 0, 35)
        if rel_vol >= 2.0:
            reasons.append(f"rel vol {rel_vol:.1f}x")

        proximity_score = 0
        if pct_52w >= -3:
            proximity_score = 30
            reasons.append(f"at 52w high ({pct_52w:.1f}%)")
        elif pct_52w >= -8:
            proximity_score = 20
            reasons.append(f"near 52w high ({pct_52w:.1f}%)")
        elif pct_52w >= -15:
            proximity_score = 10
        elif pct_52w < -25:
            proximity_score = -10
            flags.append("far from 52w high")

        rsi_score = 0
        if 58 <= rsi <= 72:
            rsi_score = 15
            reasons.append(f"RSI in breakout zone ({rsi:.0f})")
        elif rsi > 80:
            rsi_score = -10
            flags.append("RSI overextended")

        gap_score = 8 if gap > 1 else 0
        if gap > 2:
            reasons.append(f"gap up +{gap:.1f}%")

        macd_score = 5 if macd > 0 else -2
        c5_score = 5 if c5 > 3 else 0

        total = rv_score + proximity_score + rsi_score + gap_score + macd_score + c5_score
        score = self.clip(total)
        return AgentResult(self.name, score, self.tier_for(score), reasons, flags)

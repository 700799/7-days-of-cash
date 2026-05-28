"""Volume Surge agent — detects accumulation before the price move."""

from __future__ import annotations

from typing import Any, Dict

from .base import AgentResult, BaseAgent


class VolumeSurgeAgent(BaseAgent):
    name = "volume_surge"
    description = "Rising volume trend with rel_vol > 1.5x — smart money accumulation"

    def evaluate(self, m: Dict[str, Any], context: Dict[str, Any] | None = None) -> AgentResult:
        reasons = []
        flags = []

        rel_vol = m.get("rel_vol", 1.0)
        v5 = m.get("vol_trend_5d", 0.0)
        v7 = m.get("vol_trend_7d", 0.0)
        c5 = m.get("change_5d", 0.0)
        c7 = m.get("change_7d", 0.0)
        dollar_vol = m.get("dollar_vol_20d", 0)

        rv_score = self.clip((rel_vol - 1.0) * 30, 0, 40)
        if rel_vol >= 2.0:
            reasons.append(f"rel vol {rel_vol:.1f}x")
        elif rel_vol >= 1.5:
            reasons.append(f"elevated vol {rel_vol:.1f}x")
        elif rel_vol < 1.0:
            flags.append("below avg vol")

        trend_score = 0
        if v5 > 0 and v7 > 0:
            trend_score = 30
            reasons.append("vol trend rising 5d & 7d")
        elif v5 > 0:
            trend_score = 15
        elif v5 < 0 and v7 < 0:
            trend_score = -15
            flags.append("vol declining")

        # Liquidity bonus
        liq_score = 0
        if dollar_vol >= 50_000_000:
            liq_score = 10
            reasons.append("highly liquid")
        elif dollar_vol >= 10_000_000:
            liq_score = 5
        elif dollar_vol < 1_000_000:
            liq_score = -5
            flags.append("low liquidity")

        # Bonus when price is starting to follow
        price_followthrough = 0
        if c5 > 2 and c7 > 4:
            price_followthrough = 15
            reasons.append("price following volume")

        total = rv_score + trend_score + liq_score + price_followthrough
        score = self.clip(total)
        return AgentResult(self.name, score, self.tier_for(score), reasons, flags)

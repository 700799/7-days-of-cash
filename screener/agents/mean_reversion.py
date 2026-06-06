"""Mean Reversion agent — flags pullbacks in established uptrends."""

from __future__ import annotations

from typing import Any, Dict

from .base import AgentResult, BaseAgent


class MeanReversionAgent(BaseAgent):
    name = "mean_reversion"
    description = "Pullback to 20-MA in a long-term uptrend (50-MA > 200-MA, RSI < 50)"

    def evaluate(self, m: Dict[str, Any], context: Dict[str, Any] | None = None) -> AgentResult:
        reasons = []
        flags = []

        rsi = m.get("rsi_14", 50.0)
        pct_ma20 = m.get("pct_from_ma20", 0.0)
        pct_ma50 = m.get("pct_from_ma50", 0.0)
        ma_50 = m.get("ma_50", 0.0)
        ma_200 = m.get("ma_200", 0.0)
        c5 = m.get("change_5d", 0.0)

        # Long-term uptrend filter
        uptrend = ma_50 > ma_200
        if not uptrend:
            flags.append("not in long-term uptrend")
            return AgentResult(self.name, 10.0, "skip", reasons, flags)

        reasons.append("LT uptrend (50>200 MA)")

        # Pullback proximity to 20-MA
        pullback_score = 0
        if -2 <= pct_ma20 <= 2:
            pullback_score = 30
            reasons.append(f"at 20-MA ({pct_ma20:+.1f}%)")
        elif -5 <= pct_ma20 < -2:
            pullback_score = 25
            reasons.append(f"just below 20-MA ({pct_ma20:+.1f}%)")
        elif 2 < pct_ma20 <= 5:
            pullback_score = 15
        elif pct_ma20 < -10:
            pullback_score = -10
            flags.append("deep below 20-MA")

        # Oversold (but not crashed) RSI
        rsi_score = 0
        if 35 <= rsi <= 50:
            rsi_score = 25
            reasons.append(f"RSI cooled ({rsi:.0f})")
        elif rsi < 30:
            rsi_score = 10
            flags.append("deeply oversold")
        elif rsi > 65:
            rsi_score = -10

        # 50-MA still rising
        ma50_score = 10 if pct_ma50 > -8 else -10

        # Recent stabilization
        stabilization = 0
        if -2 < c5 < 3:
            stabilization = 10
            reasons.append("price stabilizing")

        total = pullback_score + rsi_score + ma50_score + stabilization
        score = self.clip(total)
        return AgentResult(self.name, score, self.tier_for(score), reasons, flags)

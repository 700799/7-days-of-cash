"""Momentum agent — rewards strong recent gains with rising volume."""

from __future__ import annotations

from typing import Any, Dict

from .base import AgentResult, BaseAgent


class MomentumAgent(BaseAgent):
    name = "momentum"
    description = "Strong multi-timeframe gains with rising volume and healthy RSI"

    def evaluate(self, m: Dict[str, Any], context: Dict[str, Any] | None = None) -> AgentResult:
        reasons = []
        flags = []

        c7 = m.get("change_7d", 0.0)
        c20 = m.get("change_20d", 0.0)
        rsi = m.get("rsi_14", 50.0)
        v5 = m.get("vol_trend_5d", 0.0)
        v7 = m.get("vol_trend_7d", 0.0)
        macd = m.get("macd_hist", 0.0)
        pct_ma50 = m.get("pct_from_ma50", 0.0)

        # Score: gain × volume confirmation × healthy RSI
        gain_score = self.clip(c7 * 4, 0, 50)  # 0-50 for 0-12.5%+ gain
        vol_score = 0
        if v5 > 0 and v7 > 0:
            vol_score += 20
            reasons.append("vol rising 5d & 7d")
        elif v5 > 0 or v7 > 0:
            vol_score += 10
            reasons.append("vol partially rising")

        rsi_score = 0
        if 55 <= rsi <= 75:
            rsi_score = 15
            reasons.append(f"RSI healthy ({rsi:.0f})")
        elif rsi > 80:
            rsi_score = -10
            flags.append(f"RSI overextended ({rsi:.0f})")
        elif rsi < 45:
            rsi_score = -5

        macd_score = 8 if macd > 0 else -3
        if macd > 0:
            reasons.append("MACD bullish")

        ma_score = 7 if pct_ma50 > 0 else -3
        if pct_ma50 > 5:
            reasons.append(f"+{pct_ma50:.0f}% above 50-MA")

        if c7 > 8 and c20 > 0:
            reasons.append(f"7d +{c7:.1f}%, 20d +{c20:.1f}%")

        total = gain_score + vol_score + rsi_score + macd_score + ma_score
        score = self.clip(total)
        return AgentResult(self.name, score, self.tier_for(score), reasons, flags)

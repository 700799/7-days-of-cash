"""Relative Strength agent — outperformance vs broad market benchmarks."""
from __future__ import annotations

from typing import Any, Dict, Optional

from .base import AgentResult, BaseAgent


class RelativeStrengthAgent(BaseAgent):
    name = "relative_strength"
    description = "Outperformance vs VOO, VXF, QQQ — true RS leaders"

    def evaluate(self, m: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> AgentResult:
        reasons = []
        flags = []

        bench = (context or {}).get("benchmarks", {})
        voo = bench.get("VOO", {}).get("change_7d", 0.0)
        vxf = bench.get("VXF", {}).get("change_7d", 0.0)
        qqq = bench.get("QQQ", {}).get("change_7d", 0.0)

        c7 = m.get("change_7d", 0.0)
        c20 = m.get("change_20d", 0.0)

        alpha_voo = c7 - voo
        alpha_vxf = c7 - vxf
        alpha_qqq = c7 - qqq

        # Score scaled by alpha vs each benchmark
        alpha_score = (alpha_voo + alpha_vxf + alpha_qqq) / 3.0
        score_base = self.clip(alpha_score * 5, 0, 70)

        if alpha_voo > 5:
            reasons.append(f"+{alpha_voo:.1f}% vs VOO")
        if alpha_vxf > 5:
            reasons.append(f"+{alpha_vxf:.1f}% vs VXF")
        if alpha_qqq > 3:
            reasons.append(f"+{alpha_qqq:.1f}% vs QQQ")

        if alpha_voo < -2:
            flags.append("underperforming VOO")
        if alpha_qqq < -3:
            flags.append("lagging QQQ")

        # Bonus for sustained RS (20d outperformance)
        voo_20 = bench.get("VOO", {}).get("change_20d", 0.0)
        sustained_score = 0
        if c20 - voo_20 > 5:
            sustained_score = 15
            reasons.append(f"sustained RS (20d alpha +{c20 - voo_20:.0f}%)")

        # Down-market RS bonus
        regime_bonus = 0
        regime = (context or {}).get("regime", {})
        if regime.get("trend") == "bearish" and c7 > 0:
            regime_bonus = 15
            reasons.append("up in a down market")

        total = score_base + sustained_score + regime_bonus
        score = self.clip(total)
        return AgentResult(self.name, score, self.tier_for(score), reasons, flags)

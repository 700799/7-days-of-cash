// Breakout agent — port of screener/agents/breakout.py.

import type { Metrics } from "../metrics";
import { type Agent, type AgentContext, type AgentResult, clip, fmt0, fmt1, tierFor } from "./base";

export const breakoutAgent: Agent = {
  name: "breakout",
  description: "High-volume break near 52w high, RSI crossing 60, healthy MACD",

  evaluate(m: Metrics, _context: AgentContext): AgentResult {
    const reasons: string[] = [];
    const flags: string[] = [];

    const relVol = m.rel_vol ?? 1.0;
    const rsi = m.rsi_14 ?? 50;
    const pct52w = m.pct_from_52w_high ?? -50;
    const gap = m.gap_pct ?? 0;
    const c5 = m.change_5d ?? 0;
    const macd = m.macd_hist ?? 0;

    const rvScore = clip((relVol - 1.0) * 25, 0, 35);
    if (relVol >= 2.0) reasons.push(`rel vol ${fmt1(relVol)}x`);

    let proximityScore = 0;
    if (pct52w >= -3) {
      proximityScore = 30;
      reasons.push(`at 52w high (${fmt1(pct52w)}%)`);
    } else if (pct52w >= -8) {
      proximityScore = 20;
      reasons.push(`near 52w high (${fmt1(pct52w)}%)`);
    } else if (pct52w >= -15) {
      proximityScore = 10;
    } else if (pct52w < -25) {
      proximityScore = -10;
      flags.push("far from 52w high");
    }

    let rsiScore = 0;
    if (rsi >= 58 && rsi <= 72) {
      rsiScore = 15;
      reasons.push(`RSI in breakout zone (${fmt0(rsi)})`);
    } else if (rsi > 80) {
      rsiScore = -10;
      flags.push("RSI overextended");
    }

    const gapScore = gap > 1 ? 8 : 0;
    if (gap > 2) reasons.push(`gap up +${fmt1(gap)}%`);

    const macdScore = macd > 0 ? 5 : -2;
    const c5Score = c5 > 3 ? 5 : 0;

    const score = clip(rvScore + proximityScore + rsiScore + gapScore + macdScore + c5Score);
    return { name: this.name, score, tier: tierFor(score), reasons, flags };
  },
};

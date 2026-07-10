// Mean Reversion agent — port of screener/agents/mean_reversion.py.

import type { Metrics } from "../metrics";
import { type Agent, type AgentContext, type AgentResult, clip, fmt0, fmtSigned1, tierFor } from "./base";

export const meanReversionAgent: Agent = {
  name: "mean_reversion",
  description: "Pullback to 20-MA in a long-term uptrend (50-MA > 200-MA, RSI < 50)",

  evaluate(m: Metrics, _context: AgentContext): AgentResult {
    const reasons: string[] = [];
    const flags: string[] = [];

    const rsi = m.rsi_14 ?? 50;
    const pctMa20 = m.pct_from_ma20 ?? 0;
    const pctMa50 = m.pct_from_ma50 ?? 0;
    const ma50 = m.ma_50 ?? 0;
    const ma200 = m.ma_200 ?? 0;
    const c5 = m.change_5d ?? 0;

    // Long-term uptrend gate — everything else is skipped when it fails.
    if (!(ma50 > ma200)) {
      flags.push("not in long-term uptrend");
      return { name: this.name, score: 10.0, tier: "skip", reasons, flags };
    }
    reasons.push("LT uptrend (50>200 MA)");

    let pullbackScore = 0;
    if (pctMa20 >= -2 && pctMa20 <= 2) {
      pullbackScore = 30;
      reasons.push(`at 20-MA (${fmtSigned1(pctMa20)}%)`);
    } else if (pctMa20 >= -5 && pctMa20 < -2) {
      pullbackScore = 25;
      reasons.push(`just below 20-MA (${fmtSigned1(pctMa20)}%)`);
    } else if (pctMa20 > 2 && pctMa20 <= 5) {
      pullbackScore = 15;
    } else if (pctMa20 < -10) {
      pullbackScore = -10;
      flags.push("deep below 20-MA");
    }

    let rsiScore = 0;
    if (rsi >= 35 && rsi <= 50) {
      rsiScore = 25;
      reasons.push(`RSI cooled (${fmt0(rsi)})`);
    } else if (rsi < 30) {
      rsiScore = 10;
      flags.push("deeply oversold");
    } else if (rsi > 65) {
      rsiScore = -10;
    }

    const ma50Score = pctMa50 > -8 ? 10 : -10;

    let stabilization = 0;
    if (c5 > -2 && c5 < 3) {
      stabilization = 10;
      reasons.push("price stabilizing");
    }

    const score = clip(pullbackScore + rsiScore + ma50Score + stabilization);
    return { name: this.name, score, tier: tierFor(score), reasons, flags };
  },
};

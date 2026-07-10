// Momentum agent — port of screener/agents/momentum.py.

import type { Metrics } from "../metrics";
import { type Agent, type AgentContext, type AgentResult, clip, fmt0, fmt1, tierFor } from "./base";

export const momentumAgent: Agent = {
  name: "momentum",
  description: "Strong multi-timeframe gains with rising volume and healthy RSI",

  evaluate(m: Metrics, _context: AgentContext): AgentResult {
    const reasons: string[] = [];
    const flags: string[] = [];

    const c7 = m.change_7d ?? 0;
    const c5 = m.change_5d ?? 0;
    const c20 = m.change_20d ?? 0;
    const rsi = m.rsi_14 ?? 50;
    const v5 = m.vol_trend_5d ?? 0;
    const v7 = m.vol_trend_7d ?? 0;
    const macd = m.macd_hist ?? 0;
    const pctMa50 = m.pct_from_ma50 ?? 0;
    void c5;

    const gainScore = clip(c7 * 4, 0, 50);

    let volScore = 0;
    if (v5 > 0 && v7 > 0) {
      volScore = 20;
      reasons.push("vol rising 5d & 7d");
    } else if (v5 > 0 || v7 > 0) {
      volScore = 10;
      reasons.push("vol partially rising");
    }

    let rsiScore = 0;
    if (rsi >= 55 && rsi <= 75) {
      rsiScore = 15;
      reasons.push(`RSI healthy (${fmt0(rsi)})`);
    } else if (rsi > 80) {
      rsiScore = -10;
      flags.push(`RSI overextended (${fmt0(rsi)})`);
    } else if (rsi < 45) {
      rsiScore = -5;
    }

    const macdScore = macd > 0 ? 8 : -3;
    if (macd > 0) reasons.push("MACD bullish");

    const maScore = pctMa50 > 0 ? 7 : -3;
    if (pctMa50 > 5) reasons.push(`+${fmt0(pctMa50)}% above 50-MA`);

    if (c7 > 8 && c20 > 0) reasons.push(`7d +${fmt1(c7)}%, 20d +${fmt1(c20)}%`);

    const score = clip(gainScore + volScore + rsiScore + macdScore + maScore);
    return { name: this.name, score, tier: tierFor(score), reasons, flags };
  },
};

// Volume Surge agent — port of screener/agents/volume_surge.py.

import type { Metrics } from "../metrics";
import { type Agent, type AgentContext, type AgentResult, clip, fmt1, tierFor } from "./base";

export const volumeSurgeAgent: Agent = {
  name: "volume_surge",
  description: "Rising volume trend with rel_vol > 1.5x — smart money accumulation",

  evaluate(m: Metrics, _context: AgentContext): AgentResult {
    const reasons: string[] = [];
    const flags: string[] = [];

    const relVol = m.rel_vol ?? 1.0;
    const v5 = m.vol_trend_5d ?? 0;
    const v7 = m.vol_trend_7d ?? 0;
    const c5 = m.change_5d ?? 0;
    const c7 = m.change_7d ?? 0;
    const dollarVol = m.dollar_vol_20d ?? 0;

    const rvScore = clip((relVol - 1.0) * 30, 0, 40);
    if (relVol >= 2.0) reasons.push(`rel vol ${fmt1(relVol)}x`);
    else if (relVol >= 1.5) reasons.push(`elevated vol ${fmt1(relVol)}x`);
    else if (relVol < 1.0) flags.push("below avg vol");

    let trendScore = 0;
    if (v5 > 0 && v7 > 0) {
      trendScore = 30;
      reasons.push("vol trend rising 5d & 7d");
    } else if (v5 > 0) {
      trendScore = 15;
    } else if (v5 < 0 && v7 < 0) {
      trendScore = -15;
      flags.push("vol declining");
    }

    let liqScore = 0;
    if (dollarVol >= 50_000_000) {
      liqScore = 10;
      reasons.push("highly liquid");
    } else if (dollarVol >= 10_000_000) {
      liqScore = 5;
    } else if (dollarVol < 1_000_000) {
      liqScore = -5;
      flags.push("low liquidity");
    }

    let followthrough = 0;
    if (c5 > 2 && c7 > 4) {
      followthrough = 15;
      reasons.push("price following volume");
    }

    const score = clip(rvScore + trendScore + liqScore + followthrough);
    return { name: this.name, score, tier: tierFor(score), reasons, flags };
  },
};

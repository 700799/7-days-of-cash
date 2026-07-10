// Relative Strength agent — port of screener/agents/relative_strength.py.

import type { Metrics } from "../metrics";
import { type Agent, type AgentContext, type AgentResult, clip, fmt0, fmt1, tierFor } from "./base";

export const relativeStrengthAgent: Agent = {
  name: "relative_strength",
  description: "Outperformance vs VOO, VXF, QQQ — true RS leaders",

  evaluate(m: Metrics, context: AgentContext): AgentResult {
    const reasons: string[] = [];
    const flags: string[] = [];

    const bench = context.benchmarks ?? {};
    const voo = bench["VOO"]?.change_7d ?? 0;
    const vxf = bench["VXF"]?.change_7d ?? 0;
    const qqq = bench["QQQ"]?.change_7d ?? 0;

    const c7 = m.change_7d ?? 0;
    const c20 = m.change_20d ?? 0;

    const alphaVoo = c7 - voo;
    const alphaVxf = c7 - vxf;
    const alphaQqq = c7 - qqq;

    const alphaScore = (alphaVoo + alphaVxf + alphaQqq) / 3.0;
    const scoreBase = clip(alphaScore * 5, 0, 70);

    if (alphaVoo > 5) reasons.push(`+${fmt1(alphaVoo)}% vs VOO`);
    if (alphaVxf > 5) reasons.push(`+${fmt1(alphaVxf)}% vs VXF`);
    if (alphaQqq > 3) reasons.push(`+${fmt1(alphaQqq)}% vs QQQ`);

    if (alphaVoo < -2) flags.push("underperforming VOO");
    if (alphaQqq < -3) flags.push("lagging QQQ");

    const voo20 = bench["VOO"]?.change_20d ?? 0;
    let sustainedScore = 0;
    if (c20 - voo20 > 5) {
      sustainedScore = 15;
      reasons.push(`sustained RS (20d alpha +${fmt0(c20 - voo20)}%)`);
    }

    let regimeBonus = 0;
    if (context.regime?.trend === "bearish" && c7 > 0) {
      regimeBonus = 15;
      reasons.push("up in a down market");
    }

    const score = clip(scoreBase + sustainedScore + regimeBonus);
    return { name: this.name, score, tier: tierFor(score), reasons, flags };
  },
};

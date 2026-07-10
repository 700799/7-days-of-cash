// Multi-agent orchestrator — port of screener/orchestrator.py.

import { type AgentContext, buildAgents } from "./agents";
import type { Metrics } from "./metrics";

export const DEFAULT_WEIGHTS: Record<string, number> = {
  momentum: 1.0,
  breakout: 0.9,
  volume_surge: 0.9,
  relative_strength: 1.0,
  mean_reversion: 0.7,
};

export interface ScoredRecord extends Metrics {
  composite_score: number;
  top_reasons: string;
  flags: string;
  best_strategy: string;
  [key: `score_${string}`]: number;
  [key: `tier_${string}`]: string;
}

const round1 = (v: number): number => Math.round(v * 10) / 10;

const dedupe = <T>(xs: T[]): T[] => [...new Set(xs)];

/** Score every record with every agent → composite ranking, sorted desc. */
export function scoreRecords(
  records: Metrics[],
  options: {
    benchmarks?: AgentContext["benchmarks"];
    regime?: AgentContext["regime"];
    agentNames?: string[] | null;
    weights?: Record<string, number>;
  } = {},
): ScoredRecord[] {
  if (records.length === 0) return [];

  const agents = buildAgents(options.agentNames);
  const weights = options.weights ?? DEFAULT_WEIGHTS;
  const context: AgentContext = {
    benchmarks: options.benchmarks ?? {},
    regime: options.regime ?? {},
  };

  const rows: ScoredRecord[] = [];
  for (const rec of records) {
    const row = { ...rec } as ScoredRecord;
    let weightedTotal = 0;
    let weightSum = 0;
    const topReasons: string[] = [];
    const flagSet: string[] = [];

    for (const agent of agents) {
      const result = agent.evaluate(rec, context);
      row[`score_${agent.name}`] = result.score;
      row[`tier_${agent.name}`] = result.tier;
      const w = weights[agent.name] ?? 1.0;
      weightedTotal += result.score * w;
      weightSum += w;
      if (result.tier === "strong" || result.tier === "moderate") {
        topReasons.push(...result.reasons.slice(0, 2));
      }
      flagSet.push(...result.flags);
    }

    row.composite_score = weightSum ? round1(weightedTotal / weightSum) : 0.0;
    row.top_reasons = topReasons.length ? dedupe(topReasons).slice(0, 4).join(" | ") : "";
    row.flags = flagSet.length ? dedupe(flagSet).slice(0, 3).join(" | ") : "";
    row.best_strategy = bestStrategy(row, agents.map((a) => a.name));
    rows.push(row);
  }

  rows.sort((a, b) => b.composite_score - a.composite_score);
  return rows;
}

function bestStrategy(row: ScoredRecord, names: string[]): string {
  let best = "";
  let bestScore = -1.0;
  for (const n of names) {
    const s = row[`score_${n}`] ?? 0.0;
    if (s > bestScore) {
      best = n;
      bestScore = s;
    }
  }
  return best;
}

// Agent framework — port of screener/agents/base.py.
//
// An agent scores one stock's metrics 0-100 with a conviction tier and
// human-readable reasons/flags. Add a new strategy by implementing Agent and
// registering it in index.ts — the orchestrator picks it up automatically.

import type { Metrics } from "../metrics";

export type Tier = "strong" | "moderate" | "weak" | "skip";

export interface AgentResult {
  name: string;
  score: number;
  tier: Tier;
  reasons: string[];
  flags: string[];
}

export interface AgentContext {
  benchmarks: Record<string, { change_7d?: number; change_20d?: number }>;
  regime: { trend?: string; risk?: string; leadership?: string };
}

export interface Agent {
  name: string;
  description: string;
  evaluate(m: Metrics, context: AgentContext): AgentResult;
}

export function tierFor(score: number): Tier {
  if (score >= 75) return "strong";
  if (score >= 55) return "moderate";
  if (score >= 35) return "weak";
  return "skip";
}

export function clip(v: number, lo = 0, hi = 100): number {
  return Math.max(lo, Math.min(hi, v));
}

/** Python-style f-string "{:.0f}" / "{:.1f}" formatting (round-half-even is
 * close enough for display strings; scores never depend on these). */
export const fmt0 = (v: number): string => v.toFixed(0);
export const fmt1 = (v: number): string => v.toFixed(1);
/** "{:+.1f}" — explicit sign. */
export const fmtSigned1 = (v: number): string => (v >= 0 ? `+${v.toFixed(1)}` : v.toFixed(1));

// Agent registry — port of screener/agents/__init__.py.
// Order matters: best_strategy ties resolve to the first agent in this list.

import type { Agent } from "./base";
import { breakoutAgent } from "./breakout";
import { meanReversionAgent } from "./meanReversion";
import { momentumAgent } from "./momentum";
import { relativeStrengthAgent } from "./relativeStrength";
import { volumeSurgeAgent } from "./volumeSurge";

export const ALL_AGENTS: readonly Agent[] = [
  momentumAgent,
  breakoutAgent,
  volumeSurgeAgent,
  relativeStrengthAgent,
  meanReversionAgent,
];

export function buildAgents(names?: string[] | null): Agent[] {
  if (!names || names.length === 0) return [...ALL_AGENTS];
  const wanted = new Set(names.map((n) => n.toLowerCase()));
  return ALL_AGENTS.filter((a) => wanted.has(a.name));
}

export * from "./base";

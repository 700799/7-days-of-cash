// Engine parity: the TypeScript engine must reproduce the Python engine's
// outputs on shared fixtures (worker/test/fixtures/engine_parity.json,
// regenerated with `python scripts/gen_parity_fixtures.py`).

import { describe, expect, it } from "vitest";
import { computeMetrics, type Metrics, type Ohlcv } from "../src/engine/metrics";
import { buildAgents, type AgentContext } from "../src/engine/agents";
import { scoreRecords } from "../src/engine/orchestrator";
import { applyFilters } from "../src/engine/filters";
import { marketRegime } from "../src/engine/benchmarks";
import fixtures from "./fixtures/engine_parity.json";

// Tolerance per rounding precision: 1.5 ulp of the rounded field absorbs
// Python banker's-rounding vs JS half-up differences.
const TOL: Record<string, number> = {
  price: 0.015,
  change_5d: 0.015,
  change_7d: 0.015,
  change_20d: 0.015,
  avg_vol_20d: 1.5,
  rel_vol: 0.015,
  vol_trend_5d: 1.5,
  vol_trend_7d: 1.5,
  dollar_vol_20d: 2,
  ma_20: 0.015,
  ma_50: 0.015,
  ma_200: 0.015,
  pct_from_ma20: 0.015,
  pct_from_ma50: 0.015,
  pct_from_52w_high: 0.015,
  rsi_14: 0.15,
  atr_14: 0.015,
  atr_pct: 0.015,
  macd_hist: 0.0015,
  avg_range_pct: 0.15,
  gap_pct: 0.015,
};

type FixtureCase = {
  name: string;
  bars: Ohlcv;
  metrics: Record<string, number | string>;
  agents: Record<
    string,
    Record<string, { score: number; tier: string; reasons: string[]; flags: string[] }>
  >;
};

const REGIMES: AgentContext["regime"][] = [
  { trend: "bullish", risk: "on", leadership: "growth" },
  { trend: "bearish", risk: "off", leadership: "defensive" },
];

describe("compute_metrics parity", () => {
  for (const c of fixtures.cases as FixtureCase[]) {
    it(`matches Python for ${c.name}`, () => {
      const m = computeMetrics(c.name.toUpperCase(), c.bars);
      expect(m).not.toBeNull();
      for (const [field, tol] of Object.entries(TOL)) {
        const got = (m as unknown as Record<string, number>)[field];
        const want = c.metrics[field] as number;
        expect(
          Math.abs(got - want),
          `${c.name}.${field}: got ${got}, want ${want}`,
        ).toBeLessThanOrEqual(tol);
      }
    });
  }

  it("returns null for < 10 bars", () => {
    expect(computeMetrics("SHORT", fixtures.too_short.bars as Ohlcv)).toBeNull();
  });
});

describe("agent parity", () => {
  const benchmarks = fixtures.orchestrator.benchmarks as AgentContext["benchmarks"];

  for (const c of fixtures.cases as FixtureCase[]) {
    for (const [ri, regime] of REGIMES.entries()) {
      it(`matches Python agent scores for ${c.name} (regime ${ri})`, () => {
        const ctx: AgentContext = { benchmarks, regime };
        // Use the PYTHON metrics as agent input to isolate agent-logic parity
        // from tiny metric rounding drift.
        const m = c.metrics as unknown as Metrics;
        for (const agent of buildAgents(null)) {
          const got = agent.evaluate(m, ctx);
          const want = c.agents[`regime_${ri}`][agent.name];
          expect(got.score, `${c.name}/${agent.name} score`).toBeCloseTo(want.score, 6);
          expect(got.tier, `${c.name}/${agent.name} tier`).toBe(want.tier);
          expect(got.reasons, `${c.name}/${agent.name} reasons`).toEqual(want.reasons);
          expect(got.flags, `${c.name}/${agent.name} flags`).toEqual(want.flags);
        }
      });
    }
  }
});

describe("orchestrator parity", () => {
  it("reproduces composite ranking", () => {
    const { benchmarks, regime, expected } = fixtures.orchestrator;
    const inputs = (fixtures.cases as FixtureCase[]).map(
      (c) => c.metrics as unknown as Metrics,
    );
    const got = scoreRecords(inputs, {
      benchmarks: benchmarks as AgentContext["benchmarks"],
      regime: regime as AgentContext["regime"],
    });
    expect(got.length).toBe(expected.length);
    for (let i = 0; i < got.length; i++) {
      const g = got[i];
      const w = expected[i] as Record<string, unknown>;
      expect(g.ticker, `rank ${i}`).toBe(w.ticker);
      expect(g.composite_score).toBeCloseTo(w.composite_score as number, 1);
      expect(g.best_strategy).toBe(w.best_strategy);
      expect(g.top_reasons).toBe(w.top_reasons);
      expect(g.flags).toBe(w.flags);
    }
  });
});

describe("filters parity", () => {
  function scored() {
    const { benchmarks, regime } = fixtures.orchestrator;
    return scoreRecords(
      (fixtures.cases as FixtureCase[]).map((c) => c.metrics as unknown as Metrics),
      {
        benchmarks: benchmarks as AgentContext["benchmarks"],
        regime: regime as AgentContext["regime"],
      },
    );
  }

  it("default config keeps the same tickers", () => {
    const got = applyFilters(scored(), {});
    expect(got.map((r) => r.ticker)).toEqual(fixtures.filters.expected_tickers);
  });

  it("custom config keeps the same tickers", () => {
    const got = applyFilters(scored(), fixtures.filters_custom.config);
    expect(got.map((r) => r.ticker)).toEqual(fixtures.filters_custom.expected_tickers);
  });
});

describe("market regime", () => {
  it("classifies bullish/risk-on/growth", () => {
    const r = marketRegime({
      VOO: { ticker: "VOO", label: "", asset: "", change_7d: 1.5 },
      QQQ: { ticker: "QQQ", label: "", asset: "", change_7d: 3.0 },
      IWM: { ticker: "IWM", label: "", asset: "", change_7d: 2.0 },
      TLT: { ticker: "TLT", label: "", asset: "", change_7d: -1.0 },
      GLD: { ticker: "GLD", label: "", asset: "", change_7d: 0.0 },
    });
    expect(r).toEqual({ trend: "bullish", risk: "on", leadership: "growth" });
  });

  it("classifies bearish/risk-off/defensive", () => {
    const r = marketRegime({
      VOO: { ticker: "VOO", label: "", asset: "", change_7d: -2.0 },
      QQQ: { ticker: "QQQ", label: "", asset: "", change_7d: -3.0 },
      IWM: { ticker: "IWM", label: "", asset: "", change_7d: -2.5 },
      TLT: { ticker: "TLT", label: "", asset: "", change_7d: 1.0 },
      GLD: { ticker: "GLD", label: "", asset: "", change_7d: 0.5 },
    });
    expect(r).toEqual({ trend: "bearish", risk: "off", leadership: "defensive" });
  });

  it("empty benchmarks → mixed/neutral/broad", () => {
    expect(marketRegime({})).toEqual({ trend: "mixed", risk: "neutral", leadership: "broad" });
  });
});

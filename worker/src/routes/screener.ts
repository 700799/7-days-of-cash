// Screener routes — port of api/routes/screener.py.
//
// /cached, /top, /history, /share/:id read the cron-assembled screener_results.
// /run scores a custom ticker set live (≤ 40 to stay inside subrequest budget).
// /export streams the latest run as CSV.

import { Hono } from "hono";
import { z } from "zod";
import { marketRegime, type BenchmarkRow } from "../engine/benchmarks";
import { applyFilters, type FilterConfig } from "../engine/filters";
import { computeMetrics, type Metrics } from "../engine/metrics";
import { scoreRecords } from "../engine/orchestrator";
import { fetchChart } from "../lib/yahoo";
import type { AppContext, Env } from "../types";

// Live-run cap: each ticker costs one chart subrequest; keep headroom under
// the 50-subrequest free-plan budget.
const MAX_LIVE_TICKERS = 40;

const runSchema = z.object({
  tickers: z
    .array(z.string().transform((s) => s.trim().toUpperCase()))
    .max(MAX_LIVE_TICKERS + 1)
    .optional(),
  filters: z.record(z.unknown()).optional(),
  agents: z.array(z.string()).optional(),
});

export const screenerRoutes = new Hono<AppContext>();

async function loadBenchmarks(env: Env): Promise<Record<string, BenchmarkRow>> {
  const rows = await env.DB.prepare("SELECT * FROM benchmark_metrics").all<BenchmarkRow>();
  const out: Record<string, BenchmarkRow> = {};
  for (const b of rows.results ?? []) out[b.ticker] = b;
  return out;
}

function decorate(
  r: ReturnType<typeof scoreRecords>[number],
  benchmarks: Record<string, BenchmarkRow>,
) {
  return {
    ...r,
    score: r.composite_score,
    ret_7d: r.change_7d,
    momentum: r["score_momentum"],
    breakout: r["score_breakout"],
    volume: r["score_volume_surge"],
    rs: r["score_relative_strength"],
    mean_reversion: r["score_mean_reversion"],
    vs_voo: r.change_7d - (benchmarks["VOO"]?.change_7d ?? 0),
  };
}

screenerRoutes.post("/run", async (c) => {
  const parsed = runSchema.safeParse(await c.req.json().catch(() => ({})));
  if (!parsed.success) return c.json({ detail: "Invalid payload" }, 422);
  const { tickers, filters, agents } = parsed.data;

  if (!tickers || tickers.length === 0) {
    return c.json(
      { detail: "Provide up to 40 tickers. Full-universe results come from GET /api/screener/cached." },
      422,
    );
  }
  if (tickers.length > MAX_LIVE_TICKERS) {
    return c.json(
      {
        detail: `Live screener accepts up to ${MAX_LIVE_TICKERS} tickers. Use GET /api/screener/cached for the full universe.`,
      },
      413,
    );
  }

  const unique = [...new Set(tickers)].filter((t) => /^[A-Z][A-Z0-9.\-]{0,9}$/.test(t));
  const records: Metrics[] = [];
  for (let i = 0; i < unique.length; i += 8) {
    const batch = unique.slice(i, i + 8);
    const settled = await Promise.all(
      batch.map(async (t) => {
        const bars = await fetchChart(t, "35d");
        return bars ? computeMetrics(t, bars) : null;
      }),
    );
    records.push(...settled.filter((m): m is Metrics => m !== null));
  }

  const benchmarks = await loadBenchmarks(c.env);
  const regime = marketRegime(benchmarks);
  let scored = scoreRecords(records, { benchmarks, regime, agentNames: agents ?? null });
  if (filters && Object.keys(filters).length > 0) {
    scored = applyFilters(scored, filters as FilterConfig);
  }

  return c.json({
    regime,
    benchmarks: Object.values(benchmarks),
    results: scored.map((r) => decorate(r, benchmarks)),
    ran_at: new Date().toISOString(),
  });
});

async function latestResult(env: Env): Promise<{ ran_at: string; payload: string } | null> {
  return env.DB.prepare(
    "SELECT ran_at, payload FROM screener_results ORDER BY ran_at DESC LIMIT 1",
  ).first<{ ran_at: string; payload: string }>();
}

screenerRoutes.get("/cached", async (c) => {
  const row = await latestResult(c.env);
  if (!row) return c.json({ detail: "No cached results yet. The refresh cron will populate them." }, 404);
  const payload = JSON.parse(row.payload);
  return c.json({
    regime: payload.regime ?? {},
    benchmarks: payload.benchmarks ?? [],
    results: payload.results ?? [],
    ran_at: payload.ran_at ?? row.ran_at,
  });
});

screenerRoutes.get("/top", async (c) => {
  const n = Number(c.req.query("n") ?? 10);
  if (!Number.isInteger(n) || n < 1 || n > 100) {
    return c.json({ detail: "n must be between 1 and 100" }, 400);
  }
  const row = await latestResult(c.env);
  if (!row) return c.json([]);
  const results = (JSON.parse(row.payload).results ?? []) as Record<string, unknown>[];
  return c.json(
    results.slice(0, n).map((r) => ({
      ticker: r.ticker,
      ret_7d: r.ret_7d ?? r.change_7d,
      score: r.score ?? r.composite_score,
      best_strategy: r.best_strategy,
      vs_voo: r.vs_voo,
    })),
  );
});

screenerRoutes.get("/history", async (c) => {
  const days = Math.max(1, Math.min(Number(c.req.query("days") ?? 7) || 7, 30));
  const rows = await c.env.DB.prepare(
    `SELECT id, ran_at, payload FROM screener_results
     WHERE ran_at >= datetime('now', '-${days} days') ORDER BY ran_at DESC`,
  ).all<{ id: number; ran_at: string; payload: string }>();
  return c.json(
    (rows.results ?? []).map((row) => {
      const payload = JSON.parse(row.payload);
      const results = (payload.results ?? []) as { ticker: string }[];
      return {
        id: row.id,
        ran_at: payload.ran_at ?? row.ran_at,
        results_count: results.length,
        top_5_tickers: results.slice(0, 5).map((r) => r.ticker),
        error: payload.error ?? null,
      };
    }),
  );
});

screenerRoutes.get("/share/:id", async (c) => {
  const id = Number(c.req.param("id"));
  if (!Number.isInteger(id) || id < 1) return c.json({ detail: "Invalid id" }, 400);
  const row = await c.env.DB.prepare(
    "SELECT ran_at, payload FROM screener_results WHERE id = ?",
  )
    .bind(id)
    .first<{ ran_at: string; payload: string }>();
  if (!row) return c.json({ detail: "Screener result not found." }, 404);
  const payload = JSON.parse(row.payload);
  const results = (payload.results ?? []) as Record<string, unknown>[];
  return c.json({
    id,
    ran_at: payload.ran_at ?? row.ran_at,
    results_count: results.length,
    top_picks: results.slice(0, 10),
  });
});

screenerRoutes.get("/export", async (c) => {
  const row = await latestResult(c.env);
  if (!row) return c.json({ detail: "No screener results to export yet." }, 404);
  const payload = JSON.parse(row.payload);
  const results = (payload.results ?? []) as Record<string, unknown>[];
  if (results.length === 0) return c.json({ detail: "No results in latest screener run." }, 404);

  const lead = [
    "ticker", "price", "ret_7d", "change_7d", "score", "composite_score",
    "momentum", "breakout", "volume", "rs", "mean_reversion", "best_strategy", "vs_voo",
  ];
  const extras = Object.keys(results[0]).filter((k) => !lead.includes(k)).sort();
  const fields = [...lead, ...extras];

  const esc = (v: unknown): string => {
    if (v === null || v === undefined) return "";
    const s = String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const csv = [
    fields.join(","),
    ...results.map((r) => fields.map((f) => esc(r[f])).join(",")),
  ].join("\n");

  const date = (payload.ran_at ?? row.ran_at ?? "").slice(0, 10).replace(/-/g, "") || "latest";
  return c.body(csv, 200, {
    "Content-Type": "text/csv; charset=utf-8",
    "Content-Disposition": `attachment; filename="best7daysmula_screener_${date}.csv"`,
  });
});

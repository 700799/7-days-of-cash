import { Pool } from "pg";

export type Breadth = {
  n?: number;
  pct_above_ma20?: number;
  pct_above_ma50?: number;
  pct_pos_7d?: number;
  median_rel_vol?: number;
  pct_rsi_hot?: number;
  new_52w_highs?: number;
  herd_counts?: Record<string, number>;
};

export type HerdInfo = {
  herd_state?: string;
  herd_score?: number;
  herd_reasons?: string[];
  stop_suggest?: number | null;
  trim_zone?: number | null;
  inputs?: Record<string, number | boolean>;
};

export type Run = {
  id: number;
  run_at: string;
  regime: { trend?: string; risk?: string; leadership?: string } | null;
  breadth: Breadth | null;
  universe_size: number;
  result_count: number;
  elapsed_sec: number;
  agent_names: string[];
};

export type Result = {
  rank: number;
  ticker: string;
  price: number | null;
  change_5d: number | null;
  change_7d: number | null;
  change_20d: number | null;
  rel_vol: number | null;
  rsi_14: number | null;
  composite_score: number | null;
  best_strategy: string | null;
  top_reasons: string | null;
  flags: string | null;
  herd_state: string | null;
  herd: HerdInfo | null;
  prev_herd_state: string | null;
};

const globalForPool = globalThis as unknown as { _pool?: Pool };

function getPool(): Pool {
  const cs = process.env.DATABASE_URL;
  if (!cs) throw new Error("DATABASE_URL is not set");
  if (!globalForPool._pool) {
    const isLocal = /localhost|127\.0\.0\.1/.test(cs);
    globalForPool._pool = new Pool({
      connectionString: cs,
      max: 3,
      // Neon serves a valid public cert, but disabling strict verification
      // avoids handshake failures across providers/runtimes for this v1.
      ssl: isLocal ? false : { rejectUnauthorized: false },
    });
  }
  return globalForPool._pool;
}

function num(v: unknown): number | null {
  if (v === null || v === undefined) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

export async function getLatestRun(): Promise<Run | null> {
  const { rows } = await getPool().query(
    `SELECT id, run_at, regime, breadth, universe_size, result_count, elapsed_sec, agent_names
       FROM screener_runs
      ORDER BY run_at DESC
      LIMIT 1`
  );
  if (rows.length === 0) return null;
  const r = rows[0];
  return {
    id: Number(r.id),
    run_at: new Date(r.run_at).toISOString(),
    regime: r.regime ?? null,
    breadth: r.breadth ?? null,
    universe_size: Number(r.universe_size),
    result_count: Number(r.result_count),
    elapsed_sec: Number(r.elapsed_sec),
    agent_names: r.agent_names ?? [],
  };
}

export async function getResults(runId: number): Promise<Result[]> {
  // Joins each ticker against the immediately-previous run so the UI can
  // show herd-state flips ("↑ was EARLY"). LEFT JOIN: tickers new to the
  // board (or a missing previous run) get prev_herd_state = null.
  const { rows } = await getPool().query(
    `WITH prev AS (
       SELECT id FROM screener_runs
        WHERE run_at < (SELECT run_at FROM screener_runs WHERE id = $1)
        ORDER BY run_at DESC
        LIMIT 1
     )
     SELECT r.rank, r.ticker, r.price, r.change_5d, r.change_7d, r.change_20d,
            r.rel_vol, r.rsi_14, r.composite_score, r.best_strategy, r.top_reasons,
            r.flags, r.herd_state, r.herd, p.herd_state AS prev_herd_state
       FROM screener_results r
       LEFT JOIN screener_results p
              ON p.run_id = (SELECT id FROM prev) AND p.ticker = r.ticker
      WHERE r.run_id = $1
      ORDER BY r.rank`,
    [runId]
  );
  return rows.map((r) => ({
    rank: Number(r.rank),
    ticker: r.ticker,
    price: num(r.price),
    change_5d: num(r.change_5d),
    change_7d: num(r.change_7d),
    change_20d: num(r.change_20d),
    rel_vol: num(r.rel_vol),
    rsi_14: num(r.rsi_14),
    composite_score: num(r.composite_score),
    best_strategy: r.best_strategy ?? null,
    top_reasons: r.top_reasons ?? null,
    flags: r.flags ?? null,
    herd_state: r.herd_state ?? null,
    herd: r.herd && Object.keys(r.herd).length > 0 ? r.herd : null,
    prev_herd_state: r.prev_herd_state ?? null,
  }));
}

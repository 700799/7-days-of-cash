import { Pool } from "pg";

export type Run = {
  id: number;
  run_at: string;
  regime: { trend?: string; risk?: string; leadership?: string } | null;
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
    `SELECT id, run_at, regime, universe_size, result_count, elapsed_sec, agent_names
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
    universe_size: Number(r.universe_size),
    result_count: Number(r.result_count),
    elapsed_sec: Number(r.elapsed_sec),
    agent_names: r.agent_names ?? [],
  };
}

export async function getResults(runId: number): Promise<Result[]> {
  const { rows } = await getPool().query(
    `SELECT rank, ticker, price, change_5d, change_7d, change_20d,
            rel_vol, rsi_14, composite_score, best_strategy, top_reasons, flags
       FROM screener_results
      WHERE run_id = $1
      ORDER BY rank`,
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
  }));
}

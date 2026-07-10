// Mover summaries — port of api/routes/movers.py + api/movers.py heuristic.
// Uses D1 ticker_metrics (closes_10d) instead of live OHLCV fetches; falls
// back to a single chart call for symbols outside the screened universe.

import { Hono } from "hono";
import { computeMetrics } from "../engine/metrics";
import { fetchChart, fetchNews } from "../lib/yahoo";
import type { AppContext, Env } from "../types";

const MOVERS_TTL_SEC = 4 * 3600;

interface Mover {
  symbol: string;
  price: number | null;
  change_7d: number | null;
  change_1d: number | null;
  summary: string;
  headlines: { title: string; link: string; publisher: string; published_at: string | null }[];
}

const arrowFor = (change: number): string => (change > 0.5 ? "▲" : change < -0.5 ? "▼" : "▬");
const fmtChange = (v: number): string => `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`;
const pctChange = (latest: number, prior: number): number =>
  prior > 0 ? (latest / prior - 1) * 100 : 0;

async function loadCloses(env: Env, symbol: string): Promise<number[] | null> {
  const row = await env.DB.prepare(
    `SELECT closes_10d FROM ticker_metrics WHERE ticker = ?
     AND fetched_at >= datetime('now', '-8 hours')`,
  )
    .bind(symbol)
    .first<{ closes_10d: string }>();
  if (row?.closes_10d) return JSON.parse(row.closes_10d) as number[];

  const bars = await fetchChart(symbol, "10d");
  if (!bars) return null;
  // Opportunistically cache the metrics row so the next call is free.
  const m = computeMetrics(symbol, bars);
  if (m) {
    await env.DB.prepare(
      `INSERT INTO ticker_metrics (ticker, price, change_7d, closes_10d, fetched_at)
       VALUES (?, ?, ?, ?, datetime('now'))
       ON CONFLICT (ticker) DO UPDATE SET price=excluded.price, change_7d=excluded.change_7d,
         closes_10d=excluded.closes_10d, fetched_at=datetime('now')`,
    )
      .bind(symbol, m.price, m.change_7d, JSON.stringify(bars.close.slice(-10)))
      .run();
  }
  return bars.close.slice(-10);
}

async function buildMover(env: Env, symbol: string): Promise<Mover> {
  symbol = symbol.toUpperCase();
  const [closes, news] = await Promise.all([
    loadCloses(env, symbol),
    fetchNews(symbol, 2).catch(() => []),
  ]);
  const headlines = news.slice(0, 2).map((n) => ({
    title: n.title,
    link: n.link,
    publisher: n.publisher,
    published_at: n.published_at,
  }));

  if (!closes || closes.length === 0) {
    return {
      symbol,
      price: null,
      change_7d: null,
      change_1d: null,
      summary: `${symbol}: No recent activity.`,
      headlines,
    };
  }

  const n = closes.length;
  const price = closes[n - 1];
  const lb7 = Math.min(7, n - 1);
  const change7 = pctChange(price, closes[n - 1 - lb7]);
  const change1 = n >= 2 ? pctChange(price, closes[n - 2]) : 0;

  const arrow = arrowFor(change7);
  const chgStr = fmtChange(change7);
  let summary = `${symbol} ${arrow} ${chgStr} over 7d ($${price.toFixed(2)}).`;
  if (headlines.length === 2) {
    summary += ` Headlines: '${headlines[0].title}'. '${headlines[1].title}'.`;
  } else if (headlines.length === 1) {
    summary += ` Headlines: '${headlines[0].title}'.`;
  }

  return {
    symbol,
    price: Math.round(price * 100) / 100,
    change_7d: Math.round(change7 * 100) / 100,
    change_1d: Math.round(change1 * 100) / 100,
    summary,
    headlines,
  };
}

export const moverRoutes = new Hono<AppContext>();

moverRoutes.get("/", async (c) => {
  const raw = c.req.query("symbols") ?? "";
  const symbols = [
    ...new Set(
      raw
        .split(",")
        .map((s) => s.trim().toUpperCase())
        .filter((s) => /^[A-Z][A-Z0-9.\-]{0,9}$/.test(s)),
    ),
  ].slice(0, 50);
  if (symbols.length === 0) return c.json([]);

  const cacheKey = `movers:${symbols.sort().join(",")}`;
  const cached = await c.env.DB.prepare(
    `SELECT payload FROM movers_cache WHERE cache_key = ?
     AND fetched_at >= datetime('now', '-${MOVERS_TTL_SEC} seconds')`,
  )
    .bind(cacheKey)
    .first<{ payload: string }>();
  if (cached) return c.json(JSON.parse(cached.payload));

  const movers: Mover[] = [];
  for (let i = 0; i < symbols.length; i += 8) {
    const batch = symbols.slice(i, i + 8);
    movers.push(...(await Promise.all(batch.map((s) => buildMover(c.env, s)))));
  }

  await c.env.DB.prepare(
    `INSERT INTO movers_cache (cache_key, payload, fetched_at) VALUES (?, ?, datetime('now'))
     ON CONFLICT (cache_key) DO UPDATE SET payload=excluded.payload, fetched_at=datetime('now')`,
  )
    .bind(cacheKey, JSON.stringify(movers))
    .run();
  return c.json(movers);
});

moverRoutes.get("/:symbol", async (c) => {
  const symbol = (c.req.param("symbol") ?? "").toUpperCase();
  if (!/^[A-Z][A-Z0-9.\-]{0,9}$/.test(symbol)) return c.json({ detail: "Invalid symbol" }, 422);
  return c.json(await buildMover(c.env, symbol));
});

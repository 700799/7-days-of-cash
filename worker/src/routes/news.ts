// News routes — port of api/routes/news.py. D1-cached, Yahoo-backed.

import { Hono } from "hono";
import { fetchNews, type NewsItem } from "../lib/yahoo";
import type { AppContext, Env } from "../types";

const TICKER_TTL_SEC = 900; // 15 min
const TRENDING_TTL_SEC = 3600; // 1 h

export const newsRoutes = new Hono<AppContext>();

async function cachedNews(
  env: Env,
  cacheKey: string,
  ttlSec: number,
  fetcher: () => Promise<NewsItem[]>,
): Promise<NewsItem[]> {
  const row = await env.DB.prepare(
    `SELECT payload FROM news_cache WHERE cache_key = ?
     AND fetched_at >= datetime('now', '-${ttlSec} seconds')`,
  )
    .bind(cacheKey)
    .first<{ payload: string }>();
  if (row) return JSON.parse(row.payload) as NewsItem[];

  const items = await fetcher();
  await env.DB.prepare(
    `INSERT INTO news_cache (cache_key, payload, fetched_at) VALUES (?, ?, datetime('now'))
     ON CONFLICT (cache_key) DO UPDATE SET payload=excluded.payload, fetched_at=datetime('now')`,
  )
    .bind(cacheKey, JSON.stringify(items))
    .run();
  return items;
}

newsRoutes.get("/ticker/:symbol", async (c) => {
  const symbol = (c.req.param("symbol") ?? "").toUpperCase();
  if (!/^[A-Z][A-Z0-9.\-^]{0,9}$/.test(symbol)) {
    return c.json({ detail: "Invalid symbol" }, 422);
  }
  const items = await cachedNews(c.env, `ticker:${symbol}`, TICKER_TTL_SEC, () =>
    fetchNews(symbol, 8),
  );
  return c.json(items);
});

newsRoutes.get("/market", async (c) => {
  const items = await cachedNews(c.env, "market", TICKER_TTL_SEC, () => fetchNews("^GSPC", 8));
  return c.json(items);
});

newsRoutes.get("/trending", async (c) => {
  // The cron keeps this warm; fall back to a live pull when cold.
  const items = await cachedNews(c.env, "trending", TRENDING_TTL_SEC, async () => {
    const pools = await Promise.all(["^GSPC", "^IXIC", "^DJI"].map((q) => fetchNews(q, 8)));
    const all = pools.flat();
    all.sort((a, b) => (b.published_at ?? "").localeCompare(a.published_at ?? ""));
    const seen = new Set<string>();
    return all
      .filter((item) => {
        const urlKey = item.link.toLowerCase();
        const titleKey = item.title.toLowerCase();
        if (!titleKey || seen.has(urlKey) || seen.has(titleKey)) return false;
        seen.add(urlKey);
        seen.add(titleKey);
        return true;
      })
      .slice(0, 5);
  });
  return c.json(items.slice(0, 5));
});

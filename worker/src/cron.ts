// Scheduled work: rolling ticker refresh, screener assembly, price alerts,
// and daily email digests. Replaces the HTTP /api/cron/* endpoints — the
// scheduled() handler is internal-only, so no CRON_SECRET is needed.
//
// Free-plan budget: 50 subrequests per invocation. Each 5-minute tick spends
//   ~SLICE_SIZE chart fetches + up to ~10 benchmark/news/email calls.

import { BENCHMARK_META, type BenchmarkRow, benchmarkChanges, marketRegime } from "./engine/benchmarks";
import { applyFilters } from "./engine/filters";
import { computeMetrics, type Metrics } from "./engine/metrics";
import { scoreRecords } from "./engine/orchestrator";
import { getExtendedTickers } from "./engine/universe";
import { sendEmail } from "./lib/email";
import { fetchChart, fetchNews } from "./lib/yahoo";
import type { Env } from "./types";

const SLICE_SIZE = 35; // chart fetches per tick; leaves headroom in the 50-subrequest budget
const FRESH_HOURS = 5; // a metric row older than this is stale for assembly
const ASSEMBLY_MIN_COVERAGE = 0.7; // assemble once ≥70% of the universe is fresh
const TRENDING_INDICES = ["^GSPC", "^IXIC", "^DJI"];

export async function runScheduled(env: Env, cron: string): Promise<void> {
  if (cron === "0 13 * * *") {
    await runDigests(env);
    return;
  }
  await runSliceRefresh(env);
}

// ---------------------------------------------------------------------------
// Rolling slice refresh
// ---------------------------------------------------------------------------

async function runSliceRefresh(env: Env): Promise<void> {
  const universe = getExtendedTickers();
  const state = await env.DB.prepare(
    "SELECT cursor, universe_size FROM refresh_state WHERE id = 1",
  ).first<{ cursor: number; universe_size: number }>();
  let cursor = state?.cursor ?? 0;
  if ((state?.universe_size ?? 0) !== universe.length || cursor >= universe.length) {
    cursor = cursor % universe.length || 0;
  }

  const slice = universe.slice(cursor, cursor + SLICE_SIZE);
  const wrapped =
    slice.length < SLICE_SIZE ? [...slice, ...universe.slice(0, SLICE_SIZE - slice.length)] : slice;
  const nextCursor = (cursor + SLICE_SIZE) % universe.length;

  // Fetch charts with limited concurrency (8 at a time) to be polite to Yahoo.
  const results: { ticker: string; metrics: Metrics; closes10: number[] }[] = [];
  for (let i = 0; i < wrapped.length; i += 8) {
    const batch = wrapped.slice(i, i + 8);
    const settled = await Promise.all(
      batch.map(async (ticker) => {
        const bars = await fetchChart(ticker, "35d");
        if (!bars) return null;
        const m = computeMetrics(ticker, bars);
        if (!m) return null;
        return { ticker, metrics: m, closes10: bars.close.slice(-10) };
      }),
    );
    results.push(...settled.filter((r): r is NonNullable<typeof r> => r !== null));
  }

  // Upsert metric rows in one batch.
  if (results.length > 0) {
    const stmt = env.DB.prepare(
      `INSERT INTO ticker_metrics (
         ticker, price, change_5d, change_7d, change_20d, avg_vol_20d, rel_vol,
         vol_trend_5d, vol_trend_7d, dollar_vol_20d, ma_20, ma_50, ma_200,
         pct_from_ma20, pct_from_ma50, pct_from_52w_high, rsi_14, atr_14,
         atr_pct, macd_hist, avg_range_pct, gap_pct, closes_10d, fetched_at
       ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, datetime('now'))
       ON CONFLICT (ticker) DO UPDATE SET
         price=excluded.price, change_5d=excluded.change_5d, change_7d=excluded.change_7d,
         change_20d=excluded.change_20d, avg_vol_20d=excluded.avg_vol_20d, rel_vol=excluded.rel_vol,
         vol_trend_5d=excluded.vol_trend_5d, vol_trend_7d=excluded.vol_trend_7d,
         dollar_vol_20d=excluded.dollar_vol_20d, ma_20=excluded.ma_20, ma_50=excluded.ma_50,
         ma_200=excluded.ma_200, pct_from_ma20=excluded.pct_from_ma20,
         pct_from_ma50=excluded.pct_from_ma50, pct_from_52w_high=excluded.pct_from_52w_high,
         rsi_14=excluded.rsi_14, atr_14=excluded.atr_14, atr_pct=excluded.atr_pct,
         macd_hist=excluded.macd_hist, avg_range_pct=excluded.avg_range_pct,
         gap_pct=excluded.gap_pct, closes_10d=excluded.closes_10d, fetched_at=datetime('now')`,
    );
    await env.DB.batch(
      results.map(({ metrics: m, closes10 }) =>
        stmt.bind(
          m.ticker, m.price, m.change_5d, m.change_7d, m.change_20d, m.avg_vol_20d,
          m.rel_vol, m.vol_trend_5d, m.vol_trend_7d, m.dollar_vol_20d, m.ma_20, m.ma_50,
          m.ma_200, m.pct_from_ma20, m.pct_from_ma50, m.pct_from_52w_high, m.rsi_14,
          m.atr_14, m.atr_pct, m.macd_hist, m.avg_range_pct, m.gap_pct,
          JSON.stringify(closes10),
        ),
      ),
    );
  }

  await env.DB.prepare(
    `UPDATE refresh_state SET cursor = ?, universe_size = ?, last_slice_at = datetime('now') WHERE id = 1`,
  )
    .bind(nextCursor, universe.length)
    .run();

  // Refresh benchmarks every tick (7 subrequests) — cheap and keeps regime live.
  await refreshBenchmarks(env);

  // Rotate one trending-news refresh per tick (1 subrequest, 1h TTL handles the rest).
  await refreshTrendingIfStale(env);

  console.log(
    `slice refresh: cursor ${cursor}→${nextCursor}, fetched ${results.length}/${wrapped.length}`,
  );

  await maybeAssemble(env, universe.length);
}

async function refreshBenchmarks(env: Env): Promise<Record<string, BenchmarkRow>> {
  const rows: Record<string, BenchmarkRow> = {};
  await Promise.all(
    BENCHMARK_META.map(async (meta) => {
      const bars = await fetchChart(meta.ticker, "35d");
      if (!bars || bars.close.length < 8) return;
      const changes = benchmarkChanges(bars.close);
      if (!changes) return;
      rows[meta.ticker] = { ...meta, ...changes };
    }),
  );
  const stmts = Object.values(rows).map((b) =>
    env.DB.prepare(
      `INSERT INTO benchmark_metrics (ticker, label, asset, price, change_5d, change_7d, change_20d, fetched_at)
       VALUES (?,?,?,?,?,?,?, datetime('now'))
       ON CONFLICT (ticker) DO UPDATE SET price=excluded.price, change_5d=excluded.change_5d,
         change_7d=excluded.change_7d, change_20d=excluded.change_20d, fetched_at=datetime('now')`,
    ).bind(b.ticker, b.label, b.asset, b.price, b.change_5d, b.change_7d, b.change_20d),
  );
  if (stmts.length) await env.DB.batch(stmts);
  return rows;
}

async function refreshTrendingIfStale(env: Env): Promise<void> {
  const row = await env.DB.prepare(
    `SELECT 1 FROM news_cache WHERE cache_key = 'trending'
     AND fetched_at >= datetime('now', '-3600 seconds')`,
  ).first();
  if (row) return;

  const pools = await Promise.all(TRENDING_INDICES.map((idx) => fetchNews(idx, 8)));
  const all = pools.flat();
  all.sort((a, b) => (b.published_at ?? "").localeCompare(a.published_at ?? ""));
  const seen = new Set<string>();
  const deduped = all.filter((item) => {
    const urlKey = item.link.toLowerCase();
    const titleKey = item.title.toLowerCase();
    if (!titleKey || seen.has(urlKey) || seen.has(titleKey)) return false;
    seen.add(urlKey);
    seen.add(titleKey);
    return true;
  });
  await env.DB.prepare(
    `INSERT INTO news_cache (cache_key, payload, fetched_at) VALUES ('trending', ?, datetime('now'))
     ON CONFLICT (cache_key) DO UPDATE SET payload=excluded.payload, fetched_at=datetime('now')`,
  )
    .bind(JSON.stringify(deduped.slice(0, 5)))
    .run();
}

// ---------------------------------------------------------------------------
// Screener assembly — score all fresh metrics, persist a screener_results row
// ---------------------------------------------------------------------------

async function maybeAssemble(env: Env, universeSize: number): Promise<void> {
  const fresh = await env.DB.prepare(
    `SELECT * FROM ticker_metrics WHERE fetched_at >= datetime('now', '-${FRESH_HOURS} hours')`,
  ).all<Record<string, unknown>>();
  const records = (fresh.results ?? []) as unknown as Metrics[];
  if (records.length < universeSize * ASSEMBLY_MIN_COVERAGE) {
    console.log(`assembly skipped: ${records.length}/${universeSize} fresh`);
    return;
  }

  const benchRows = await env.DB.prepare("SELECT * FROM benchmark_metrics").all<BenchmarkRow>();
  const benchmarks: Record<string, BenchmarkRow> = {};
  for (const b of benchRows.results ?? []) benchmarks[b.ticker] = b;
  const regime = marketRegime(benchmarks);

  const scored = scoreRecords(records, { benchmarks, regime });
  // Normalize for the frontend: expose score/ret_7d aliases used by the UI.
  const filtered = applyFilters(scored, {}).map((r) => ({
    ...r,
    score: r.composite_score,
    ret_7d: r.change_7d,
    momentum: r["score_momentum"],
    breakout: r["score_breakout"],
    volume: r["score_volume_surge"],
    rs: r["score_relative_strength"],
    mean_reversion: r["score_mean_reversion"],
    vs_voo: r.change_7d - (benchmarks["VOO"]?.change_7d ?? 0),
  }));

  const payload = {
    ran_at: new Date().toISOString(),
    results_count: filtered.length,
    results: filtered,
    regime,
    benchmarks: Object.values(benchmarks),
    error: null,
  };
  await env.DB.prepare("INSERT INTO screener_results (ran_at, payload) VALUES (datetime('now'), ?)")
    .bind(JSON.stringify(payload))
    .run();
  // Keep only the last 200 runs (~30 days at one per 4h-ish assembly cadence).
  await env.DB.prepare(
    `DELETE FROM screener_results WHERE id NOT IN
       (SELECT id FROM screener_results ORDER BY ran_at DESC LIMIT 200)`,
  ).run();
  await env.DB.prepare(
    "UPDATE refresh_state SET last_assembly_at = datetime('now') WHERE id = 1",
  ).run();
  console.log(`assembly complete: ${filtered.length} leaders from ${records.length} fresh tickers`);

  await checkPriceAlerts(env);
}

// ---------------------------------------------------------------------------
// Price alerts
// ---------------------------------------------------------------------------

async function checkPriceAlerts(env: Env): Promise<void> {
  const alerts = await env.DB.prepare(
    `SELECT pa.id, pa.user_id, pa.symbol, pa.condition, pa.target, u.email,
            tm.price
     FROM price_alerts pa
     JOIN users u ON u.id = pa.user_id
     LEFT JOIN ticker_metrics tm ON tm.ticker = pa.symbol
     WHERE pa.triggered = 0 AND tm.price IS NOT NULL`,
  ).all<{
    id: number;
    user_id: string;
    symbol: string;
    condition: string;
    target: number;
    email: string;
    price: number;
  }>();

  for (const a of alerts.results ?? []) {
    const hit =
      (a.condition === "above" && a.price >= a.target) ||
      (a.condition === "below" && a.price <= a.target);
    if (!hit) continue;

    const arrow = a.condition === "above" ? "▲" : "▼";
    const subject = `[Best7DaysMula] ${a.symbol} ${arrow} $${a.target.toFixed(2)} alert triggered`;
    const html =
      `<!DOCTYPE html><html><body style="background:#000;color:#22ff88;font-family:monospace;">` +
      `<h2>${a.symbol} price alert triggered</h2>` +
      `<p>Current price: <strong>$${a.price.toFixed(2)}</strong></p>` +
      `<p>Your alert: ${a.condition} $${a.target.toFixed(2)}</p>` +
      `<p><a href="https://finance.yahoo.com/quote/${a.symbol}" style="color:#22ff88;">View on Yahoo Finance</a></p>` +
      `</body></html>`;
    const text = `${a.symbol} ${arrow} $${a.target.toFixed(2)} — current price $${a.price.toFixed(2)}`;

    const sent = await sendEmail(env, a.email, subject, html, text);
    if (sent) {
      await env.DB.prepare("UPDATE price_alerts SET triggered = 1 WHERE id = ?").bind(a.id).run();
    }
  }
}

// ---------------------------------------------------------------------------
// Daily digest (13:00 UTC; weekly = Mondays)
// ---------------------------------------------------------------------------

async function runDigests(env: Env): Promise<void> {
  const isMonday = new Date().getUTCDay() === 1;
  const users = await env.DB.prepare(
    `SELECT u.id, u.email, up.digest_frequency, up.digest_email
     FROM users u JOIN user_preferences up ON up.user_id = u.id
     WHERE up.digest_frequency IN ('daily', 'weekly')`,
  ).all<{ id: string; email: string; digest_frequency: string; digest_email: string | null }>();

  for (const u of users.results ?? []) {
    if (u.digest_frequency === "weekly" && !isMonday) continue;
    try {
      const { subject, html, text } = await buildDigest(env, u.id, u.digest_frequency);
      const ok = await sendEmail(env, u.digest_email || u.email, subject, html, text);
      if (ok) {
        await env.DB.prepare(
          "UPDATE user_preferences SET last_sent_at = datetime('now') WHERE user_id = ?",
        )
          .bind(u.id)
          .run();
      }
    } catch (e) {
      console.warn(`digest failed for ${u.id}: ${e}`);
    }
  }
}

async function buildDigest(
  env: Env,
  userId: string,
  frequency: string,
): Promise<{ subject: string; html: string; text: string }> {
  const date = new Date().toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
    timeZone: "UTC",
  });
  const freqLabel = frequency.charAt(0).toUpperCase() + frequency.slice(1);
  const subject = `Best7DaysMula ${freqLabel} Digest — ${date}`;

  // Trending (cached)
  const trendingRow = await env.DB.prepare(
    "SELECT payload FROM news_cache WHERE cache_key = 'trending'",
  ).first<{ payload: string }>();
  const trending: { title: string; link: string; publisher: string }[] = trendingRow
    ? JSON.parse(trendingRow.payload).slice(0, 5)
    : [];

  // Watchlist movers (from ticker_metrics — no live fetches in the digest path)
  const watch = await env.DB.prepare(
    `SELECT w.symbol, tm.price, tm.change_7d
     FROM watchlists w LEFT JOIN ticker_metrics tm ON tm.ticker = w.symbol
     WHERE w.user_id = ? LIMIT 25`,
  )
    .bind(userId)
    .all<{ symbol: string; price: number | null; change_7d: number | null }>();

  const moverLines = (watch.results ?? []).map((w) => {
    if (w.price == null || w.change_7d == null) return `${w.symbol}: No recent activity.`;
    const arrow = w.change_7d > 0.5 ? "▲" : w.change_7d < -0.5 ? "▼" : "▬";
    const chg = `${w.change_7d >= 0 ? "+" : ""}${w.change_7d.toFixed(1)}%`;
    return `${w.symbol} ${arrow} ${chg} over 7d ($${w.price.toFixed(2)}).`;
  });

  // Screener leaders (latest cached run)
  const leaderRow = await env.DB.prepare(
    "SELECT payload FROM screener_results ORDER BY ran_at DESC LIMIT 1",
  ).first<{ payload: string }>();
  const leaders: { ticker: string; change_7d: number }[] = leaderRow
    ? JSON.parse(leaderRow.payload).results.slice(0, 5)
    : [];

  const quote = (s: string): string => `https://finance.yahoo.com/quote/${s}`;
  const sectionStyle = "color:#22ff88;font-family:monospace;";

  const html =
    `<!DOCTYPE html><html><body style="background:#000;${sectionStyle}padding:16px;">` +
    `<h2 style="${sectionStyle}">&gt; MARKET TRENDING</h2><ul>` +
    trending
      .map((t) => `<li><a href="${t.link}" style="color:#8aff9f;">${t.title}</a> — ${t.publisher}</li>`)
      .join("") +
    `</ul><h2 style="${sectionStyle}">&gt; YOUR WATCHLIST MOVERS</h2><ul>` +
    (watch.results ?? [])
      .map((w, i) => `<li><a href="${quote(w.symbol)}" style="color:#8aff9f;">${moverLines[i]}</a></li>`)
      .join("") +
    `</ul><h2 style="${sectionStyle}">&gt; SCREENER LEADERS</h2><ul>` +
    leaders
      .map(
        (l) =>
          `<li><a href="${quote(l.ticker)}" style="color:#8aff9f;">${l.ticker}: +${l.change_7d?.toFixed(1)}% 7d</a></li>`,
      )
      .join("") +
    `</ul><p style="color:#6acc7e;font-size:12px;">Screener refreshes continuously. Not financial advice.</p>` +
    `</body></html>`;

  const text = [
    "> MARKET TRENDING",
    ...trending.map((t) => `- ${t.title} (${t.publisher})`),
    "",
    "> YOUR WATCHLIST MOVERS",
    ...moverLines.map((l) => `- ${l}`),
    "",
    "> SCREENER LEADERS",
    ...leaders.map((l) => `- ${l.ticker}: +${l.change_7d?.toFixed(1)}% 7d`),
  ].join("\n");

  return { subject, html, text };
}

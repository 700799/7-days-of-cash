// Best7DaysMula Worker — API (Hono) + static assets + scheduled jobs.
//
// /api/* is handled here (run_worker_first in wrangler.toml); everything else
// falls through to the static Next.js export via the ASSETS binding.

import { Hono } from "hono";
import { runScheduled } from "./cron";
import {
  bodySizeLimit,
  csrfOriginCheck,
  securityHeaders,
  sessionMiddleware,
} from "./middleware";
import { alertRoutes } from "./routes/alerts";
import { authRoutes } from "./routes/auth";
import { moverRoutes } from "./routes/movers";
import { newsRoutes } from "./routes/news";
import { preferenceRoutes } from "./routes/preferences";
import { screenerRoutes } from "./routes/screener";
import { tickerRoutes } from "./routes/tickers";
import type { AppContext, Env } from "./types";

const app = new Hono<AppContext>();

app.use("*", securityHeaders);
app.use("/api/*", bodySizeLimit);
app.use("/api/*", csrfOriginCheck);
app.use("/api/*", sessionMiddleware);

app.route("/api/auth", authRoutes);
app.route("/api/tickers", tickerRoutes);
app.route("/api/news", newsRoutes);
app.route("/api/movers", moverRoutes);
app.route("/api/screener", screenerRoutes);
app.route("/api/preferences", preferenceRoutes);
app.route("/api/alerts", alertRoutes);

app.get("/api/health", (c) => c.json({ status: "ok" }));

// Refresh-pipeline status — handy for monitoring the rolling refresh.
app.get("/api/status", async (c) => {
  const state = await c.env.DB.prepare(
    "SELECT cursor, universe_size, last_slice_at, last_assembly_at FROM refresh_state WHERE id = 1",
  ).first();
  const fresh = await c.env.DB.prepare(
    "SELECT COUNT(*) AS n FROM ticker_metrics WHERE fetched_at >= datetime('now', '-5 hours')",
  ).first<{ n: number }>();
  return c.json({ ...state, fresh_tickers: fresh?.n ?? 0 });
});

app.notFound((c) => {
  if (new URL(c.req.url).pathname.startsWith("/api/")) {
    return c.json({ detail: "Not found" }, 404);
  }
  // Non-API paths are served by the assets binding before reaching the Worker.
  return c.env.ASSETS.fetch(c.req.raw);
});

app.onError((err, c) => {
  console.error(`unhandled error on ${c.req.method} ${c.req.path}:`, err);
  return c.json({ detail: "Internal server error" }, 500);
});

export default {
  fetch: app.fetch,
  async scheduled(event: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    ctx.waitUntil(runScheduled(env, event.cron));
  },
} satisfies ExportedHandler<Env>;

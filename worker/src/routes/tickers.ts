// Watchlist CRUD — port of api/routes/tickers.py.

import { Hono } from "hono";
import { z } from "zod";
import { requireUser } from "../middleware";
import { symbolExists } from "../lib/yahoo";
import type { AppContext } from "../types";

const DEFAULT_TICKERS = [
  "NVDA", "GEV", "MU", "SNDK", "GOOG", "NBIS", "AAPL", "AMZN",
  "AMD", "INTC", "TSM", "RKLB", "ASTS", "IONQ", "MRVL", "VTIAX",
];

const SYMBOL_RE = /^[A-Z][A-Z0-9.\-]{0,9}$/;
const tickerCreateSchema = z.object({
  symbol: z
    .string()
    .transform((s) => s.trim().toUpperCase())
    .pipe(z.string().regex(SYMBOL_RE, "Invalid symbol format")),
  note: z.string().max(500).optional().nullable(),
});
const tickerUpdateSchema = z.object({ note: z.string().max(500).nullable() });

const VALIDATION_TTL_SEC = 24 * 3600;

export const tickerRoutes = new Hono<AppContext>();

tickerRoutes.get("/defaults", (c) => c.json(DEFAULT_TICKERS));

tickerRoutes.get("/", async (c) => {
  const user = c.get("user");
  if (!user) return c.json([]);
  const rows = await c.env.DB.prepare(
    "SELECT symbol, note, added_at FROM watchlists WHERE user_id = ? ORDER BY added_at DESC",
  )
    .bind(user.id)
    .all();
  return c.json(rows.results ?? []);
});

async function validateSymbol(c: { env: AppContext["Bindings"] }, symbol: string): Promise<boolean> {
  const cached = await c.env.DB.prepare(
    `SELECT valid FROM symbol_validation_cache
     WHERE symbol = ? AND fetched_at >= datetime('now', '-${VALIDATION_TTL_SEC} seconds')`,
  )
    .bind(symbol)
    .first<{ valid: number }>();
  if (cached !== null && cached !== undefined) return !!cached.valid;

  const valid = await symbolExists(symbol);
  await c.env.DB.prepare(
    `INSERT INTO symbol_validation_cache (symbol, valid, fetched_at) VALUES (?, ?, datetime('now'))
     ON CONFLICT (symbol) DO UPDATE SET valid=excluded.valid, fetched_at=datetime('now')`,
  )
    .bind(symbol, valid ? 1 : 0)
    .run();
  return valid;
}

tickerRoutes.post("/", requireUser, async (c) => {
  const parsed = tickerCreateSchema.safeParse(await c.req.json().catch(() => ({})));
  if (!parsed.success) {
    return c.json({ detail: parsed.error.issues[0]?.message ?? "Invalid payload" }, 422);
  }
  const { symbol, note } = parsed.data;
  const user = c.get("user")!;

  if (!(await validateSymbol(c, symbol))) {
    return c.json({ detail: `Symbol '${symbol}' does not resolve on Yahoo Finance` }, 422);
  }

  const existing = await c.env.DB.prepare(
    "SELECT 1 FROM watchlists WHERE user_id = ? AND symbol = ?",
  )
    .bind(user.id, symbol)
    .first();
  if (existing) return c.json({ detail: "Already in watchlist" }, 409);

  await c.env.DB.prepare(
    "INSERT INTO watchlists (user_id, symbol, note) VALUES (?, ?, ?)",
  )
    .bind(user.id, symbol, note ?? null)
    .run();
  const row = await c.env.DB.prepare(
    "SELECT symbol, note, added_at FROM watchlists WHERE user_id = ? AND symbol = ?",
  )
    .bind(user.id, symbol)
    .first();
  return c.json(row, 201);
});

tickerRoutes.patch("/:symbol", requireUser, async (c) => {
  const symbol = (c.req.param("symbol") ?? "").toUpperCase();
  const parsed = tickerUpdateSchema.safeParse(await c.req.json().catch(() => ({})));
  if (!parsed.success) return c.json({ detail: "Invalid payload" }, 422);
  const user = c.get("user")!;

  const existing = await c.env.DB.prepare(
    "SELECT 1 FROM watchlists WHERE user_id = ? AND symbol = ?",
  )
    .bind(user.id, symbol)
    .first();
  if (!existing) return c.json({ detail: "Ticker not in watchlist" }, 404);

  await c.env.DB.prepare(
    "UPDATE watchlists SET note = ? WHERE user_id = ? AND symbol = ?",
  )
    .bind(parsed.data.note, user.id, symbol)
    .run();
  const row = await c.env.DB.prepare(
    "SELECT symbol, note, added_at FROM watchlists WHERE user_id = ? AND symbol = ?",
  )
    .bind(user.id, symbol)
    .first();
  return c.json(row);
});

tickerRoutes.delete("/:symbol", requireUser, async (c) => {
  const symbol = (c.req.param("symbol") ?? "").toUpperCase();
  const user = c.get("user")!;
  await c.env.DB.prepare("DELETE FROM watchlists WHERE user_id = ? AND symbol = ?")
    .bind(user.id, symbol)
    .run();
  return c.body(null, 204);
});

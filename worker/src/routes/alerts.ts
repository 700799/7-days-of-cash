// Price alert CRUD — port of api/routes/alerts.py (open to all signed-in users).

import { Hono } from "hono";
import { z } from "zod";
import { requireUser } from "../middleware";
import type { AppContext } from "../types";

const ALERT_LIMIT = 10;

const createSchema = z.object({
  symbol: z
    .string()
    .transform((s) => s.trim().toUpperCase())
    .pipe(z.string().regex(/^[A-Z][A-Z0-9.\-]{0,9}$/, "Invalid symbol format")),
  condition: z.enum(["above", "below"]),
  target: z.number().positive().transform((v) => Math.round(v * 10000) / 10000),
});

export const alertRoutes = new Hono<AppContext>();

alertRoutes.get("/", requireUser, async (c) => {
  const user = c.get("user")!;
  const rows = await c.env.DB.prepare(
    `SELECT id, symbol, condition, target, triggered, created_at
     FROM price_alerts WHERE user_id = ? ORDER BY created_at DESC`,
  )
    .bind(user.id)
    .all<{ id: number; symbol: string; condition: string; target: number; triggered: number; created_at: string }>();
  return c.json(
    (rows.results ?? []).map((r) => ({ ...r, triggered: !!r.triggered })),
  );
});

alertRoutes.post("/", requireUser, async (c) => {
  const parsed = createSchema.safeParse(await c.req.json().catch(() => ({})));
  if (!parsed.success) {
    return c.json({ detail: parsed.error.issues[0]?.message ?? "Invalid payload" }, 422);
  }
  const user = c.get("user")!;
  const { symbol, condition, target } = parsed.data;

  const activeCount = await c.env.DB.prepare(
    "SELECT COUNT(*) AS n FROM price_alerts WHERE user_id = ? AND triggered = 0",
  )
    .bind(user.id)
    .first<{ n: number }>();
  if ((activeCount?.n ?? 0) >= ALERT_LIMIT) {
    return c.json(
      { detail: `Alert limit reached (${ALERT_LIMIT} active alerts max). Delete one to add another.` },
      429,
    );
  }

  try {
    const row = await c.env.DB.prepare(
      `INSERT INTO price_alerts (user_id, symbol, condition, target)
       VALUES (?, ?, ?, ?)
       RETURNING id, symbol, condition, target, triggered, created_at`,
    )
      .bind(user.id, symbol, condition, target)
      .first<{ id: number; symbol: string; condition: string; target: number; triggered: number; created_at: string }>();
    return c.json({ ...row, triggered: !!row?.triggered }, 201);
  } catch (e) {
    if (String(e).toLowerCase().includes("unique")) {
      return c.json({ detail: "Identical alert already exists." }, 409);
    }
    throw e;
  }
});

alertRoutes.delete("/:id", requireUser, async (c) => {
  const id = Number(c.req.param("id"));
  if (!Number.isInteger(id)) return c.json({ detail: "Invalid id" }, 400);
  const user = c.get("user")!;
  const existing = await c.env.DB.prepare(
    "SELECT 1 FROM price_alerts WHERE id = ? AND user_id = ?",
  )
    .bind(id, user.id)
    .first();
  if (!existing) return c.json({ detail: "Alert not found" }, 404);
  await c.env.DB.prepare("DELETE FROM price_alerts WHERE id = ? AND user_id = ?")
    .bind(id, user.id)
    .run();
  return c.body(null, 204);
});

// Email digest preferences — port of api/routes/preferences.py.

import { Hono } from "hono";
import { z } from "zod";
import { requireUser } from "../middleware";
import type { AppContext } from "../types";

const updateSchema = z.object({
  digest_frequency: z.enum(["none", "daily", "weekly"]),
  digest_email: z.string().email().max(320).optional().nullable(),
});

export const preferenceRoutes = new Hono<AppContext>();

preferenceRoutes.get("/", requireUser, async (c) => {
  const user = c.get("user")!;
  const row = await c.env.DB.prepare(
    "SELECT digest_frequency, digest_email, last_sent_at FROM user_preferences WHERE user_id = ?",
  )
    .bind(user.id)
    .first();
  return c.json(row ?? { digest_frequency: "none", digest_email: null, last_sent_at: null });
});

preferenceRoutes.patch("/", requireUser, async (c) => {
  const parsed = updateSchema.safeParse(await c.req.json().catch(() => ({})));
  if (!parsed.success) {
    return c.json({ detail: parsed.error.issues[0]?.message ?? "Invalid payload" }, 422);
  }
  const user = c.get("user")!;
  const { digest_frequency, digest_email } = parsed.data;

  await c.env.DB.prepare(
    `INSERT INTO user_preferences (user_id, digest_frequency, digest_email, updated_at)
     VALUES (?, ?, ?, datetime('now'))
     ON CONFLICT (user_id) DO UPDATE SET digest_frequency=excluded.digest_frequency,
       digest_email=excluded.digest_email, updated_at=datetime('now')`,
  )
    .bind(user.id, digest_frequency, digest_email ?? null)
    .run();

  const row = await c.env.DB.prepare(
    "SELECT digest_frequency, digest_email, last_sent_at FROM user_preferences WHERE user_id = ?",
  )
    .bind(user.id)
    .first();
  return c.json(row);
});

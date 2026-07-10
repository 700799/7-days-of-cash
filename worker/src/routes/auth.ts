// Auth routes: Google OAuth login/callback + session cookie management.

import { Hono } from "hono";
import { getCookie, setCookie } from "hono/cookie";
import { buildAuthUrl, exchangeCode, STATE_COOKIE } from "../lib/oauth";
import {
  clearSessionCookie,
  createSession,
  deleteSession,
  SESSION_COOKIE,
  sessionCookie,
} from "../lib/session";
import type { AppContext } from "../types";

const DEFAULT_TICKERS = [
  "NVDA", "GEV", "MU", "SNDK", "GOOG", "NBIS", "AAPL", "AMZN",
  "AMD", "INTC", "TSM", "RKLB", "ASTS", "IONQ", "MRVL", "VTIAX",
];

export const authRoutes = new Hono<AppContext>();

authRoutes.get("/login/google", (c) => {
  if (!c.env.GOOGLE_CLIENT_ID) {
    return c.json({ detail: "Google OAuth not configured" }, 500);
  }
  const { url, state } = buildAuthUrl(c.env);
  setCookie(c, STATE_COOKIE, state, {
    path: "/",
    httpOnly: true,
    sameSite: "Lax",
    maxAge: 600,
    secure: c.env.APP_ORIGIN.startsWith("https"),
  });
  return c.redirect(url, 302);
});

authRoutes.get("/callback", async (c) => {
  const code = c.req.query("code");
  const state = c.req.query("state");
  const expectedState = getCookie(c, STATE_COOKIE);
  if (!code || !state || !expectedState || state !== expectedState) {
    return c.json({ detail: "OAuth state mismatch" }, 400);
  }

  const info = await exchangeCode(c.env, code);
  if (!info) return c.json({ detail: "OAuth exchange failed" }, 400);

  const userId = String(info.sub);
  await c.env.DB.prepare(
    `INSERT INTO users (id, email, name, picture) VALUES (?, ?, ?, ?)
     ON CONFLICT (id) DO UPDATE SET email=excluded.email, name=excluded.name, picture=excluded.picture`,
  )
    .bind(userId, info.email, info.name ?? null, info.picture ?? null)
    .run();

  // Seed the default watchlist for first-time users.
  const hasTickers = await c.env.DB.prepare(
    "SELECT 1 FROM watchlists WHERE user_id = ? LIMIT 1",
  )
    .bind(userId)
    .first();
  if (!hasTickers) {
    await c.env.DB.batch(
      DEFAULT_TICKERS.map((sym) =>
        c.env.DB.prepare(
          "INSERT OR IGNORE INTO watchlists (user_id, symbol) VALUES (?, ?)",
        ).bind(userId, sym),
      ),
    );
  }

  const token = await createSession(c.env, userId);
  c.header("Set-Cookie", sessionCookie(token, c.env.APP_ORIGIN, 30 * 86400));
  return c.redirect("/", 302);
});

authRoutes.post("/logout", async (c) => {
  const token = getCookie(c, SESSION_COOKIE);
  if (token) await deleteSession(c.env, token);
  c.header("Set-Cookie", clearSessionCookie(c.env.APP_ORIGIN));
  return c.json({ ok: true });
});

authRoutes.get("/me", (c) => {
  const user = c.get("user");
  if (!user) return c.json({ detail: "Not authenticated" }, 401);
  return c.json(user);
});

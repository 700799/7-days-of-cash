// Shared middleware: session resolution, auth guards, CSRF origin check,
// security headers.

import type { Context, Next } from "hono";
import { getCookie } from "hono/cookie";
import { SESSION_COOKIE, userFromToken } from "./lib/session";
import type { AppContext } from "./types";

/** Resolve the session cookie to a user (or null) on every request. */
export async function sessionMiddleware(c: Context<AppContext>, next: Next): Promise<void> {
  const token = getCookie(c, SESSION_COOKIE);
  c.set("user", await userFromToken(c.env, token));
  await next();
}

/** 401 unless a signed-in user is present. */
export async function requireUser(c: Context<AppContext>, next: Next): Promise<Response | void> {
  if (!c.get("user")) return c.json({ detail: "Not authenticated" }, 401);
  await next();
}

/** CSRF backstop: mutating requests must come from our own origin. */
export async function csrfOriginCheck(c: Context<AppContext>, next: Next): Promise<Response | void> {
  const method = c.req.method;
  if (method === "POST" || method === "PATCH" || method === "DELETE" || method === "PUT") {
    const origin = c.req.header("Origin");
    if (origin && origin !== c.env.APP_ORIGIN) {
      return c.json({ detail: "Cross-origin write rejected" }, 403);
    }
  }
  await next();
}

/** Body size cap — reject oversized payloads before route parsing (64 KB).
 * Checks Content-Length when present; falls back to buffering the body for
 * chunked requests (Hono caches the read, so route handlers still get it). */
const MAX_BODY_BYTES = 64 * 1024;

export async function bodySizeLimit(c: Context<AppContext>, next: Next): Promise<Response | void> {
  const method = c.req.method;
  if (method === "POST" || method === "PATCH" || method === "PUT") {
    const len = Number(c.req.header("Content-Length") ?? NaN);
    if (Number.isFinite(len)) {
      if (len > MAX_BODY_BYTES) return c.json({ detail: "Request body too large" }, 413);
    } else if (c.req.raw.body) {
      const buf = await c.req.arrayBuffer();
      if (buf.byteLength > MAX_BODY_BYTES) {
        return c.json({ detail: "Request body too large" }, 413);
      }
    }
  }
  await next();
}

/** Security headers on every response; noindex on API responses. */
export async function securityHeaders(c: Context<AppContext>, next: Next): Promise<void> {
  await next();
  c.header("X-Content-Type-Options", "nosniff");
  c.header("Referrer-Policy", "strict-origin-when-cross-origin");
  c.header("Permissions-Policy", "camera=(), microphone=(), geolocation=()");
  if (c.env.APP_ORIGIN.startsWith("https")) {
    c.header("Strict-Transport-Security", "max-age=63072000; includeSubDomains; preload");
  }
  if (new URL(c.req.url).pathname.startsWith("/api/")) {
    c.header("X-Robots-Tag", "noindex, nofollow");
    c.header("X-Frame-Options", "DENY");
  } else {
    c.header("X-Frame-Options", "SAMEORIGIN");
  }
}

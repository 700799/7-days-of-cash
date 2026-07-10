// Session management: random tokens stored in D1, HttpOnly cookies.

import type { Env, User } from "../types";

export const SESSION_COOKIE = "b7dm_session";
const SESSION_TTL_DAYS = 30;

export function randomToken(bytes = 32): string {
  const buf = new Uint8Array(bytes);
  crypto.getRandomValues(buf);
  return [...buf].map((b) => b.toString(16).padStart(2, "0")).join("");
}

export async function createSession(env: Env, userId: string): Promise<string> {
  const token = randomToken();
  const expires = new Date(Date.now() + SESSION_TTL_DAYS * 86400_000).toISOString();
  await env.DB.prepare(
    "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
  )
    .bind(token, userId, expires)
    .run();
  return token;
}

export async function deleteSession(env: Env, token: string): Promise<void> {
  await env.DB.prepare("DELETE FROM sessions WHERE token = ?").bind(token).run();
}

/** Resolve a session token to its user; null when missing/expired. */
export async function userFromToken(env: Env, token: string | undefined): Promise<User | null> {
  if (!token || !/^[0-9a-f]{64}$/.test(token)) return null;
  const row = await env.DB.prepare(
    `SELECT u.id, u.email, u.name, u.picture
     FROM sessions s JOIN users u ON u.id = s.user_id
     WHERE s.token = ? AND s.expires_at > datetime('now')`,
  )
    .bind(token)
    .first<User>();
  return row ?? null;
}

export function sessionCookie(token: string, origin: string, maxAgeSec: number): string {
  const secure = origin.startsWith("https") ? "; Secure" : "";
  return `${SESSION_COOKIE}=${token}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${maxAgeSec}${secure}`;
}

export function clearSessionCookie(origin: string): string {
  return sessionCookie("", origin, 0);
}

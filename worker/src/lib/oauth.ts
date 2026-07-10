// Google OAuth 2.0 (authorization-code flow) implemented directly in the Worker.

import type { Env } from "../types";
import { randomToken } from "./session";

const AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth";
const TOKEN_URL = "https://oauth2.googleapis.com/token";
const USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo";

export const STATE_COOKIE = "b7dm_oauth_state";

export function redirectUri(env: Env): string {
  return `${env.APP_ORIGIN.replace(/\/$/, "")}/api/auth/callback`;
}

export function buildAuthUrl(env: Env): { url: string; state: string } {
  const state = randomToken(16);
  const params = new URLSearchParams({
    client_id: env.GOOGLE_CLIENT_ID ?? "",
    redirect_uri: redirectUri(env),
    response_type: "code",
    scope: "openid email profile",
    state,
    prompt: "select_account",
  });
  return { url: `${AUTH_URL}?${params}`, state };
}

export interface GoogleUserinfo {
  sub: string;
  email: string;
  name?: string;
  picture?: string;
}

/** Exchange the auth code for tokens, then fetch userinfo. Null on any failure. */
export async function exchangeCode(env: Env, code: string): Promise<GoogleUserinfo | null> {
  const tokenRes = await fetch(TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      code,
      client_id: env.GOOGLE_CLIENT_ID ?? "",
      client_secret: env.GOOGLE_CLIENT_SECRET ?? "",
      redirect_uri: redirectUri(env),
      grant_type: "authorization_code",
    }),
  });
  if (!tokenRes.ok) return null;
  const token = (await tokenRes.json()) as { access_token?: string };
  if (!token.access_token) return null;

  const infoRes = await fetch(USERINFO_URL, {
    headers: { Authorization: `Bearer ${token.access_token}` },
  });
  if (!infoRes.ok) return null;
  const info = (await infoRes.json()) as GoogleUserinfo;
  if (!info.sub || !info.email) return null;
  return info;
}

"""Google OAuth + cookie-based session auth.

Uses Authlib's Starlette OAuth client. Sessions are stored server-side in Postgres
(`sessions` table) keyed by a random opaque token; the cookie just carries the token.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request, status

from .config import get_settings
from .db import get_conn
from .defaults import DEFAULT_TICKERS
from .models import User


_oauth: Optional[OAuth] = None


def get_oauth() -> OAuth:
    """Return a configured Authlib OAuth registry (lazy)."""
    global _oauth
    if _oauth is not None:
        return _oauth
    settings = get_settings()
    oauth = OAuth()
    oauth.register(
        name="google",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )
    _oauth = oauth
    return oauth


def reset_oauth_cache() -> None:
    """Test helper."""
    global _oauth
    _oauth = None


def upsert_user(user_id: str, email: str, name: Optional[str], picture: Optional[str]) -> None:
    """Insert or update the user row.

    For a brand-new user whose watchlist is empty, seed it with DEFAULT_TICKERS so the
    landing experience isn't blank. Existing users with non-empty watchlists are left
    alone (idempotent on repeat logins).
    """
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """INSERT INTO users(id,email,name,picture) VALUES (%s,%s,%s,%s)
                   ON CONFLICT (id) DO UPDATE SET email=EXCLUDED.email,
                                                  name=EXCLUDED.name,
                                                  picture=EXCLUDED.picture""",
                [user_id, email, name, picture],
            )
            cur.execute(
                "SELECT 1 FROM watchlists WHERE user_id=%s LIMIT 1",
                [user_id],
            )
            existing = cur.fetchone()
            if existing is None:
                cur.executemany(
                    "INSERT INTO watchlists(user_id, symbol, note) VALUES (%s, %s, NULL)",
                    [(user_id, sym) for sym in DEFAULT_TICKERS],
                )


def create_session(user_id: str, ttl_days: Optional[int] = None) -> str:
    settings = get_settings()
    ttl = ttl_days if ttl_days is not None else settings.SESSION_TTL_DAYS
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=ttl)
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                "INSERT INTO sessions(token,user_id,expires_at) VALUES (%s,%s,%s)",
                [token, user_id, expires_at],
            )
    return token


def delete_session(token: str) -> None:
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE token=%s", [token])


def lookup_session(token: str) -> Optional[User]:
    if not token:
        return None
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """SELECT u.id, u.email, u.name, u.picture
                   FROM sessions s JOIN users u ON u.id = s.user_id
                   WHERE s.token = %s AND s.expires_at > now()""",
                [token],
            )
            row = cur.fetchone()
    if row is None:
        return None
    return User(id=row[0], email=row[1], name=row[2], picture=row[3])


def _read_session_cookie(request: Request) -> Optional[str]:
    return request.cookies.get(get_settings().SESSION_COOKIE_NAME)


def get_current_user(request: Request) -> User:
    """FastAPI dependency: 401 if no valid session."""
    user = lookup_session(_read_session_cookie(request) or "")
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def get_current_user_optional(request: Request) -> Optional[User]:
    """FastAPI dependency: returns None for anonymous callers."""
    return lookup_session(_read_session_cookie(request) or "")


# Re-exported convenience for tests / route modules
__all__ = [
    "get_oauth",
    "reset_oauth_cache",
    "upsert_user",
    "create_session",
    "delete_session",
    "lookup_session",
    "get_current_user",
    "get_current_user_optional",
]

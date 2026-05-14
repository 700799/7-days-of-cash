"""Google OAuth + cookie-based session auth.

Uses Authlib's Starlette OAuth client. Sessions are stored server-side in DuckDB
(`sessions` table) keyed by a random opaque token; the cookie just carries the token.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta
from typing import Optional

from authlib.integrations.starlette_client import OAuth
from fastapi import Depends, HTTPException, Request, status

from .config import get_settings
from .db import get_conn, get_write_conn
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
    with get_write_conn() as c:
        c.execute(
            """INSERT INTO users(id,email,name,picture) VALUES (?,?,?,?)
               ON CONFLICT (id) DO UPDATE SET email=excluded.email,
                                              name=excluded.name,
                                              picture=excluded.picture""",
            [user_id, email, name, picture],
        )


def create_session(user_id: str, ttl_days: Optional[int] = None) -> str:
    settings = get_settings()
    ttl = ttl_days if ttl_days is not None else settings.SESSION_TTL_DAYS
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=ttl)
    with get_write_conn() as c:
        c.execute(
            "INSERT INTO sessions(token,user_id,expires_at) VALUES (?,?,?)",
            [token, user_id, expires_at],
        )
    return token


def delete_session(token: str) -> None:
    with get_write_conn() as c:
        c.execute("DELETE FROM sessions WHERE token=?", [token])


def lookup_session(token: str) -> Optional[User]:
    if not token:
        return None
    with get_conn() as c:
        row = c.execute(
            """SELECT u.id, u.email, u.name, u.picture
               FROM sessions s JOIN users u ON u.id = s.user_id
               WHERE s.token = ? AND s.expires_at > CURRENT_TIMESTAMP""",
            [token],
        ).fetchone()
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

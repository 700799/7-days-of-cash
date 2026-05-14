"""Authentication routes: Google OAuth login + session cookie management."""
from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from ..auth import (
    create_session,
    delete_session,
    get_current_user,
    get_oauth,
    upsert_user,
)
from ..config import get_settings
from ..models import User
from ..security import AUTH_LIMIT, limiter

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _is_secure(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.hostname in (None, "localhost", "127.0.0.1", "0.0.0.0"):
        return False
    return parsed.scheme == "https"


@router.get("/login/google")
@limiter.limit(AUTH_LIMIT)
async def login_google(request: Request):
    settings = get_settings()
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=500, detail="Google OAuth not configured")
    redirect_uri = f"{settings.BACKEND_URL.rstrip('/')}/api/auth/callback"
    oauth = get_oauth()
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback")
@limiter.limit(AUTH_LIMIT)
async def callback(request: Request):
    settings = get_settings()
    oauth = get_oauth()
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth error: {e}")

    userinfo = token.get("userinfo")
    if userinfo is None:
        try:
            userinfo = await oauth.google.userinfo(token=token)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Cannot read userinfo: {e}")

    sub = userinfo.get("sub") or userinfo.get("id")
    email = userinfo.get("email")
    if not sub or not email:
        raise HTTPException(status_code=400, detail="Google userinfo missing sub/email")

    upsert_user(
        user_id=str(sub),
        email=email,
        name=userinfo.get("name"),
        picture=userinfo.get("picture"),
    )
    session_token = create_session(str(sub))

    redirect = RedirectResponse(url=settings.FRONTEND_URL or "/", status_code=302)
    redirect.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=session_token,
        max_age=settings.SESSION_TTL_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="lax",
        secure=_is_secure(settings.BACKEND_URL),
        path="/",
    )
    return redirect


@router.post("/logout")
async def logout(request: Request, response: Response):
    settings = get_settings()
    token = request.cookies.get(settings.SESSION_COOKIE_NAME)
    if token:
        delete_session(token)
    response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me", response_model=User)
async def me(user: User = Depends(get_current_user)):
    return user

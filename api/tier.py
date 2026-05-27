"""Tier/subscription enforcement for Best7DaysMula.

Two tiers: 'free' and 'pro'. Tier is read from the subscriptions table.
Missing row → implicitly 'free'. Pro requires active status; past_due or
canceled falls back to free.

Usage in route handlers:
    from ..tier import require_pro, get_user_tier

    @router.post("/export")
    def export(user: User = Depends(require_pro)):
        ...
"""
from __future__ import annotations

from typing import Literal

from fastapi import Depends, HTTPException, status

from .auth import get_current_user
from .db import get_conn
from .models import User

Tier = Literal["free", "pro"]

FREE_WATCHLIST_LIMIT = 5
PRO_ALERT_LIMIT = 10


def get_user_tier(user_id: str) -> Tier:
    """Return the user's current tier: 'pro' or 'free'.

    Reads the subscriptions table. Returns 'free' for any missing or
    non-active subscription so access degrades gracefully when DB is slow.
    """
    try:
        with get_conn() as c:
            with c.cursor() as cur:
                cur.execute(
                    """SELECT plan, status FROM subscriptions WHERE user_id = %s""",
                    [user_id],
                )
                row = cur.fetchone()
        if row and row[0] == "pro" and row[1] in ("active", "trialing"):
            return "pro"
    except Exception:
        pass
    return "free"


def require_pro(user: User = Depends(get_current_user)) -> User:
    """FastAPI dependency: passes through for Pro users, 403 for Free.

    Returns the user so routes can use it directly:
        def my_route(user: User = Depends(require_pro)):
    """
    tier = get_user_tier(user.id)
    if tier != "pro":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pro subscription required. Upgrade at /pricing.",
        )
    return user

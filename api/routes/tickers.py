"""Watchlist CRUD: tickers tied to the authenticated user."""
from __future__ import annotations

from typing import List, Optional

import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..auth import get_current_user, get_current_user_optional
from ..config import get_settings
from ..db import get_conn
from ..defaults import DEFAULT_TICKERS
from ..models import Ticker, TickerCreate, TickerUpdate, User
from ..security import WRITE_LIMIT, limiter
from ..tier import FREE_WATCHLIST_LIMIT, get_user_tier

router = APIRouter(prefix="/api/tickers", tags=["tickers"])


@router.get("/defaults", response_model=List[str])
def list_default_tickers() -> List[str]:
    """Default ticker list shown to anonymous users on the home page."""
    return list(DEFAULT_TICKERS)


def _validate_symbol_exists(symbol: str) -> bool:
    """Verify a ticker resolves on yfinance. Cached 24h in symbol_validation_cache."""
    settings = get_settings()
    symbol = symbol.upper()

    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """SELECT valid FROM symbol_validation_cache
                   WHERE symbol=%s
                     AND fetched_at >= now() - (%s || ' seconds')::interval""",
                [symbol, str(settings.SYMBOL_VALIDATION_TTL_SEC)],
            )
            row = cur.fetchone()
    if row is not None:
        return bool(row[0])

    valid = False
    try:
        info = yf.Ticker(symbol).info or {}
        if info.get("regularMarketPrice") is not None:
            valid = True
    except Exception:
        valid = False

    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """INSERT INTO symbol_validation_cache(symbol, valid, fetched_at)
                   VALUES (%s, %s, now())
                   ON CONFLICT (symbol) DO UPDATE SET valid=EXCLUDED.valid,
                                                     fetched_at=EXCLUDED.fetched_at""",
                [symbol, valid],
            )
    return valid


@router.get("", response_model=List[Ticker])
def list_tickers(user: Optional[User] = Depends(get_current_user_optional)) -> List[Ticker]:
    if user is None:
        return []
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                "SELECT symbol, note, added_at FROM watchlists WHERE user_id=%s ORDER BY added_at DESC",
                [user.id],
            )
            rows = cur.fetchall()
    return [Ticker(symbol=r[0], note=r[1], added_at=r[2]) for r in rows]


@router.post("", response_model=Ticker, status_code=status.HTTP_201_CREATED)
@limiter.limit(WRITE_LIMIT)
def add_ticker(
    request: Request,
    payload: TickerCreate,
    user: User = Depends(get_current_user),
) -> Ticker:
    symbol = payload.symbol  # already normalized by validator
    if not _validate_symbol_exists(symbol):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Symbol {symbol!r} does not resolve on yfinance",
        )

    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM watchlists WHERE user_id=%s AND symbol=%s",
                [user.id, symbol],
            )
            existing = cur.fetchone()
            if existing is not None:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already in watchlist")

            # Enforce free-tier watchlist limit
            tier = get_user_tier(user.id)
            if tier == "free":
                cur.execute(
                    "SELECT COUNT(*) FROM watchlists WHERE user_id=%s",
                    [user.id],
                )
                count_row = cur.fetchone()
                if count_row and count_row[0] >= FREE_WATCHLIST_LIMIT:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=(
                            f"Free plan limited to {FREE_WATCHLIST_LIMIT} tickers. "
                            "Upgrade to Pro for unlimited watchlist slots."
                        ),
                    )

            cur.execute(
                "INSERT INTO watchlists(user_id, symbol, note) VALUES (%s, %s, %s)",
                [user.id, symbol, payload.note],
            )
            cur.execute(
                "SELECT symbol, note, added_at FROM watchlists WHERE user_id=%s AND symbol=%s",
                [user.id, symbol],
            )
            row = cur.fetchone()
    return Ticker(symbol=row[0], note=row[1], added_at=row[2])


@router.patch("/{symbol}", response_model=Ticker)
def update_ticker(
    symbol: str,
    payload: TickerUpdate,
    user: User = Depends(get_current_user),
) -> Ticker:
    symbol = symbol.upper()
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM watchlists WHERE user_id=%s AND symbol=%s",
                [user.id, symbol],
            )
            existing = cur.fetchone()
            if existing is None:
                raise HTTPException(status_code=404, detail="Ticker not in watchlist")
            cur.execute(
                "UPDATE watchlists SET note=%s WHERE user_id=%s AND symbol=%s",
                [payload.note, user.id, symbol],
            )
            cur.execute(
                "SELECT symbol, note, added_at FROM watchlists WHERE user_id=%s AND symbol=%s",
                [user.id, symbol],
            )
            row = cur.fetchone()
    return Ticker(symbol=row[0], note=row[1], added_at=row[2])


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticker(symbol: str, user: User = Depends(get_current_user)):
    symbol = symbol.upper()
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                "DELETE FROM watchlists WHERE user_id=%s AND symbol=%s",
                [user.id, symbol],
            )
            cur.execute(
                "SELECT 1 FROM watchlists WHERE user_id=%s AND symbol=%s",
                [user.id, symbol],
            )
            still = cur.fetchone()
    if still is not None:
        raise HTTPException(status_code=500, detail="Failed to delete")
    return None

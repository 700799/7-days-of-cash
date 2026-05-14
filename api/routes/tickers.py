"""Watchlist CRUD: tickers tied to the authenticated user."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Optional

import yfinance as yf
from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import get_current_user, get_current_user_optional
from ..config import get_settings
from ..db import get_conn, get_write_conn
from ..models import Ticker, TickerCreate, TickerUpdate, User

router = APIRouter(prefix="/api/tickers", tags=["tickers"])


def _validate_symbol_exists(symbol: str) -> bool:
    """Verify a ticker resolves on yfinance. Cached 24h in symbol_validation_cache."""
    settings = get_settings()
    symbol = symbol.upper()
    cutoff = datetime.utcnow() - timedelta(seconds=settings.SYMBOL_VALIDATION_TTL_SEC)

    with get_conn() as c:
        row = c.execute(
            "SELECT valid FROM symbol_validation_cache WHERE symbol=? AND fetched_at>=?",
            [symbol, cutoff],
        ).fetchone()
    if row is not None:
        return bool(row[0])

    valid = False
    try:
        info = yf.Ticker(symbol).info or {}
        if info.get("regularMarketPrice") is not None:
            valid = True
    except Exception:
        valid = False

    with get_write_conn() as c:
        c.execute(
            """INSERT INTO symbol_validation_cache(symbol, valid, fetched_at)
               VALUES (?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT (symbol) DO UPDATE SET valid=excluded.valid,
                                                 fetched_at=excluded.fetched_at""",
            [symbol, valid],
        )
    return valid


@router.get("", response_model=List[Ticker])
def list_tickers(user: Optional[User] = Depends(get_current_user_optional)) -> List[Ticker]:
    if user is None:
        return []
    with get_conn() as c:
        rows = c.execute(
            "SELECT symbol, note, added_at FROM watchlists WHERE user_id=? ORDER BY added_at DESC",
            [user.id],
        ).fetchall()
    return [Ticker(symbol=r[0], note=r[1], added_at=r[2]) for r in rows]


@router.post("", response_model=Ticker, status_code=status.HTTP_201_CREATED)
def add_ticker(payload: TickerCreate, user: User = Depends(get_current_user)) -> Ticker:
    symbol = payload.symbol  # already normalized by validator
    if not _validate_symbol_exists(symbol):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Symbol {symbol!r} does not resolve on yfinance",
        )

    with get_conn() as c:
        existing = c.execute(
            "SELECT 1 FROM watchlists WHERE user_id=? AND symbol=?",
            [user.id, symbol],
        ).fetchone()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already in watchlist")

    with get_write_conn() as c:
        c.execute(
            "INSERT INTO watchlists(user_id, symbol, note) VALUES (?, ?, ?)",
            [user.id, symbol, payload.note],
        )
        row = c.execute(
            "SELECT symbol, note, added_at FROM watchlists WHERE user_id=? AND symbol=?",
            [user.id, symbol],
        ).fetchone()
    return Ticker(symbol=row[0], note=row[1], added_at=row[2])


@router.patch("/{symbol}", response_model=Ticker)
def update_ticker(
    symbol: str,
    payload: TickerUpdate,
    user: User = Depends(get_current_user),
) -> Ticker:
    symbol = symbol.upper()
    with get_write_conn() as c:
        existing = c.execute(
            "SELECT 1 FROM watchlists WHERE user_id=? AND symbol=?",
            [user.id, symbol],
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Ticker not in watchlist")
        c.execute(
            "UPDATE watchlists SET note=? WHERE user_id=? AND symbol=?",
            [payload.note, user.id, symbol],
        )
        row = c.execute(
            "SELECT symbol, note, added_at FROM watchlists WHERE user_id=? AND symbol=?",
            [user.id, symbol],
        ).fetchone()
    return Ticker(symbol=row[0], note=row[1], added_at=row[2])


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticker(symbol: str, user: User = Depends(get_current_user)):
    symbol = symbol.upper()
    with get_write_conn() as c:
        cur = c.execute(
            "DELETE FROM watchlists WHERE user_id=? AND symbol=?",
            [user.id, symbol],
        )
        # DuckDB's rowcount is unreliable in some versions; check existence after.
        still = c.execute(
            "SELECT 1 FROM watchlists WHERE user_id=? AND symbol=?",
            [user.id, symbol],
        ).fetchone()
    if still is not None:
        raise HTTPException(status_code=500, detail="Failed to delete")
    return None

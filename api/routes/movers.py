"""Mover snapshot routes. Reads/writes a 4-hour cache row per symbol."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from ..db import get_conn
from ..movers import build_mover

router = APIRouter(prefix="/api/movers", tags=["movers"])


MOVERS_TTL_SEC = 4 * 60 * 60  # 4h


def _read_cache(symbol: str) -> Optional[Dict[str, Any]]:
    key = f"mover:{symbol.upper()}"
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """SELECT payload FROM movers_cache
                   WHERE cache_key=%s
                     AND fetched_at >= now() - (%s || ' seconds')::interval""",
                [key, str(MOVERS_TTL_SEC)],
            )
            row = cur.fetchone()
    if not row:
        return None
    try:
        return json.loads(row[0])
    except Exception:
        return None


def _write_cache(symbol: str, payload: Dict[str, Any]) -> None:
    key = f"mover:{symbol.upper()}"
    with get_conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """INSERT INTO movers_cache(cache_key, payload, fetched_at)
                   VALUES (%s, %s, now())
                   ON CONFLICT (cache_key) DO UPDATE SET payload=EXCLUDED.payload,
                                                        fetched_at=EXCLUDED.fetched_at""",
                [key, json.dumps(payload)],
            )


def _resolve(symbol: str) -> Dict[str, Any]:
    cached = _read_cache(symbol)
    if cached is not None:
        return cached
    payload = build_mover(symbol)
    _write_cache(symbol, payload)
    return payload


@router.get("")
def list_movers(symbols: str = Query(..., description="Comma-separated symbols, max 50")) -> List[Dict[str, Any]]:
    """Batch mover endpoint — accepts up to 50 symbols."""
    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not syms:
        return []
    if len(syms) > 50:
        raise HTTPException(status_code=413, detail="Too many symbols (max 50)")
    return [_resolve(sym) for sym in syms]


@router.get("/{symbol}")
def get_mover(symbol: str) -> Dict[str, Any]:
    """Single-symbol mover — 404 only if even the fallback build fails."""
    payload = _resolve(symbol)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"Unknown symbol {symbol!r}")
    return payload

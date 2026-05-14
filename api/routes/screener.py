"""Screener route — runs the multi-agent pipeline on demand."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from ..auth import get_current_user_optional
from ..models import ScreenerRequest, ScreenerResponse, User
from ..security import EXPENSIVE_LIMIT, limiter

router = APIRouter(prefix="/api/screener", tags=["screener"])

# Hard cap — Vercel Hobby has a 10-second function timeout. ~50 tickers is the
# largest set the live pipeline can complete in time. Larger universes go
# through the cron-cached `/cached` endpoint.
MAX_LIVE_TICKERS = 50


def _run_pipeline(
    tickers: Optional[List[str]],
    filters: Optional[Dict[str, Any]],
    agent_names: Optional[List[str]],
) -> Dict[str, Any]:
    # Imported lazily so module import (and tests that mock the universe) stay cheap.
    from screener.benchmarks import fetch_benchmarks, market_regime
    from screener.data_fetcher import fetch_batch
    from screener.filters import apply_filters
    from screener.metrics import compute_metrics
    from screener.orchestrator import score_records
    from screener.universe import get_sp500_tickers

    universe = [t.upper() for t in tickers] if tickers else get_sp500_tickers()

    benchmarks = fetch_benchmarks()
    regime = market_regime(benchmarks)

    raw = fetch_batch(universe)
    records: List[Dict[str, Any]] = []
    for ticker, df in raw.items():
        rec = compute_metrics(ticker, df)
        if rec is not None:
            records.append(rec)

    scored_df = score_records(records, benchmarks=benchmarks, regime=regime, agent_names=agent_names)
    if filters:
        # apply_filters takes records, not a DataFrame
        scored_records = scored_df.to_dict("records") if not scored_df.empty else []
        scored_df = apply_filters(scored_records, filters)

    results = scored_df.to_dict("records") if not scored_df.empty else []
    return {
        "regime": regime,
        "benchmarks": benchmarks,
        "results": results,
        "ran_at": datetime.now(timezone.utc),
    }


@router.post("/run", response_model=ScreenerResponse)
@limiter.limit(EXPENSIVE_LIMIT)
def run_screener(
    request: Request,
    payload: ScreenerRequest,
    _user: Optional[User] = Depends(get_current_user_optional),
) -> ScreenerResponse:
    if payload.tickers and len(payload.tickers) > MAX_LIVE_TICKERS:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Live screener accepts up to {MAX_LIVE_TICKERS} tickers. "
                f"Use GET /api/screener/cached for the full S&P 500."
            ),
        )
    out = _run_pipeline(payload.tickers, payload.filters, payload.agents)
    return ScreenerResponse(**out)


@router.get("/cached", response_model=ScreenerResponse)
def get_cached_screener(
    _user: Optional[User] = Depends(get_current_user_optional),
) -> ScreenerResponse:
    """Return latest pre-computed screener results (updated every 4 hours via cron).

    Returns instantly from Postgres cache. Never hits yfinance live.
    """
    import json
    from ..db import get_conn

    try:
        with get_conn() as c:
            with c.cursor() as cur:
                cur.execute(
                    """SELECT ran_at, payload FROM screener_results
                       ORDER BY ran_at DESC LIMIT 1"""
                )
                row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No cached results yet. Cron will populate them.")
        ran_at_str, payload_str = row
        payload = json.loads(payload_str)
        return ScreenerResponse(
            regime={},
            benchmarks={},
            results=payload.get("results", []),
            ran_at=ran_at_str,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch cached results: {e}")

"""Screener route — runs the multi-agent pipeline on demand."""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from ..auth import get_current_user_optional
from ..db import get_conn
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
    user: User = Depends(get_current_user_optional),
) -> ScreenerResponse:
    """Run live screener on a custom ticker list (≤ 50 tickers)."""
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

    Available to all users (Free + Pro). Returns instantly from Postgres cache.
    Never hits yfinance live.
    """
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


@router.get("/top")
def get_top_screener(
    n: int = 10,
    _user: Optional[User] = Depends(get_current_user_optional),
) -> list:
    """Return the top N leaders from cached pre-computed results.

    Returns a minimal list of dicts: {ticker, ret_7d, score, best_strategy}.
    Useful for integrations, dashboards, and embedding in digest emails.
    """
    if n < 1 or n > 100:
        raise HTTPException(status_code=400, detail="n must be between 1 and 100")

    try:
        with get_conn() as c:
            with c.cursor() as cur:
                cur.execute(
                    """SELECT payload FROM screener_results
                       ORDER BY ran_at DESC LIMIT 1"""
                )
                row = cur.fetchone()
        if not row:
            return []
        payload = json.loads(row[0])
        results = payload.get("results", [])
        return [
            {
                "ticker": r.get("ticker"),
                "ret_7d": r.get("ret_7d"),
                "score": r.get("score") or r.get("composite_score"),
                "best_strategy": r.get("best_strategy"),
                "vs_voo": r.get("vs_voo"),
            }
            for r in results[:n]
        ]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch top results: {e}")


@router.get("/export")
def export_screener_csv(
    user: User = Depends(get_current_user_optional),
) -> StreamingResponse:
    """Download screener results as CSV (Pro only).

    Returns the latest cached screener run as a downloadable CSV file with
    all scored columns. Suitable for import into Excel / Google Sheets.
    """
    try:
        with get_conn() as c:
            with c.cursor() as cur:
                cur.execute(
                    """SELECT ran_at, payload FROM screener_results
                       ORDER BY ran_at DESC LIMIT 1"""
                )
                row = cur.fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

    if not row:
        raise HTTPException(status_code=404, detail="No screener results to export yet.")

    ran_at, payload_str = row
    payload = json.loads(payload_str)
    results = payload.get("results", [])

    if not results:
        raise HTTPException(status_code=404, detail="No results in latest screener run.")

    # Build CSV in memory
    output = io.StringIO()
    fieldnames = [
        "ticker", "price", "ret_7d", "change_7d", "score", "composite_score",
        "momentum", "breakout", "volume", "rs", "mean_reversion",
        "best_strategy", "vs_voo",
    ]
    # Include any extra columns present in the data
    extra_keys = sorted(
        k for k in results[0].keys()
        if k not in fieldnames and not k.startswith("_")
    )
    all_fields = fieldnames + extra_keys

    writer = csv.DictWriter(output, fieldnames=all_fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(results)

    filename_date = ran_at.strftime("%Y%m%d") if ran_at else "latest"
    filename = f"best7daysmula_screener_{filename_date}.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/history")
def screener_history(
    days: int = 7,
    _user: Optional[User] = Depends(get_current_user_optional),
) -> list:
    """Return historical screener runs for the last N days (Pro only, max 30).

    Each entry: {id, ran_at, results_count, top_5_tickers, error}.
    Useful for tracking which stocks the screener consistently identifies.
    """
    days = max(1, min(days, 30))

    try:
        with get_conn() as c:
            with c.cursor() as cur:
                cur.execute(
                    """SELECT id, ran_at, payload
                       FROM screener_results
                       WHERE ran_at >= now() - (%s || ' days')::interval
                       ORDER BY ran_at DESC""",
                    [str(days)],
                )
                rows = cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

    history = []
    for row_id, ran_at, payload_data in rows:
        payload = json.loads(payload_data) if isinstance(payload_data, str) else payload_data
        results = payload.get("results", [])
        top5 = [r.get("ticker") for r in results[:5]]
        history.append({
            "id": row_id,
            "ran_at": ran_at.isoformat() if ran_at else None,
            "results_count": len(results),
            "top_5_tickers": top5,
            "error": payload.get("error"),
        })

    return history


@router.get("/share/{result_id}")
def get_shared_screener(result_id: int) -> Dict[str, Any]:
    """Public read of a specific screener run by ID (no auth required).

    Powers shareable result links: /results/{id}
    """
    try:
        with get_conn() as c:
            with c.cursor() as cur:
                cur.execute(
                    "SELECT ran_at, payload FROM screener_results WHERE id = %s",
                    [result_id],
                )
                row = cur.fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {e}")

    if not row:
        raise HTTPException(status_code=404, detail="Screener result not found.")

    ran_at, payload_data = row
    payload = json.loads(payload_data) if isinstance(payload_data, str) else payload_data
    results = payload.get("results", [])

    return {
        "id": result_id,
        "ran_at": ran_at.isoformat() if ran_at else None,
        "results_count": len(results),
        "top_picks": results[:10],
    }

"""Screener route — runs the multi-agent pipeline on demand."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends

from ..auth import get_current_user_optional
from ..models import ScreenerRequest, ScreenerResponse, User

router = APIRouter(prefix="/api/screener", tags=["screener"])


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
def run_screener(
    payload: ScreenerRequest,
    _user: Optional[User] = Depends(get_current_user_optional),
) -> ScreenerResponse:
    out = _run_pipeline(payload.tickers, payload.filters, payload.agents)
    return ScreenerResponse(**out)

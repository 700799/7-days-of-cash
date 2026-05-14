"""Precompute full-universe screener results and cache them in Postgres.

Called by Vercel Cron every 4 hours. Runs the full screener pipeline,
serializes results as JSON, and writes to screener_results table so UI can
instantly read cached results without hitting yfinance.

Estimates:
  - Full S&P 500 + Extended (~700 tickers) = 15-25 seconds
  - Cron maxDuration: 60 seconds (plenty of budget)
  - Write-once-per-run pattern keeps costs down
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

log = logging.getLogger(__name__)


def run_full_screener() -> Dict[str, Any]:
    """Orchestrate full screener run and cache results.

    Returns metadata dict: {ran_at, results_count, results: [...]}
    """
    from screener import (
        OHLCVCache, apply_filters, compute_metrics, fetch_batch,
        fetch_benchmarks, get_extended_tickers, market_regime,
    )
    from screener.orchestrator import score_records
    from .db import get_conn

    ran_at = datetime.now(timezone.utc)
    results = []
    error_msg = None

    try:
        log.info("Starting full screener precompute...")

        # Initialize cache with long TTL (let cron manage freshness)
        cache = OHLCVCache(ttl_sec=14400)  # 4 hours

        # Build universe
        tickers = get_extended_tickers()
        log.info(f"Screening {len(tickers)} tickers")

        # Fetch benchmarks and data
        benchmarks = fetch_benchmarks(period="35d")
        regime = market_regime(benchmarks)

        raw_data = fetch_batch(
            tickers,
            period="35d",
            chunk_size=60,
            max_workers=4,
            sleep_sec=0.5,
            max_retries=3,
            cache=cache,
            use_cache=True,
        )

        # Compute metrics
        records = [
            m for t, df in raw_data.items()
            if (m := compute_metrics(t, df)) is not None
        ]
        log.info(f"Computed metrics for {len(records)} records")

        # Score with agents
        scored_df = score_records(
            records,
            benchmarks=benchmarks,
            regime=regime,
        )
        records_for_filter = scored_df.to_dict(orient="records")

        # Apply filters (using defaults from config.yaml)
        results_df = apply_filters(records_for_filter)
        results = results_df.to_dict(orient="records")
        log.info(f"Screener completed: {len(results)} results")

    except Exception as e:
        log.exception("Screener pipeline failed")
        error_msg = str(e)

    payload = {
        "ran_at": ran_at.isoformat(),
        "results_count": len(results),
        "results": results,
        "error": error_msg,
    }

    # Write to Postgres
    try:
        with get_conn() as c:
            with c.cursor() as cur:
                cur.execute(
                    """INSERT INTO screener_results (ran_at, payload)
                       VALUES (%s, %s)
                       RETURNING id""",
                    [ran_at, json.dumps(payload)],
                )
                row = cur.fetchone()
                result_id = row[0] if row else None
        log.info(f"Cached screener results to DB: id={result_id}")
    except Exception as e:
        log.exception("Failed to write screener results to DB")

    return payload

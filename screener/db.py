"""Postgres writer for screener results (Neon-compatible).

psycopg2 is imported lazily so the rest of the CLI runs without it installed;
it is only needed when `--to-postgres` is used.
"""
from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"

# Metric columns that map to dedicated table columns, in INSERT order.
_CORE_COLUMNS: List[str] = [
    "ticker", "price", "change_5d", "change_7d", "change_20d",
    "avg_vol_20d", "rel_vol", "vol_trend_5d", "vol_trend_7d", "dollar_vol_20d",
    "ma_20", "ma_50", "ma_200", "pct_from_ma20", "pct_from_ma50",
    "pct_from_52w_high", "rsi_14", "atr_14", "atr_pct", "macd_hist",
    "avg_range_pct", "gap_pct", "composite_score", "best_strategy",
    "top_reasons", "flags",
]


def _require_psycopg2():
    try:
        import psycopg2
        return psycopg2
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "psycopg2 is required for --to-postgres. Install it with: "
            "pip install psycopg2-binary"
        ) from exc


def _resolve_dsn(dsn: Optional[str]) -> str:
    dsn = dsn or os.environ.get("DATABASE_URL")
    if not dsn:
        raise RuntimeError(
            "DATABASE_URL is not set. Export it (or pass dsn=...) with your "
            "Neon connection string, e.g. postgresql://user:pass@host/db?sslmode=require"
        )
    return dsn


def _clean(value: Any) -> Any:
    """Coerce a pandas/numpy cell into a plain Python scalar (or None)."""
    if value is None:
        return None
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        f = float(value)
        return None if math.isnan(f) else f
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, float):
        return None if math.isnan(value) else value
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


def _jsonable(obj: Any) -> Any:
    """Recursively convert sets/numpy types into JSON-serializable values."""
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (set, frozenset)):
        return sorted(_jsonable(v) for v in obj)
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        f = float(obj)
        return None if math.isnan(f) else f
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, float):
        return None if math.isnan(obj) else obj
    return obj


def _build_rows(df: pd.DataFrame, run_id: int) -> List[Tuple]:
    """Build one tuple per result row: (run_id, rank, *core, agent_scores_dict).

    agent_scores is a plain dict here; the caller wraps it for the driver.
    """
    agent_cols = [c for c in df.columns if c.startswith("score_") or c.startswith("tier_")]
    rows: List[Tuple] = []
    for rank, (_, row) in enumerate(df.iterrows(), start=1):
        core = [_clean(row.get(col)) for col in _CORE_COLUMNS]
        agent_scores = {col: _clean(row.get(col)) for col in agent_cols}
        rows.append((run_id, rank, *core, agent_scores))
    return rows


def write_run(
    df: pd.DataFrame,
    *,
    regime: Optional[Dict[str, Any]] = None,
    benchmarks: Optional[Dict[str, Any]] = None,
    config: Optional[Dict[str, Any]] = None,
    universe_size: int = 0,
    elapsed_sec: float = 0.0,
    agent_names: Optional[List[str]] = None,
    dsn: Optional[str] = None,
) -> int:
    """Insert one run plus its ranked results in a single transaction.

    Returns the new run id. An empty/None ``df`` records the run with zero
    results (so the frontend can tell the screener ran but found nothing).
    """
    psycopg2 = _require_psycopg2()
    from psycopg2.extras import Json, execute_values

    dsn = _resolve_dsn(dsn)
    result_count = 0 if df is None or df.empty else len(df)

    conn = psycopg2.connect(dsn)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_PATH.read_text())
                cur.execute(
                    """
                    INSERT INTO screener_runs
                        (regime, benchmarks, config, universe_size,
                         result_count, elapsed_sec, agent_names)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        Json(_jsonable(regime or {})),
                        Json(_jsonable(benchmarks or {})),
                        Json(_jsonable(config or {})),
                        int(universe_size),
                        int(result_count),
                        float(elapsed_sec),
                        list(agent_names or []),
                    ),
                )
                run_id = int(cur.fetchone()[0])

                if result_count:
                    rows = _build_rows(df, run_id)
                    wrapped = [(*r[:-1], Json(r[-1])) for r in rows]
                    columns = ", ".join(["run_id", "rank", *_CORE_COLUMNS, "agent_scores"])
                    placeholders = "(" + ", ".join(["%s"] * (len(_CORE_COLUMNS) + 3)) + ")"
                    execute_values(
                        cur,
                        f"INSERT INTO screener_results ({columns}) VALUES %s",
                        wrapped,
                        template=placeholders,
                    )
        return run_id
    finally:
        conn.close()

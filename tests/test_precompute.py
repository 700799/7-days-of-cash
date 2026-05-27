"""Unit tests for api/precompute.py — run_full_screener().

All heavy dependencies (screener pipeline, DB) are mocked so no
network calls or Postgres connection is required.
"""
from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_scored_df(n: int = 3) -> pd.DataFrame:
    """Minimal scored DataFrame that apply_filters can consume."""
    return pd.DataFrame([
        {
            "ticker": f"TICK{i}",
            "price": 100.0 + i,
            "change_7d": 10.0 + i,
            "ret_7d": 10.0 + i,
            "avg_volume": 5_000_000,
            "dollar_vol": 500_000_000,
            "rsi": 55.0,
            "market_cap": 1e10,
            "atr_pct": 2.0,
            "score": 80.0 + i,
            "composite_score": 80.0 + i,
            "best_strategy": "momentum",
            "vs_voo": i * 1.5,
        }
        for i in range(n)
    ])


def _make_mock_conn(return_id=42):
    mock_cursor = MagicMock()
    mock_cursor.__enter__ = lambda s: s
    mock_cursor.__exit__ = MagicMock(return_value=False)
    mock_cursor.fetchone.return_value = (return_id,)

    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: s
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value = mock_cursor

    @contextmanager
    def _get_conn(*args, **kwargs):
        yield mock_conn

    return _get_conn, mock_conn, mock_cursor


# ---------------------------------------------------------------------------
# Shared patch targets
# ---------------------------------------------------------------------------

SCREENER_PATCHES = {
    "screener.OHLCVCache": MagicMock(),
    "screener.get_extended_tickers": lambda: ["AAPL", "NVDA", "MSFT"],
    "screener.fetch_benchmarks": lambda **kw: {"SPY": 1.0},
    "screener.market_regime": lambda b: "BULL",
    "screener.fetch_batch": lambda tickers, **kw: {
        t: pd.DataFrame({"Close": [100, 101, 102]}) for t in tickers
    },
    "screener.compute_metrics": lambda t, df: {
        "ticker": t, "price": 101.0, "change_7d": 10.0, "avg_volume": 5_000_000,
        "dollar_vol": 505_000_000, "rsi": 55.0, "market_cap": 1e10, "atr_pct": 2.0,
    },
    "screener.apply_filters": lambda recs, cfg: _fake_scored_df(len(recs)),
}


def _run_with_mocks(get_conn_fn):
    """Patch all screener internals and DB, then call run_full_screener()."""
    scored = _fake_scored_df(3)

    with (
        patch("screener.OHLCVCache", return_value=MagicMock()),
        patch("screener.get_extended_tickers", return_value=["AAPL", "NVDA", "MSFT"]),
        patch("screener.fetch_benchmarks", return_value={"SPY": 1.0}),
        patch("screener.market_regime", return_value="BULL"),
        patch("screener.fetch_batch", return_value={
            t: pd.DataFrame({"Close": [100, 101, 102]}) for t in ["AAPL", "NVDA", "MSFT"]
        }),
        patch("screener.compute_metrics", side_effect=lambda t, df: {
            "ticker": t, "price": 101.0, "change_7d": 12.0, "avg_volume": 5_000_000,
            "dollar_vol": 505_000_000, "rsi": 55.0, "market_cap": 1e10, "atr_pct": 2.0,
        }),
        patch("screener.orchestrator.score_records", return_value=scored),
        patch("screener.apply_filters", return_value=scored),
        patch("api.db.get_conn", get_conn_fn),
    ):
        from api.precompute import run_full_screener
        return run_full_screener()


# ---------------------------------------------------------------------------
# Return shape
# ---------------------------------------------------------------------------

class TestRunFullScreenerShape:
    def test_returns_dict(self):
        get_conn_fn, _, _ = _make_mock_conn()
        result = _run_with_mocks(get_conn_fn)
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        get_conn_fn, _, _ = _make_mock_conn()
        result = _run_with_mocks(get_conn_fn)
        for key in ("ran_at", "results_count", "results", "error"):
            assert key in result, f"Missing key: {key}"

    def test_ran_at_is_iso_string(self):
        get_conn_fn, _, _ = _make_mock_conn()
        result = _run_with_mocks(get_conn_fn)
        ran_at = result["ran_at"]
        assert isinstance(ran_at, str)
        # Should parse as ISO 8601
        dt = datetime.fromisoformat(ran_at)
        assert dt.tzinfo is not None, "ran_at should be timezone-aware"

    def test_results_count_matches_results_len(self):
        get_conn_fn, _, _ = _make_mock_conn()
        result = _run_with_mocks(get_conn_fn)
        assert result["results_count"] == len(result["results"])

    def test_results_is_list(self):
        get_conn_fn, _, _ = _make_mock_conn()
        result = _run_with_mocks(get_conn_fn)
        assert isinstance(result["results"], list)

    def test_error_is_none_on_success(self):
        get_conn_fn, _, _ = _make_mock_conn()
        result = _run_with_mocks(get_conn_fn)
        assert result["error"] is None


# ---------------------------------------------------------------------------
# DB write behavior
# ---------------------------------------------------------------------------

class TestRunFullScreenerDbWrite:
    def test_writes_to_screener_results_table(self):
        get_conn_fn, mock_conn, mock_cursor = _make_mock_conn()
        _run_with_mocks(get_conn_fn)
        # execute should have been called with an INSERT
        assert mock_cursor.execute.called
        call_args = mock_cursor.execute.call_args
        sql = call_args[0][0].upper()
        assert "INSERT" in sql
        assert "SCREENER_RESULTS" in sql

    def test_payload_is_json_serializable(self):
        """The payload written to DB must be valid JSON."""
        written_json: list = []

        mock_cursor = MagicMock()
        mock_cursor.__enter__ = lambda s: s
        mock_cursor.__exit__ = MagicMock(return_value=False)
        mock_cursor.fetchone.return_value = (1,)

        def capture_execute(sql, params):
            if "INSERT" in sql.upper():
                written_json.append(params[1])

        mock_cursor.execute.side_effect = capture_execute

        mock_conn = MagicMock()
        mock_conn.__enter__ = lambda s: s
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_conn.cursor.return_value = mock_cursor

        @contextmanager
        def _get_conn(*args, **kwargs):
            yield mock_conn

        _run_with_mocks(_get_conn)

        assert written_json, "No INSERT was executed"
        parsed = json.loads(written_json[0])
        assert "results" in parsed
        assert "ran_at" in parsed


# ---------------------------------------------------------------------------
# Error resilience
# ---------------------------------------------------------------------------

class TestRunFullScreenerErrors:
    def test_pipeline_error_captured_in_payload(self):
        """When screener pipeline raises, error is recorded but function returns."""
        get_conn_fn, _, _ = _make_mock_conn()

        with (
            patch("screener.OHLCVCache", return_value=MagicMock()),
            patch("screener.get_extended_tickers", side_effect=RuntimeError("network down")),
            patch("api.db.get_conn", get_conn_fn),
        ):
            from api.precompute import run_full_screener
            result = run_full_screener()

        assert result["error"] is not None
        assert "network down" in result["error"]
        assert result["results"] == []
        assert result["results_count"] == 0

    def test_db_write_error_does_not_raise(self):
        """DB write failure should log but not propagate — payload is still returned."""
        @contextmanager
        def _bad_conn(*args, **kwargs):
            raise RuntimeError("DB unavailable")
            yield  # unreachable, makes it a generator

        scored = _fake_scored_df(2)
        with (
            patch("screener.OHLCVCache", return_value=MagicMock()),
            patch("screener.get_extended_tickers", return_value=["AAPL", "NVDA"]),
            patch("screener.fetch_benchmarks", return_value={}),
            patch("screener.market_regime", return_value="NEUTRAL"),
            patch("screener.fetch_batch", return_value={
                t: pd.DataFrame({"Close": [100, 101]}) for t in ["AAPL", "NVDA"]
            }),
            patch("screener.compute_metrics", side_effect=lambda t, df: {"ticker": t, "price": 100.0}),
            patch("screener.orchestrator.score_records", return_value=scored),
            patch("screener.apply_filters", return_value=scored),
            patch("api.db.get_conn", _bad_conn),
        ):
            from api.precompute import run_full_screener
            result = run_full_screener()

        # Pipeline succeeded; only DB write failed
        assert result["results_count"] >= 0
        assert isinstance(result, dict)

    def test_empty_universe_returns_zero_results(self):
        get_conn_fn, _, _ = _make_mock_conn()

        with (
            patch("screener.OHLCVCache", return_value=MagicMock()),
            patch("screener.get_extended_tickers", return_value=[]),
            patch("screener.fetch_benchmarks", return_value={}),
            patch("screener.market_regime", return_value="NEUTRAL"),
            patch("screener.fetch_batch", return_value={}),
            patch("screener.compute_metrics", return_value=None),
            patch("screener.orchestrator.score_records", return_value=pd.DataFrame()),
            patch("screener.apply_filters", return_value=pd.DataFrame()),
            patch("api.db.get_conn", get_conn_fn),
        ):
            from api.precompute import run_full_screener
            result = run_full_screener()

        assert result["results_count"] == 0
        assert result["results"] == []

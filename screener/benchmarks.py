from typing import Dict, Any, List
import warnings

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)

BENCHMARK_META = {
    "VOO":   {"name": "S&P 500",        "description": "Large-cap US equities"},
    "VXF":   {"name": "Extended Mkt",   "description": "Small+mid-cap US (ex-S&P 500)"},
    "VTIAX": {"name": "Total Intl",     "description": "International developed + EM"},
}


def fetch_benchmarks(period: str = "35d") -> Dict[str, Dict[str, Any]]:
    tickers = list(BENCHMARK_META.keys())
    results: Dict[str, Dict[str, Any]] = {}

    try:
        data = yf.download(
            tickers,
            period=period,
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    except Exception:
        return results

    for ticker in tickers:
        try:
            if isinstance(data.columns, pd.MultiIndex):
                close = data["Close"][ticker].dropna()
            else:
                close = data["Close"].dropna()

            if len(close) < 8:
                continue

            lookback = min(7, len(close) - 1)
            change_7d = (close.iloc[-1] / close.iloc[-1 - lookback] - 1) * 100
            price = float(close.iloc[-1])

            results[ticker] = {
                **BENCHMARK_META[ticker],
                "ticker": ticker,
                "price": round(price, 2),
                "change_7d": round(float(change_7d), 2),
            }
        except Exception:
            continue

    return results

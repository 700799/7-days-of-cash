"""Multi-asset benchmark fetcher.

Includes equity (VOO, VXF, VTIAX, QQQ, IWM), commodity (GLD), and bond (TLT) ETFs.
"""
from __future__ import annotations

import warnings
from typing import Any, Dict

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

BENCHMARK_META = {
    "VOO":   {"name": "S&P 500",        "description": "Large-cap US equities",         "asset_class": "equity"},
    "QQQ":   {"name": "Nasdaq 100",     "description": "Mega-cap tech / growth",        "asset_class": "equity"},
    "VXF":   {"name": "Extended Mkt",   "description": "Small+mid-cap US (ex-S&P 500)", "asset_class": "equity"},
    "IWM":   {"name": "Russell 2000",   "description": "US small-cap",                  "asset_class": "equity"},
    "VTIAX": {"name": "Total Intl",     "description": "International dev + EM",        "asset_class": "intl"},
    "GLD":   {"name": "Gold",           "description": "SPDR Gold Shares",              "asset_class": "commodity"},
    "TLT":   {"name": "20+y Treasury",  "description": "Long-duration bonds",           "asset_class": "bond"},
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

            n = len(close)
            change_5d = (close.iloc[-1] / close.iloc[-1 - min(5, n - 1)] - 1) * 100
            change_7d = (close.iloc[-1] / close.iloc[-1 - min(7, n - 1)] - 1) * 100
            change_20d = (close.iloc[-1] / close.iloc[-1 - min(20, n - 1)] - 1) * 100
            price = float(close.iloc[-1])

            results[ticker] = {
                **BENCHMARK_META[ticker],
                "ticker": ticker,
                "price": round(price, 2),
                "change_5d": round(float(change_5d), 2),
                "change_7d": round(float(change_7d), 2),
                "change_20d": round(float(change_20d), 2),
            }
        except Exception:
            continue

    return results


def market_regime(benchmarks: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
    """Classify the current market regime from benchmark behavior.

    Returns:
        {"trend": "bullish|bearish|mixed", "risk": "on|off|neutral", "leadership": "growth|value|defensive"}
    """
    voo = benchmarks.get("VOO", {}).get("change_7d", 0.0)
    qqq = benchmarks.get("QQQ", {}).get("change_7d", 0.0)
    iwm = benchmarks.get("IWM", {}).get("change_7d", 0.0)
    tlt = benchmarks.get("TLT", {}).get("change_7d", 0.0)
    gld = benchmarks.get("GLD", {}).get("change_7d", 0.0)

    if voo > 1 and qqq > 1:
        trend = "bullish"
    elif voo < -1 and qqq < -1:
        trend = "bearish"
    else:
        trend = "mixed"

    if iwm > voo and qqq > voo:
        risk = "on"
    elif tlt > voo and gld > voo:
        risk = "off"
    else:
        risk = "neutral"

    if qqq > voo + 1:
        leadership = "growth"
    elif iwm > voo + 1:
        leadership = "small-cap"
    elif tlt > 0 and voo < 0:
        leadership = "defensive"
    else:
        leadership = "broad"

    return {"trend": trend, "risk": risk, "leadership": leadership}

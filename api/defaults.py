"""Default seed data for new users (and anonymous browsers).

The frontend renders DEFAULT_TICKERS to anonymous visitors via
`GET /api/tickers/defaults`. On first login the user's watchlist is
seeded from this list (only when their watchlist is empty so existing
users are never overwritten).
"""
from __future__ import annotations

from typing import List


DEFAULT_TICKERS: List[str] = [
    "NVDA", "GEV", "MU", "SNDK", "GOOG", "NBIS", "AAPL",
    "AMZN", "AMD", "INTC", "TSM", "RKLB", "ASTS", "IONQ",
    "MRVL", "VTIAX",
]

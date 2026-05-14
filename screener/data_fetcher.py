import time
import warnings
from typing import Dict, List, Optional

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)


def fetch_batch(
    tickers: List[str],
    period: str = "35d",
    chunk_size: int = 100,
    sleep_sec: float = 2.0,
    max_retries: int = 3,
) -> Dict[str, pd.DataFrame]:
    results: Dict[str, pd.DataFrame] = {}
    chunks = [tickers[i : i + chunk_size] for i in range(0, len(tickers), chunk_size)]

    for idx, chunk in enumerate(chunks):
        if idx > 0:
            time.sleep(sleep_sec)
        data = _download_with_retry(chunk, period, max_retries)
        if data is None:
            continue
        for ticker in chunk:
            df = _extract_ticker(data, ticker)
            if df is not None and len(df) >= 10:
                results[ticker] = df

    return results


def _download_with_retry(
    tickers: List[str], period: str, max_retries: int
) -> Optional[pd.DataFrame]:
    delay = 2.0
    for attempt in range(max_retries):
        try:
            data = yf.download(
                tickers,
                period=period,
                auto_adjust=True,
                progress=False,
                threads=True,
            )
            return data
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
    return None


def _extract_ticker(data: pd.DataFrame, ticker: str) -> Optional[pd.DataFrame]:
    try:
        if isinstance(data.columns, pd.MultiIndex):
            if ticker not in data.columns.get_level_values(1):
                return None
            df = data.xs(ticker, axis=1, level=1).copy()
        else:
            df = data.copy()

        df = df.dropna(how="all")
        required = {"Open", "High", "Low", "Close", "Volume"}
        if not required.issubset(df.columns):
            return None
        return df
    except Exception:
        return None

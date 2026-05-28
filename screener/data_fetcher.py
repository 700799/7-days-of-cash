"""Concurrent yfinance batch downloader with cache integration and retries."""

from __future__ import annotations

import time
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

import pandas as pd
import yfinance as yf

from .cache import OHLCVCache
from .logger import get_logger

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

log = get_logger("best7days.fetch")


def fetch_batch(
    tickers: List[str],
    period: str = "35d",
    chunk_size: int = 60,
    max_workers: int = 4,
    sleep_sec: float = 0.5,
    max_retries: int = 3,
    cache: OHLCVCache | None = None,
    use_cache: bool = True,
) -> Dict[str, pd.DataFrame]:
    """Fetch OHLCV for many tickers concurrently with cache + retry.

    Strategy:
      1. Pull all cached fresh entries in one query.
      2. Split missing tickers into chunks and download chunks in parallel threads.
      3. Persist results to cache.

    Returns a dict {ticker: DataFrame}.
    """
    results: Dict[str, pd.DataFrame] = {}
    missing = tickers

    if cache is None and use_cache:
        cache = OHLCVCache()

    if cache and use_cache:
        results = cache.get_many(tickers, period)
        missing = [t for t in tickers if t not in results]
        log.info("cache hits=%d misses=%d", len(results), len(missing))

    if not missing:
        return results

    chunks = [missing[i : i + chunk_size] for i in range(0, len(missing), chunk_size)]
    log.info(
        "downloading %d tickers across %d chunks (workers=%d)",
        len(missing),
        len(chunks),
        max_workers,
    )

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {
            ex.submit(_download_chunk, chunk, period, max_retries): chunk for chunk in chunks
        }
        for fut in as_completed(futures):
            chunk = futures[fut]
            try:
                data = fut.result()
            except Exception as e:
                log.warning("chunk failed: %s (%d tickers)", e, len(chunk))
                continue
            if data is None:
                continue
            new_dfs: Dict[str, pd.DataFrame] = {}
            for ticker in chunk:
                df = _extract_ticker(data, ticker)
                if df is not None and len(df) >= 10:
                    new_dfs[ticker] = df
            results.update(new_dfs)
            if cache and use_cache:
                cache.put_many(new_dfs, period)
            time.sleep(sleep_sec)  # courtesy pause between completed chunks

    log.info("fetched %d/%d tickers", len(results), len(tickers))
    return results


def _download_chunk(tickers: List[str], period: str, max_retries: int) -> pd.DataFrame | None:
    delay = 1.0
    for attempt in range(max_retries):
        try:
            data = yf.download(
                tickers,
                period=period,
                auto_adjust=True,
                progress=False,
                threads=True,
                group_by="ticker",
            )
            return data
        except Exception as e:
            log.debug("chunk attempt %d failed: %s", attempt + 1, e)
            if attempt < max_retries - 1:
                time.sleep(delay)
                delay *= 2
    return None


def _extract_ticker(data: pd.DataFrame, ticker: str) -> pd.DataFrame | None:
    try:
        if isinstance(data.columns, pd.MultiIndex):
            # Try level=0 (group_by='ticker') first, then level=1
            try:
                df = data[ticker].copy()
            except KeyError:
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

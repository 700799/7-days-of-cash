"""Best7DaysMula — multi-agent 7-day uptrend stock screener."""
from .benchmarks import fetch_benchmarks, market_regime
from .cache import OHLCVCache
from .data_fetcher import fetch_batch
from .exporter import save_outputs
from .filters import apply_filters
from .logger import get_logger
from .metrics import compute_metrics
from .orchestrator import score_records
from .scheduler import generate_cron, watch
from .universe import get_extended_tickers, get_sp500_tickers, load_custom_tickers

__version__ = "2.0.0"

__all__ = [
    "__version__",
    "fetch_benchmarks", "market_regime",
    "OHLCVCache", "fetch_batch",
    "save_outputs", "apply_filters",
    "get_logger", "compute_metrics",
    "score_records", "generate_cron", "watch",
    "get_extended_tickers", "get_sp500_tickers", "load_custom_tickers",
]

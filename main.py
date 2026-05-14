#!/usr/bin/env python3
"""
Best7DaysMula — 7-day uptrend stock screener.
Run:  python main.py [options]
"""
import argparse
import sys
import time
import warnings
from typing import Any, Dict

import yaml
from rich.console import Console

warnings.filterwarnings("ignore")
console = Console()

# ── helpers ──────────────────────────────────────────────────────────────────

def _load_config(path: str = "config.yaml") -> Dict[str, Any]:
    try:
        with open(path) as f:
            raw = yaml.safe_load(f)
        cfg: Dict[str, Any] = {}
        cfg.update(raw.get("filters", {}))
        cfg.update(raw.get("output", {}))
        cfg.update(raw.get("fetch", {}))
        return cfg
    except FileNotFoundError:
        return {}


def _apply_cli_overrides(cfg: Dict[str, Any], args: argparse.Namespace) -> None:
    if args.min_price   is not None: cfg["min_price"]    = args.min_price
    if args.min_gain    is not None: cfg["min_gain_7d"]  = args.min_gain
    if args.min_volume  is not None: cfg["min_avg_volume"] = args.min_volume
    if args.max_rsi     is not None: cfg["max_rsi"]      = args.max_rsi
    if args.cap         is not None: cfg["market_cap"]   = args.cap
    if args.top         is not None: cfg["top_n"]        = args.top
    if args.json:                    cfg["save_json"]     = True


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="best7days",
        description="7-day uptrend stock screener — gstack style",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # interactive pill-toggle mode
  python main.py --no-interactive         # headless, config.yaml defaults
  python main.py --min-gain 12 --top 15  # custom thresholds
  python main.py --cap small --json       # small caps, save JSON too
  python main.py --tickers-file my.txt    # custom ticker list
""",
    )
    parser.add_argument("--min-price",   type=float, help="Minimum stock price (default 2.0)")
    parser.add_argument("--min-gain",    type=float, help="Minimum 7-day gain %% (default 8.0)")
    parser.add_argument("--min-volume",  type=int,   help="Minimum 20d avg volume (default 500000)")
    parser.add_argument("--max-rsi",     type=float, help="Maximum RSI(14) (default 80)")
    parser.add_argument("--cap",         choices=["small", "mid", "large", "all"], help="Market cap filter")
    parser.add_argument("--top",         type=int,   help="Number of results to show (default 25)")
    parser.add_argument("--json",        action="store_true", help="Also save results as JSON")
    parser.add_argument("--no-interactive", action="store_true", help="Skip pill-toggle UI, use config defaults")
    parser.add_argument("--tickers-file", type=str,  help="Path to custom tickers .txt file")
    parser.add_argument("--config",      type=str,   default="config.yaml", help="Config file path")
    parser.add_argument("--no-strategy", action="store_true", help="Skip strategy guide display")

    args = parser.parse_args()

    # ── imports (here so banner shows first) ─────────────────────────────────
    from screener.ui import (
        print_banner,
        run_pill_toggles,
        print_market_summary,
        print_results_table,
        print_strategy_guide,
        print_summary_stats,
        save_outputs,
        console as ui_console,
    )
    from screener.universe import get_extended_tickers, load_custom_tickers
    from screener.data_fetcher import fetch_batch
    from screener.metrics import compute_metrics
    from screener.filters import apply_filters
    from screener.benchmarks import fetch_benchmarks

    G = "bright_green"
    DG = "green"

    # ── banner ────────────────────────────────────────────────────────────────
    print_banner()

    # ── config ────────────────────────────────────────────────────────────────
    cfg = _load_config(args.config)
    _apply_cli_overrides(cfg, args)

    # ── pill toggles ──────────────────────────────────────────────────────────
    if not args.no_interactive:
        active_filters = run_pill_toggles()
        cfg["active_filters"] = active_filters
    else:
        cfg["active_filters"] = set()   # empty = apply all defaults

    # ── ticker universe ───────────────────────────────────────────────────────
    console.print(f"[bold {G}]> BUILDING UNIVERSE...[/]")
    if args.tickers_file:
        tickers = load_custom_tickers(args.tickers_file)
        console.print(f"[{DG}]  Custom list: {len(tickers)} tickers[/]")
    else:
        tickers = get_extended_tickers()
        console.print(f"[{DG}]  S&P 500 + Extended: {len(tickers)} tickers[/]")
    console.print()

    # ── fetch benchmarks (parallel with main data) ────────────────────────────
    console.print(f"[bold {G}]> FETCHING BENCHMARKS...[/]")
    benchmarks = fetch_benchmarks(period=cfg.get("period", "35d"))
    for tkr, info in benchmarks.items():
        sign = "+" if info["change_7d"] >= 0 else ""
        color = G if info["change_7d"] >= 0 else "red"
        console.print(
            f"  [{G}]{tkr}[/]  [{color}]{sign}{info['change_7d']:.2f}%[/]  [{DG}]{info['name']}[/]"
        )
    console.print()

    # ── fetch OHLCV ───────────────────────────────────────────────────────────
    console.print(f"[bold {G}]> SCANNING {len(tickers):,} TICKERS...[/]")
    console.print(f"[{DG}]  Period: {cfg.get('period','35d')}  |  Chunk: {cfg.get('chunk_size',100)}  |  Sleep: {cfg.get('sleep_between_chunks',2)}s[/]")
    console.print()

    t0 = time.time()
    raw_data = fetch_batch(
        tickers,
        period=cfg.get("period", "35d"),
        chunk_size=cfg.get("chunk_size", 100),
        sleep_sec=cfg.get("sleep_between_chunks", 2),
        max_retries=cfg.get("max_retries", 3),
    )
    console.print(f"[{DG}]  Data fetched for {len(raw_data):,} tickers[/]")

    # ── compute metrics ───────────────────────────────────────────────────────
    console.print(f"[{DG}]  Computing metrics...[/]")
    records = []
    for ticker, df in raw_data.items():
        m = compute_metrics(ticker, df)
        if m is not None:
            records.append(m)

    elapsed = time.time() - t0
    console.print(f"[{DG}]  {len(records):,} valid records computed in {elapsed:.1f}s[/]")
    console.print()

    # ── apply filters ─────────────────────────────────────────────────────────
    console.print(f"[bold {G}]> APPLYING FILTERS...[/]")
    results_df = apply_filters(records, cfg)
    console.print(f"[{DG}]  {len(results_df)} leaders passed all filters[/]")
    console.print()

    if results_df.empty:
        console.print(f"[yellow]  No stocks passed the current filters. Try relaxing thresholds.[/]")
        sys.exit(0)

    # ── display ───────────────────────────────────────────────────────────────
    print_market_summary(benchmarks)
    print_results_table(results_df, benchmarks)
    print_summary_stats(results_df, elapsed, len(raw_data))

    if not args.no_strategy:
        print_strategy_guide()

    # ── save ──────────────────────────────────────────────────────────────────
    save_outputs(
        results_df,
        output_dir=cfg.get("output_dir", "outputs"),
        save_json=cfg.get("save_json", False),
    )

    console.print(f"\n[bold {G}]> DONE.  Good trading.[/]\n")


if __name__ == "__main__":
    main()

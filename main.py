#!/usr/bin/env python3
"""Best7DaysMula -- multi-agent 7-day uptrend stock screener.

Usage:
    python main.py                              # interactive mode
    python main.py --no-interactive             # headless, config defaults
    python main.py --watch 15                   # refresh every 15 minutes
    python main.py --agents momentum,breakout   # only specific agents
    python main.py --formats csv,json,html      # multiple export formats
    python main.py --refresh-cache              # force re-download
    python main.py --gen-cron 30                # print a crontab line
"""
from __future__ import annotations

import argparse
import sys
import time
import warnings
from typing import Any, Dict

import yaml

warnings.filterwarnings("ignore")


def _load_config(path: str = "config.yaml") -> Dict[str, Any]:
    try:
        with open(path) as f:
            raw = yaml.safe_load(f) or {}
        cfg: Dict[str, Any] = {}
        cfg.update(raw.get("filters", {}))
        cfg.update(raw.get("output", {}))
        cfg.update(raw.get("fetch", {}))
        cfg.update(raw.get("cache", {}))
        cfg.update(raw.get("agents", {}))
        return cfg
    except FileNotFoundError:
        return {}


def _apply_cli_overrides(cfg: Dict[str, Any], args: argparse.Namespace) -> None:
    if args.min_price   is not None: cfg["min_price"]      = args.min_price
    if args.min_gain    is not None: cfg["min_gain_7d"]    = args.min_gain
    if args.min_volume  is not None: cfg["min_avg_volume"] = args.min_volume
    if args.max_rsi     is not None: cfg["max_rsi"]        = args.max_rsi
    if args.cap         is not None: cfg["market_cap"]     = args.cap
    if args.top         is not None: cfg["top_n"]          = args.top
    if args.formats:                 cfg["formats"]        = [f.strip() for f in args.formats.split(",")]
    if args.agents:                  cfg["agent_names"]    = [a.strip() for a in args.agents.split(",")]
    if args.cache_ttl   is not None: cfg["cache_ttl"]      = args.cache_ttl
    if args.workers     is not None: cfg["max_workers"]    = args.workers


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="best7days",
        description="Multi-agent 7-day uptrend stock screener -- gstack style",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                # interactive pill-toggle mode
  python main.py --no-interactive               # headless using config.yaml
  python main.py --min-gain 12 --top 15         # custom thresholds
  python main.py --cap small --formats csv,json # small caps, multiple outputs
  python main.py --watch 15                     # refresh every 15 minutes
  python main.py --watch 15 --market-hours-only # only during market hours
  python main.py --agents momentum,breakout     # restrict to specific agents
  python main.py --refresh-cache                # force re-download
  python main.py --gen-cron 30                  # print crontab line for 30m refresh
  python main.py --tickers-file my.txt          # use custom ticker file
""",
    )
    parser.add_argument("--min-price",   type=float)
    parser.add_argument("--min-gain",    type=float)
    parser.add_argument("--min-volume",  type=int)
    parser.add_argument("--max-rsi",     type=float)
    parser.add_argument("--cap",         choices=["small", "mid", "large", "all"])
    parser.add_argument("--top",         type=int)
    parser.add_argument("--formats",     type=str, help="Comma list: csv,json,xlsx,parquet,html,md")
    parser.add_argument("--agents",      type=str, help="Comma list of strategy agents")
    parser.add_argument("--no-interactive", action="store_true")
    parser.add_argument("--no-strategy",    action="store_true")
    parser.add_argument("--no-agents",      action="store_true", help="Skip agent scoring (faster)")
    parser.add_argument("--tickers-file", type=str)
    parser.add_argument("--config",      type=str, default="config.yaml")
    parser.add_argument("--watch",       type=int, metavar="MIN", help="Re-run every N minutes")
    parser.add_argument("--market-hours-only", action="store_true")
    parser.add_argument("--refresh-cache", action="store_true", help="Bypass cache for this run")
    parser.add_argument("--cache-ttl", type=int, help="Cache TTL in seconds (default 3600)")
    parser.add_argument("--workers",   type=int, help="Concurrent fetch workers (default 4)")
    parser.add_argument("--gen-cron",  type=int, metavar="MIN", help="Print crontab line and exit")
    parser.add_argument("--verbose",   action="store_true")
    return parser


def run_once(args: argparse.Namespace, interactive: bool = True) -> None:
    """One full pass: fetch, score, filter, render, save."""
    from screener import (
        OHLCVCache, apply_filters, compute_metrics, fetch_batch,
        fetch_benchmarks, get_logger, market_regime, save_outputs,
        score_records, get_extended_tickers, load_custom_tickers,
    )
    from screener.ui import (
        console, print_banner, print_market_summary, print_results_table,
        print_save_summary, print_strategy_guide, print_summary_stats,
        print_top_reasons, run_agent_toggles, run_pill_toggles,
    )

    log = get_logger("best7days", level="DEBUG" if args.verbose else "INFO",
                     log_file="outputs/screener.log")
    G, DG = "bright_green", "green"

    cfg = _load_config(args.config)
    _apply_cli_overrides(cfg, args)

    cache = OHLCVCache(ttl_sec=cfg.get("cache_ttl", 3600))
    print_banner(version="2.0", cache_stats=cache.stats())

    if interactive and not args.no_interactive:
        cfg["active_filters"] = run_pill_toggles()
        if not args.no_agents:
            cfg["agent_names"] = run_agent_toggles(set(cfg.get("agent_names", []) or [
                "momentum", "breakout", "volume_surge", "relative_strength", "mean_reversion"
            ]))
    else:
        cfg["active_filters"] = set()

    console.print(f"[bold {G}]> BUILDING UNIVERSE...[/]")
    if args.tickers_file:
        tickers = load_custom_tickers(args.tickers_file)
        console.print(f"[{DG}]  Custom list: {len(tickers)} tickers[/]")
    else:
        tickers = get_extended_tickers()
        console.print(f"[{DG}]  S&P 500 + Extended: {len(tickers)} tickers[/]")
    console.print()

    console.print(f"[bold {G}]> FETCHING BENCHMARKS...[/]")
    benchmarks = fetch_benchmarks(period=cfg.get("period", "35d"))
    for tkr, info in benchmarks.items():
        sign = "+" if info["change_7d"] >= 0 else ""
        color = G if info["change_7d"] >= 0 else "red"
        console.print(
            f"  [{G}]{tkr:<6}[/] [{color}]{sign}{info['change_7d']:>6.2f}%[/]  [{DG}]{info['name']}[/]"
        )
    regime = market_regime(benchmarks)
    console.print()

    console.print(f"[bold {G}]> SCANNING {len(tickers):,} TICKERS...[/]")
    console.print(
        f"[{DG}]  Period: {cfg.get('period','35d')}  |  "
        f"Workers: {cfg.get('max_workers', 4)}  |  Cache: {'OFF' if args.refresh_cache else 'ON'}[/]"
    )
    console.print()

    pre_stats = cache.stats()
    t0 = time.time()
    raw_data = fetch_batch(
        tickers,
        period=cfg.get("period", "35d"),
        chunk_size=cfg.get("chunk_size", 60),
        max_workers=cfg.get("max_workers", 4),
        sleep_sec=cfg.get("sleep_between_chunks", 0.5),
        max_retries=cfg.get("max_retries", 3),
        cache=cache,
        use_cache=not args.refresh_cache,
    )
    post_stats = cache.stats()
    cache_hits = max(0, post_stats["fresh"] - pre_stats["fresh"]) if not args.refresh_cache else 0
    console.print(f"[{DG}]  Fetched: {len(raw_data):,} tickers in {time.time()-t0:.1f}s[/]")

    console.print(f"[{DG}]  Computing metrics...[/]")
    records = [m for t, df in raw_data.items() if (m := compute_metrics(t, df)) is not None]
    console.print(f"[{DG}]  {len(records):,} valid records[/]")
    console.print()

    if not args.no_agents and records:
        console.print(f"[bold {G}]> RUNNING {len(cfg.get('agent_names') or 5)} STRATEGY AGENTS...[/]")
        scored = score_records(
            records,
            benchmarks=benchmarks,
            regime=regime,
            agent_names=cfg.get("agent_names"),
        )
        records_for_filter = scored.to_dict(orient="records")
    else:
        records_for_filter = records
        scored = None

    console.print(f"[bold {G}]> APPLYING FILTERS...[/]")
    results_df = apply_filters(records_for_filter, cfg)
    console.print(f"[{DG}]  {len(results_df)} leaders passed[/]")
    console.print()

    if results_df.empty:
        console.print("[yellow]  No stocks passed filters. Try relaxing thresholds.[/]")
        return

    elapsed = time.time() - t0
    print_market_summary(benchmarks, regime)
    print_results_table(results_df, benchmarks, show_agents=not args.no_agents)
    print_summary_stats(results_df, elapsed, len(raw_data), cache_hits=cache_hits)
    if not args.no_agents:
        print_top_reasons(results_df, n=5)
    if not args.no_strategy:
        print_strategy_guide()

    formats = cfg.get("formats") or ["csv"]
    paths = save_outputs(
        results_df, output_dir=cfg.get("output_dir", "outputs"), formats=formats,
    )
    print_save_summary(paths)
    console.print(f"\n[bold {G}]> DONE.  Good trading.[/]\n")


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if args.gen_cron is not None:
        from screener.scheduler import generate_cron
        cmd = f"cd {sys.path[0] or '.'} && python main.py --no-interactive --no-strategy"
        line = generate_cron(args.gen_cron, cmd, market_hours_only=True)
        print(line)
        sys.exit(0)

    if args.watch is not None:
        from screener.scheduler import watch
        watch(
            task=lambda: run_once(args, interactive=False),
            interval_minutes=args.watch,
            market_hours_only=args.market_hours_only,
        )
    else:
        run_once(args, interactive=not args.no_interactive)


if __name__ == "__main__":
    main()

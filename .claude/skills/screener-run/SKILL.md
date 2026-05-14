---
name: screener-run
description: Run the Best7DaysMula multi-agent stock screener. Use this skill when the user wants to scan for stocks trending strongly upward over the last 7 days with volume confirmation. Examples - "run the screener", "find me the best stocks this week", "scan for uptrends", "what are today's leaders".
---

# Run the Best7DaysMula Screener

## When to use
The user wants to run a fresh stock screen. Triggers include: "run the screener", "scan", "find me leaders", "show me uptrends", "what's moving", "screen for breakouts/momentum".

## What it does
Scans the S&P 500 + Extended Market universe (700+ tickers), computes 20+ technical indicators, runs five strategy agents (momentum, breakout, volume surge, relative strength, mean reversion), filters with user-configurable thresholds, and compares results against seven benchmarks (VOO, QQQ, VXF, IWM, VTIAX, GLD, TLT).

## How to invoke
From the repository root:

```bash
# Full interactive mode (pill-toggle filters and agents)
python main.py

# Headless one-shot using config.yaml defaults
python main.py --no-interactive

# Common variations
python main.py --min-gain 12 --top 20            # tighter gain filter, top 20
python main.py --agents momentum,breakout         # subset of agents
python main.py --cap small --formats csv,json,html
python main.py --no-interactive --refresh-cache   # bypass SQLite cache
```

## Reading the output
- **Composite SCORE** (0-100, bright green) — weighted aggregate across active agents
- **MOM / BRK / VOL / RS / MR columns** — per-agent scores (75+ = strong)
- **STRATEGY column** — highest-scoring agent for that stock
- **vs VOO / vs QQQ** — alpha vs S&P 500 and Nasdaq 100 over 7 days
- **REGIME row** — current market regime (bullish/bearish, risk-on/off, leadership)

## Tips
- Results auto-save to `outputs/screener_YYYYMMDD_HHMMSS.<fmt>` and `screener_latest.csv`
- Use `--refresh-cache` after market close to get end-of-day data
- For watch mode (auto-refresh) use the `screener-watch` skill

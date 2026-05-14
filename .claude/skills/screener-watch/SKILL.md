---
name: screener-watch
description: Start the Best7DaysMula screener in watch mode — re-runs automatically every N minutes during market hours. Use when the user says "watch the market", "keep refreshing the screener", "monitor uptrends", "auto-refresh", or wants continuous intraday updates.
---

# Watch Mode — Continuous Screener Refresh

## When to use
User wants the screener to keep running on a schedule. Triggers: "watch", "monitor", "auto-refresh", "keep an eye", "run every N minutes", "intraday tracking".

## What it does
Runs the screener in a loop, refreshing every N minutes. SQLite cache absorbs most of the API load; only stocks with stale data get re-fetched. Optionally restricts to US market hours (M-F 9:30-16:00 ET).

## How to invoke

```bash
# Refresh every 15 minutes (24/7)
python main.py --watch 15

# Refresh every 15 minutes, but only during market hours
python main.py --watch 15 --market-hours-only

# Short interval for active trading
python main.py --watch 5 --no-interactive --no-strategy --market-hours-only

# Long interval for end-of-day review
python main.py --watch 60 --market-hours-only
```

## Stopping
Press `Ctrl-C` to exit cleanly.

## Background / detached run
```bash
nohup python main.py --watch 15 --market-hours-only --no-interactive --no-strategy \
  > outputs/watch.log 2>&1 &
```

## Cron alternative
If the user prefers system cron over a long-running process:

```bash
python main.py --gen-cron 30
# Prints:  30 9-16 * * 1-5 cd /path && python main.py --no-interactive --no-strategy
```

Then `crontab -e` and paste the line.

## Tips
- Cache TTL defaults to 1 hour — set `--cache-ttl 300` for fresher data with more API hits
- The first run downloads everything; subsequent runs are mostly cache hits (often <5s)
- Watch log is written to `outputs/screener.log` with rotation at 5MB

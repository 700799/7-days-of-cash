---
name: screener-config
description: Modify the Best7DaysMula screener configuration (filter thresholds, active agents, export formats, cache TTL). Use when the user wants to "tighten/loosen filters", "change thresholds", "add/remove agents", "configure the screener", or "edit config".
---

# Configure the Screener

## When to use
User wants to change persistent settings without typing CLI flags every run. Triggers: "tighten filters", "loosen the gain threshold", "only run momentum and breakout", "save as Excel", "change the cache to refresh every 10 minutes".

## What to edit
Open `config.yaml` at the repo root and modify the relevant section:

```yaml
filters:
  min_price: 2.00            # raise to 5.00 to skip cheap stocks
  min_gain_7d: 8.0           # raise to 15.0 for stronger trends only
  min_avg_volume: 500000     # raise to 1_000_000 for liquidity
  min_dollar_vol: 5000000    # daily dollar volume floor
  max_rsi: 80                # lower to 70 to avoid extended names
  min_pct_52w_high: -15.0    # raise to -5.0 for breakouts only
  market_cap: "all"          # small | mid | large | all
  exclude_extreme_volatility: true

agents:
  agent_names:               # comment out to disable individual agents
    - momentum
    - breakout
    - volume_surge
    - relative_strength
    - mean_reversion

output:
  top_n: 25                  # number of results to show
  formats:                   # csv | json | xlsx | parquet | html | md
    - csv
    - json

fetch:
  chunk_size: 60             # tickers per concurrent request
  max_workers: 4             # parallel download threads (raise to 8 on fast net)
  period: "35d"

cache:
  cache_ttl: 3600            # seconds; 300 = 5 min, 86400 = 1 day
```

## Reload behavior
Changes take effect on the next `python main.py` run. No restart needed.

## CLI overrides
Every config value can also be overridden via CLI flags (e.g. `--min-gain 12 --top 50`) without modifying the file.

# Best7DaysMula

> 7-day uptrend screener. Volume confirmed. Benchmark compared.
> One mission: find the leaders.

```
garrytan@ycombinator:~$ python main.py
```

---

## > WHAT IS THIS?

A terminal-native stock screener that finds stocks trending strongly upward over the last **7 trading days**, confirmed by rising volume — displayed in a gstack-style green-on-black terminal UI.

- Scans **S&P 500 + Extended Market** (~700+ tickers)
- Computes 7-day %, RSI(14), relative volume, volume trend slope
- Compares results against **VOO**, **VXF**, and **VTIAX** benchmarks
- Interactive **pill-toggle filters** — toggle each filter on/off before scanning
- Saves timestamped **CSV** (and optional **JSON**) to `outputs/`

---

## > INSTALL IN 30 SECONDS

```bash
git clone <repo>
cd Best7DaysMula
pip install -r requirements.txt
python main.py
```

---

## > QUICK START

```bash
# Interactive mode (pill-toggle filters)
python main.py

# Headless mode (use config.yaml defaults)
python main.py --no-interactive

# Custom thresholds
python main.py --min-gain 12 --top 15 --max-rsi 75

# Small caps only, save JSON too
python main.py --cap small --json

# Custom ticker list
python main.py --tickers-file my_watchlist.txt --no-interactive

# Skip strategy guide
python main.py --no-strategy
```

---

## > BY THE NUMBERS

| Metric | Default |
|---|---|
| Lookback | 7 trading days |
| Min price | $2.00 |
| Min 7-day gain | +8% |
| Min avg volume (20d) | 500,000 shares |
| Max RSI(14) | 80 |
| Results shown | Top 25 |

---

## > BENCHMARKS

| Ticker | Name | Represents |
|---|---|---|
| **VOO** | Vanguard S&P 500 ETF | Large-cap US equities |
| **VXF** | Vanguard Extended Market ETF | Small+mid-cap US (ex-S&P 500) |
| **VTIAX** | Vanguard Total Intl Stock Index | International developed + EM |

The screener shows each stock's 7-day return **vs VOO** and **vs VXF** so you can instantly see which names are outperforming the market.

---

## > METRICS EXPLAINED

| Column | Description |
|---|---|
| **7d %** | Percentage gain over 7 trading days |
| **vs VOO** | Alpha vs S&P 500 over same 7 days |
| **vs VXF** | Alpha vs Extended Market over same 7 days |
| **AVG VOL** | 20-day average daily volume |
| **REL VOL** | Today's volume / 20d avg (>1.5x = elevated) |
| **VOL up 5d** | Linear regression slope on 5-day volume (up = rising) |
| **VOL up 7d** | Same for 7-day volume |
| **RSI** | 14-period RSI with Wilder smoothing |
| **SIGNAL** | Automated label based on combined metrics |

---

## > STRATEGY GUIDE

### MOMENTUM
Buy stocks already trending up. Strong 7d% + rising volume = institutional accumulation.
- Entry: Pullback to 5-day EMA
- Exit: RSI > 80 or volume collapses

### BREAKOUT
Look for stocks breaking above resistance with massive volume.
- Rel Vol > 2.0x on breakout day, RSI crossing above 60
- Entry: Break + close above key level
- Exit: Close back below breakout level

### VOLUME SURGE
Smart money moves in before price. Volume leads price by 1-3 days.
- Vol Trend 5d AND 7d both rising, Rel Vol > 1.5x average
- Entry: On surge day or next open
- Exit: Volume drops below average

### RELATIVE STRENGTH
True leaders outperform in both up and down markets.
- Stock 7d% >> VOO + VXF; the "vs VOO" column quantifies your alpha
- Entry: RS leaders hold longer
- Exit: When RS line rolls over

---

## > PILL-TOGGLE FILTERS

On launch, an interactive checklist lets you toggle filters on/off with spacebar:

```
[ PRICE >= $2 ]        checked  on by default
[ GAIN >= +8% (7d) ]   checked  on by default
[ AVG VOL >= 500K ]    checked  on by default
[ RSI <= 80 ]          checked  on by default
[ MARKET CAP FILTER ]  checked  on by default
[ EXCLUDE VOLATILE ]   checked  on by default
```

---

## > CONFIG FILE

Edit `config.yaml` to change defaults permanently:

```yaml
filters:
  min_price: 2.00
  min_gain_7d: 8.0
  min_avg_volume: 500000
  max_rsi: 80
  market_cap: "all"           # small | mid | large | all
  exclude_extreme_volatility: true

output:
  top_n: 25
  save_csv: true
  save_json: false
  output_dir: "outputs"
```

---

## > FILE STRUCTURE

```
Best7DaysMula/
├── screener/
│   ├── universe.py       # Ticker universe (S&P500 + Extended)
│   ├── data_fetcher.py   # yfinance batch download + retry logic
│   ├── metrics.py        # RSI, volume trend, % change calculations
│   ├── filters.py        # Configurable filter logic
│   ├── benchmarks.py     # VOO / VXF / VTIAX comparison
│   └── ui.py             # gstack-style Rich terminal UI
├── main.py               # CLI entry point
├── config.yaml           # Default filter thresholds
├── outputs/              # Timestamped CSV/JSON results
└── requirements.txt
```

---

## > DATA SOURCE

Primary: yfinance (Yahoo Finance)
- Batch downloads in chunks of 100 tickers
- 2-second sleep between chunks (rate limiting)
- 3 retries with exponential backoff on failure

---

Free. No API key required. Run it daily.

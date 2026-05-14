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

## > WEB APP (NEW)

In addition to the terminal CLI, Best7DaysMula now ships with a full web UI:
**Next.js 14** frontend + **FastAPI** backend + **Postgres (Neon)** storage + **Google OAuth**, deployable to **Vercel free tier**.

### Features
- Add/remove tickers via a form box; each ticker becomes a CRUD-able pill button
- Per-ticker news + general market news at the bottom of every page
- Sign in with Google to save your watchlist across sessions
- Run the screener against your watchlist or the full S&P 500 universe

### Quickstart

```bash
# 1. Backend
cp .env.example .env
# edit .env: paste your GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET
# generate a session secret:  openssl rand -hex 32
pip install -r requirements.txt
./scripts/run_api.sh                 # http://localhost:8000

# 2. Frontend (in a second terminal)
cd web
cp .env.local.example .env.local
npm install
npm run dev                          # http://localhost:3000
```

### Google OAuth setup
1. Go to https://console.cloud.google.com → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID (Web application)
3. Authorized redirect URI: `http://localhost:8000/api/auth/callback`
4. Copy the Client ID and Secret into `.env`

### Architecture

```
Best7DaysMula/
├── screener/          # Original CLI engine (agents, metrics, filters)
├── api/               # FastAPI backend (auth, tickers, news, screener)
├── web/               # Next.js 14 frontend (App Router, Tailwind, Vitest)
├── tests/             # Pytest suite — 55 tests covering both engine + API
└── data/              # DuckDB file (gitignored)
```

### Tests

```bash
pytest                 # backend: 55 tests
cd web && npm test     # frontend: 14 tests
```

### API surface
- `GET  /api/auth/me`, `GET /api/auth/login/google`, `POST /api/auth/logout`
- `GET|POST /api/tickers`, `PATCH|DELETE /api/tickers/{symbol}`, `GET /api/tickers/defaults`
- `GET  /api/news/ticker/{symbol}`, `GET /api/news/market`, `GET /api/news/trending`
- `GET  /api/movers/{symbol}`, `GET /api/movers?symbols=A,B,C`
- `GET  /api/preferences`, `PATCH /api/preferences`
- `POST /api/screener/run`
- `POST /api/cron/refresh`, `POST /api/cron/digest` (Bearer-auth, Vercel Cron only)

---

## > DEPLOY TO VERCEL (FREE)

```bash
# 1. Create a free Neon Postgres database — https://neon.tech
#    Copy the connection string (looks like: postgresql://user:pass@xxx.neon.tech/db?sslmode=require)

# 2. Push this branch to GitHub (you've done this already)

# 3. In Vercel:
#    - Import the repo
#    - Set environment variables (see .env.example):
#        DATABASE_URL          (from Neon)
#        GOOGLE_CLIENT_ID      (from Google Cloud Console OAuth)
#        GOOGLE_CLIENT_SECRET
#        SESSION_SECRET        (openssl rand -hex 32)
#        CRON_SECRET           (openssl rand -hex 32)
#        FRONTEND_URL          (https://your-app.vercel.app)
#        BACKEND_URL           (same — they share the domain on Vercel)
#        RESEND_API_KEY        (optional; if unset, falls back to SMTP)
#    - Deploy

# 4. After first deploy, run the migration ONCE:
#    From Vercel CLI:  vercel env pull .env  &&  python scripts/migrate.py
#    Or trigger /api/cron/refresh manually with the Bearer token.
```

Free tier limits stay clear because:
- **Pre-computed screener** — full S&P 500 runs in cron every 4h (writes to Postgres). UI just reads → < 100ms.
- **Cached everything** — news 4h TTL, movers 4h TTL, symbol validation 24h TTL.
- **2 cron jobs** total (Vercel Hobby allows 2 free).
- **No LLM calls** — "why it moved" uses heuristic (price + headlines).

---

## > SECURITY & ABUSE PROTECTION

- **Rate limits** (per-user when logged in via cookie, else per-IP):
  - 60/min default for cheap reads
  - 30/min for `/api/news/*`
  - 20/min for write ops (POST/PATCH/DELETE on watchlist)
  - 10/min for `/api/auth/*` (slows brute-force)
  - 5/min for `/api/screener/run` (the only endpoint that hits yfinance live)
- **CORS**: strict allowlist (no wildcard with credentials), only your `FRONTEND_URL` + dev localhost.
- **Body cap**: 64 KB max — any oversized POST returns 413 before parsing.
- **Cron auth**: `/api/cron/*` requires `Authorization: Bearer ${CRON_SECRET}`, timing-safe compared. Returns 503 if `CRON_SECRET` env var is unset (refuse rather than allow).
- **Live screener cap**: `/api/screener/run` rejects requests with > 50 tickers (use `/api/screener/cached` for the full universe).
- **Symbol validation cache**: prevents repeated yfinance probing for the same invalid symbol (24h TTL per symbol).
- **Security headers** (set in `vercel.json`): `X-Frame-Options: DENY`, HSTS preload, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` denying camera/mic/geo.
- **`X-Robots-Tag: noindex, nofollow`** on every `/api/*` response — search engines won't index your data endpoints.
- **`robots.txt`** blocks aggressive scrapers (Ahrefs, Semrush, MJ12, DotBot) and disallows crawling of `/api/`.

### Estimated free-tier cost ceiling

| Concern | Mitigation | Result |
|---|---|---|
| Yahoo Finance abuse | 4h news cache + 4h movers cache + cron-pre-compute + 5/min `/screener/run` | Effectively no live yfinance hits from public traffic |
| Vercel function invocations | All reads served from Postgres cache; 2 crons; rate limits | Well under 100k invocations/mo Hobby cap |
| Neon Postgres usage | Schema fits in < 50 MB; one row/user; cache rows TTL'd | Well under 0.5 GB / 100h compute Hobby cap |
| Resend email | 1 digest/user/day max enforced server-side via `last_sent_at`; daily cron only | Easily under 100/day Resend free tier |
| LLM tokens | None used — "why it moved" is heuristic | $0/mo |

---

Free. No API key required for the CLI. Run it daily.

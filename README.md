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
**Next.js 14** frontend + **Cloudflare Worker** backend (TypeScript/Hono) + **D1 (SQLite)** storage + **Google OAuth**, deployable to the **Cloudflare free tier**.

> The Python FastAPI backend under `api/` is **legacy** (Vercel-era) — kept for
> reference, no longer the deploy path. The screener engine was ported to
> TypeScript in `worker/src/engine/` with fixture-verified numerical parity.

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
├── worker/            # Cloudflare Worker (TypeScript) — THE deploy target
│   ├── src/engine/    #   Screener engine port (metrics, 5 agents, filters…)
│   ├── src/routes/    #   Hono API routes (auth, tickers, news, screener…)
│   ├── src/cron.ts    #   Rolling refresh + assembly + alerts + digests
│   ├── migrations/    #   D1 (SQLite) schema
│   └── test/          #   Vitest incl. Python↔TS parity fixtures
├── web/               # Next.js 14 frontend (static export, Tailwind, Vitest)
├── screener/          # Original Python CLI engine (still works locally)
├── api/               # LEGACY: FastAPI backend from the Vercel era
└── scripts/           # gen_universe.py, gen_parity_fixtures.py, …
```

### Tests

```bash
cd worker && npm test  # engine parity vs Python fixtures: 37 tests
cd web && npm test     # frontend: 44 tests
pytest                 # legacy Python suite (engine + old API): 174 tests
```

**Engine parity**: `scripts/gen_parity_fixtures.py` runs the Python engine on
synthetic OHLCV series and dumps every metric, agent score, reason string, and
composite ranking to `worker/test/fixtures/engine_parity.json`. The TS tests
assert the port reproduces all of it. Regenerate after changing either engine.

### API surface
- `GET  /api/auth/me`, `GET /api/auth/login/google`, `POST /api/auth/logout`
- `GET|POST /api/tickers`, `PATCH|DELETE /api/tickers/{symbol}`, `GET /api/tickers/defaults`
- `GET  /api/news/ticker/{symbol}`, `GET /api/news/market`, `GET /api/news/trending`
- `GET  /api/movers/{symbol}`, `GET /api/movers?symbols=A,B,C`
- `GET  /api/preferences`, `PATCH /api/preferences`
- `GET|POST /api/alerts`, `DELETE /api/alerts/{id}` (price alerts, emailed on trigger)
- `POST /api/screener/run` (live, ≤40 tickers) · `GET /api/screener/cached` · `GET /api/screener/top?n=10`
- `GET  /api/screener/history?days=7` · `GET /api/screener/share/{id}` (public) · `GET /api/screener/export` (CSV)
- `GET  /api/status` (refresh-pipeline health) · `GET /api/health`
- Scheduled work runs in the Worker's `scheduled()` handler (Cron Triggers) — no
  HTTP cron endpoints, so there is no CRON_SECRET to protect.

---

## > DEPLOY TO CLOUDFLARE (FREE)

One Worker serves everything: the API (Hono + D1) **and** the static Next.js
export, same-origin — no CORS, cookies just work.

```bash
# 0. Prereqs: a Cloudflare account + `npx wrangler login`

# 1. Create the D1 database and apply the schema
cd worker
npx wrangler d1 create b7dm            # copy the database_id it prints
#    → paste it into worker/wrangler.toml [[d1_databases]] database_id
npx wrangler d1 migrations apply b7dm --remote

# 2. Secrets (Google OAuth + optional Resend for email)
npx wrangler secret put GOOGLE_CLIENT_ID
npx wrangler secret put GOOGLE_CLIENT_SECRET
npx wrangler secret put RESEND_API_KEY          # optional — email digest/alerts

# 3. Set APP_ORIGIN in wrangler.toml [vars] to your production URL
#    (https://best7daysmula.<you>.workers.dev or your custom domain)

# 4. Build the frontend, then deploy the Worker (assets bundle in with it)
cd ../web && npm install && npm run build       # static export → web/out
cd ../worker && npm install && npx wrangler deploy

# 5. Google OAuth: add the production redirect URI in Google Cloud Console:
#    https://<your-app-domain>/api/auth/callback
```

### Local dev

```bash
cd worker
npx wrangler d1 migrations apply b7dm --local
npx wrangler dev                                # http://localhost:8787 (API + static app)
# Manually fire the refresh cron while developing:
npx wrangler dev --test-scheduled
curl "http://localhost:8787/__scheduled?cron=*/5+*+*+*+*"
# Watch the rolling refresh advance:
curl http://localhost:8787/api/status
```

### How it fits the free tier

- **Rolling slice refresh** — a cron fires every 5 minutes and fetches ~35
  tickers from Yahoo (staying under the 50-subrequest free-plan budget). The
  full ~620-ticker universe refreshes continuously (~90 min per lap). Once
  ≥70% of the universe is fresh, each tick also re-assembles the screener
  (pure math over D1 rows) and checks price alerts.
- On the **$5/mo Workers paid plan** (1000 subrequests/invocation) you can
  raise `SLICE_SIZE` in `worker/src/cron.ts` to cover the universe in 1–2
  invocations.
- **Cached everything in D1** — news 15min/1h TTL, movers 4h TTL, symbol
  validation 24h TTL, screener results persisted (last 200 runs).
- **No LLM calls** — "why it moved" uses a heuristic (price + headlines).

---

## > SECURITY & ABUSE PROTECTION

- **Sessions**: random 256-bit tokens (Web Crypto) stored server-side in D1;
  HttpOnly + SameSite=Lax + Secure cookies. No JWTs to leak.
- **OAuth hardening**: `state` parameter round-tripped through a short-lived
  HttpOnly cookie; token exchange server-side only.
- **CSRF**: SameSite=Lax cookies *plus* an Origin-header check on every
  mutating request (`POST/PATCH/DELETE` from a foreign origin → 403).
- **Input validation**: every request body/query parsed with zod — strict
  symbol regex (`^[A-Z][A-Z0-9.\-]{0,9}$`), bounded numbers, enum conditions.
- **Body cap**: 64 KB max — oversized payloads rejected with 413 before parsing.
- **Same-origin architecture**: frontend and API share one origin, so CORS is
  simply never enabled — there is no cross-origin surface to misconfigure.
- **No HTTP cron endpoints**: scheduled work runs in the Worker's internal
  `scheduled()` handler, unreachable from the network.
- **Live screener cap**: `/api/screener/run` rejects > 40 tickers (full
  universe comes from the pre-computed `/cached` endpoint).
- **Symbol validation cache** (24h TTL) prevents repeated Yahoo probing.
- **Security headers** on every response: `X-Frame-Options`, nosniff, HSTS
  (https only), `Referrer-Policy`, `Permissions-Policy`;
  `X-Robots-Tag: noindex` on `/api/*`.
- **Rate limiting**: add one free Cloudflare WAF rate-limiting rule for
  `/api/*` in the dashboard (Security → WAF → Rate limiting rules) — e.g.
  100 requests / 1 minute per IP. In-code caps bound the expensive paths.

### Estimated free-tier cost ceiling

| Concern | Mitigation | Result |
|---|---|---|
| Yahoo Finance abuse | 15min–4h D1 caches + pre-computed screener + 40-ticker live cap | Minimal live Yahoo hits from public traffic |
| Workers requests | Static assets + cached reads; 288 cron ticks/day | Well under 100k req/day free cap |
| Workers subrequests | 35-ticker slices + 7 benchmarks + ≤1 news refresh per tick | Under the 50/invocation free cap |
| D1 usage | ~620 metric rows + 200 result payloads + TTL'd caches | Well under 5 GB / 5M reads/day free cap |
| Resend email | 1 digest/user/day enforced via `last_sent_at`; alerts trigger once | Easily under 100/day Resend free tier |
| LLM tokens | None used — "why it moved" is heuristic | $0/mo |

---

Free. No API key required for the CLI. Run it daily.

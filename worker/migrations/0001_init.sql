-- Best7DaysMula D1 schema (SQLite).
-- Translated from the legacy Postgres schema in api/db.py; BYTEA/JSONB become TEXT.

CREATE TABLE IF NOT EXISTS users (
    id         TEXT PRIMARY KEY,
    email      TEXT NOT NULL,
    name       TEXT,
    picture    TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions (expires_at);

CREATE TABLE IF NOT EXISTS watchlists (
    user_id  TEXT NOT NULL,
    symbol   TEXT NOT NULL,
    note     TEXT,
    added_at TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, symbol)
);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id          TEXT PRIMARY KEY,
    digest_frequency TEXT NOT NULL DEFAULT 'none',
    digest_email     TEXT,
    last_sent_at     TEXT,
    updated_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS price_alerts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    TEXT NOT NULL,
    symbol     TEXT NOT NULL,
    condition  TEXT NOT NULL,
    target     REAL NOT NULL,
    triggered  INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE (user_id, symbol, condition, target)
);

-- Dormant: billing carried over for future activation.
CREATE TABLE IF NOT EXISTS subscriptions (
    user_id                TEXT PRIMARY KEY,
    stripe_customer_id     TEXT,
    stripe_subscription_id TEXT,
    plan                   TEXT NOT NULL DEFAULT 'free',
    status                 TEXT NOT NULL DEFAULT 'active',
    current_period_end     TEXT,
    updated_at             TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS news_cache (
    cache_key  TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS movers_cache (
    cache_key  TEXT PRIMARY KEY,
    payload    TEXT NOT NULL,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS symbol_validation_cache (
    symbol     TEXT PRIMARY KEY,
    valid      INTEGER NOT NULL,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS screener_results (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ran_at  TEXT DEFAULT (datetime('now')),
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_screener_results_ran_at ON screener_results (ran_at DESC);

-- One row per ticker: the full computed metric set from engine/metrics.ts.
-- Raw OHLCV is discarded after computation; closes_10d (JSON array of the last
-- 10 closes) is kept so movers can compute 1d/7d changes without a refetch.
CREATE TABLE IF NOT EXISTS ticker_metrics (
    ticker            TEXT PRIMARY KEY,
    price             REAL,
    change_5d         REAL,
    change_7d         REAL,
    change_20d        REAL,
    avg_vol_20d       INTEGER,
    rel_vol           REAL,
    vol_trend_5d      REAL,
    vol_trend_7d      REAL,
    dollar_vol_20d    INTEGER,
    ma_20             REAL,
    ma_50              REAL,
    ma_200            REAL,
    pct_from_ma20     REAL,
    pct_from_ma50     REAL,
    pct_from_52w_high REAL,
    rsi_14            REAL,
    atr_14            REAL,
    atr_pct           REAL,
    macd_hist         REAL,
    avg_range_pct     REAL,
    gap_pct           REAL,
    closes_10d        TEXT,
    fetched_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_ticker_metrics_fetched ON ticker_metrics (fetched_at);

-- Rolling-refresh slice cursor. Single row (id=1).
CREATE TABLE IF NOT EXISTS refresh_state (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    cursor          INTEGER NOT NULL DEFAULT 0,
    universe_size   INTEGER NOT NULL DEFAULT 0,
    last_slice_at   TEXT,
    last_assembly_at TEXT
);
INSERT OR IGNORE INTO refresh_state (id, cursor, universe_size) VALUES (1, 0, 0);

-- Benchmark snapshot (VOO/QQQ/VXF/IWM/VTIAX/GLD/TLT) refreshed each cron run.
CREATE TABLE IF NOT EXISTS benchmark_metrics (
    ticker     TEXT PRIMARY KEY,
    label      TEXT,
    asset      TEXT,
    price      REAL,
    change_5d  REAL,
    change_7d  REAL,
    change_20d REAL,
    fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
);

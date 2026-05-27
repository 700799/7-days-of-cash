-- Best7DaysMula screener storage (Postgres / Neon).
-- Source of truth for the `--to-postgres` writer. Safe to run repeatedly:
-- the writer executes this on every run to self-bootstrap a fresh database.

CREATE TABLE IF NOT EXISTS screener_runs (
    id             BIGSERIAL PRIMARY KEY,
    run_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    regime         JSONB       NOT NULL DEFAULT '{}'::jsonb,
    benchmarks     JSONB       NOT NULL DEFAULT '{}'::jsonb,
    config         JSONB       NOT NULL DEFAULT '{}'::jsonb,
    universe_size  INTEGER     NOT NULL DEFAULT 0,
    result_count   INTEGER     NOT NULL DEFAULT 0,
    elapsed_sec    REAL        NOT NULL DEFAULT 0,
    agent_names    TEXT[]      NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS screener_results (
    id                BIGSERIAL PRIMARY KEY,
    run_id            BIGINT  NOT NULL REFERENCES screener_runs(id) ON DELETE CASCADE,
    rank              INTEGER NOT NULL,
    ticker            TEXT    NOT NULL,
    price             NUMERIC,
    change_5d         NUMERIC,
    change_7d         NUMERIC,
    change_20d        NUMERIC,
    avg_vol_20d       BIGINT,
    rel_vol           NUMERIC,
    vol_trend_5d      NUMERIC,
    vol_trend_7d      NUMERIC,
    dollar_vol_20d    BIGINT,
    ma_20             NUMERIC,
    ma_50             NUMERIC,
    ma_200            NUMERIC,
    pct_from_ma20     NUMERIC,
    pct_from_ma50     NUMERIC,
    pct_from_52w_high NUMERIC,
    rsi_14            NUMERIC,
    atr_14            NUMERIC,
    atr_pct           NUMERIC,
    macd_hist         NUMERIC,
    avg_range_pct     NUMERIC,
    gap_pct           NUMERIC,
    composite_score   NUMERIC,
    best_strategy     TEXT,
    top_reasons       TEXT,
    flags             TEXT,
    -- Per-agent score_*/tier_* values live here so adding or removing a
    -- strategy agent never requires a schema migration.
    agent_scores      JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_screener_results_run_rank ON screener_results (run_id, rank);
CREATE INDEX IF NOT EXISTS idx_screener_results_ticker   ON screener_results (ticker);
CREATE INDEX IF NOT EXISTS idx_screener_runs_run_at      ON screener_runs (run_at DESC);

"""DuckDB schema initialization + user upsert behavior."""
from __future__ import annotations

from api.auth import upsert_user
from api.db import get_conn, init_schema


def test_schema_creates_idempotently(tmp_db_path):
    init_schema()
    init_schema()  # second call should be a no-op
    with get_conn() as c:
        tables = {row[0] for row in c.execute("SHOW TABLES").fetchall()}
    assert {"users", "sessions", "watchlists", "ohlcv_cache", "news_cache"} <= tables


def test_user_upsert_dedupes(tmp_db_path):
    upsert_user("g-1", "alice@example.com", "Alice", None)
    upsert_user("g-1", "alice@example.com", "Alice Renamed", "https://pic")
    upsert_user("g-2", "bob@example.com", "Bob", None)

    with get_conn() as c:
        rows = c.execute("SELECT id, name, picture FROM users ORDER BY id").fetchall()

    assert len(rows) == 2
    by_id = {r[0]: r for r in rows}
    assert by_id["g-1"][1] == "Alice Renamed"
    assert by_id["g-1"][2] == "https://pic"
    assert by_id["g-2"][1] == "Bob"

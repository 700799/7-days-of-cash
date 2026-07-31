// Route-level integration tests: the real Worker bundle running in Miniflare
// with a real (in-memory) D1 database seeded from migrations/0001_init.sql.
// No external network — Yahoo-dependent paths are exercised via seeded rows.

import { execSync } from "node:child_process";
import { mkdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { Miniflare } from "miniflare";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const ORIGIN = "http://localhost";

let mf: Miniflare;

type D1Like = {
  prepare(sql: string): {
    bind(...args: unknown[]): { run(): Promise<unknown>; first<T>(): Promise<T | null> };
    run(): Promise<unknown>;
    first<T>(): Promise<T | null>;
  };
};

async function db(): Promise<D1Like> {
  return (await mf.getD1Database("DB")) as unknown as D1Like;
}

async function exec(sql: string, ...args: unknown[]): Promise<void> {
  const d = await db();
  await d.prepare(sql).bind(...args).run();
}

async function seedSession(userId = "u1", token = "a".repeat(64)): Promise<string> {
  await exec(
    "INSERT OR IGNORE INTO users (id, email, name, picture) VALUES (?, ?, ?, ?)",
    userId, `${userId}@example.com`, "Test User", null,
  );
  await exec(
    "INSERT OR REPLACE INTO sessions (token, user_id, expires_at) VALUES (?, ?, datetime('now', '+30 days'))",
    token, userId,
  );
  return token;
}

function authHeaders(token: string, extra: Record<string, string> = {}): Record<string, string> {
  return { Cookie: `b7dm_session=${token}`, Origin: ORIGIN, ...extra };
}

const FAKE_RESULTS = Array.from({ length: 15 }, (_, i) => ({
  ticker: `TK${i}`,
  price: 100 + i,
  ret_7d: 10 + i,
  change_7d: 10 + i,
  score: 90 - i,
  composite_score: 90 - i,
  best_strategy: "momentum",
  vs_voo: 2.5,
}));

async function seedScreenerResult(): Promise<void> {
  await exec(
    "INSERT INTO screener_results (ran_at, payload) VALUES (datetime('now'), ?)",
    JSON.stringify({
      ran_at: new Date().toISOString(),
      results_count: FAKE_RESULTS.length,
      results: FAKE_RESULTS,
      regime: { trend: "bullish", risk: "on", leadership: "growth" },
      benchmarks: [],
      error: null,
    }),
  );
}

beforeAll(async () => {
  // Bundle the Worker with esbuild (same module graph wrangler would deploy).
  // The bundle must live inside the worker directory — workerd refuses script
  // paths that escape its starting directory.
  const outDir = join(ROOT, "test", ".build");
  mkdirSync(outDir, { recursive: true });
  const outFile = join(outDir, "index.mjs");
  execSync(
    `npx esbuild src/index.ts --bundle --format=esm --platform=neutral ` +
      `--conditions=workerd,worker,browser --external:cloudflare:* --outfile=${outFile}`,
    { cwd: ROOT, stdio: "pipe" },
  );

  mf = new Miniflare({
    modules: true,
    scriptPath: outFile,
    d1Databases: ["DB"],
    bindings: { APP_ORIGIN: ORIGIN },
    compatibilityDate: "2025-06-01",
  });

  // Apply the migration. Strip -- comments, then run one statement at a time.
  const migration = readFileSync(join(ROOT, "migrations", "0001_init.sql"), "utf8")
    .split("\n")
    .filter((line) => !line.trim().startsWith("--"))
    .join("\n");
  const d = (await mf.getD1Database("DB")) as unknown as { exec(sql: string): Promise<unknown> };
  for (const stmt of migration.split(";")) {
    const sql = stmt.trim();
    if (sql) await d.exec(sql.replace(/\n/g, " "));
  }
}, 60_000);

afterAll(async () => {
  await mf?.dispose();
});

const get = (path: string, headers: Record<string, string> = {}) =>
  mf.dispatchFetch(`${ORIGIN}${path}`, { headers });
const send = (
  method: string,
  path: string,
  body: unknown,
  headers: Record<string, string> = {},
) =>
  mf.dispatchFetch(`${ORIGIN}${path}`, {
    method,
    headers: { "Content-Type": "application/json", Origin: ORIGIN, ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

describe("health + status", () => {
  it("GET /api/health → ok", async () => {
    const res = await get("/api/health");
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ status: "ok" });
  });

  it("GET /api/status → refresh_state shape", async () => {
    const res = await get("/api/status");
    expect(res.status).toBe(200);
    const body = (await res.json()) as Record<string, unknown>;
    expect(body).toHaveProperty("cursor");
    expect(body).toHaveProperty("universe_size");
    expect(body).toHaveProperty("fresh_tickers");
  });

  it("unknown API path → JSON 404", async () => {
    const res = await get("/api/nope");
    expect(res.status).toBe(404);
    expect(((await res.json()) as { detail: string }).detail).toBe("Not found");
  });
});

describe("auth + sessions", () => {
  it("GET /api/auth/me without cookie → 401", async () => {
    const res = await get("/api/auth/me");
    expect(res.status).toBe(401);
  });

  it("GET /api/auth/me with bad token → 401", async () => {
    const res = await get("/api/auth/me", { Cookie: "b7dm_session=deadbeef" });
    expect(res.status).toBe(401);
  });

  it("GET /api/auth/me with seeded session → user JSON", async () => {
    const token = await seedSession("me1", "b".repeat(64));
    const res = await get("/api/auth/me", { Cookie: `b7dm_session=${token}` });
    expect(res.status).toBe(200);
    const user = (await res.json()) as { id: string; email: string };
    expect(user.id).toBe("me1");
    expect(user.email).toBe("me1@example.com");
  });

  it("expired session → 401", async () => {
    const token = "c".repeat(64);
    await seedSession("me2", token);
    await exec("UPDATE sessions SET expires_at = datetime('now', '-1 day') WHERE token = ?", token);
    const res = await get("/api/auth/me", { Cookie: `b7dm_session=${token}` });
    expect(res.status).toBe(401);
  });

  it("POST /api/auth/logout clears the session row", async () => {
    const token = await seedSession("me3", "d".repeat(64));
    const res = await send("POST", "/api/auth/logout", undefined, {
      Cookie: `b7dm_session=${token}`,
    });
    expect(res.status).toBe(200);
    const d = await db();
    const row = await d.prepare("SELECT 1 AS x FROM sessions WHERE token = ?").bind(token).first();
    expect(row).toBeNull();
  });
});

describe("tickers", () => {
  it("GET /api/tickers/defaults → 16 symbols", async () => {
    const res = await get("/api/tickers/defaults");
    const list = (await res.json()) as string[];
    expect(list).toHaveLength(16);
    expect(list).toContain("NVDA");
  });

  it("GET /api/tickers unauthenticated → []", async () => {
    const res = await get("/api/tickers");
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual([]);
  });

  it("POST /api/tickers unauthenticated → 401", async () => {
    const res = await send("POST", "/api/tickers", { symbol: "AAPL" });
    expect(res.status).toBe(401);
  });

  it("POST with foreign Origin → 403 (CSRF)", async () => {
    const token = await seedSession("t1", "e".repeat(64));
    const res = await send(
      "POST",
      "/api/tickers",
      { symbol: "AAPL" },
      { ...authHeaders(token), Origin: "https://evil.example" },
    );
    expect(res.status).toBe(403);
  });

  it("POST invalid symbol format → 422", async () => {
    const token = await seedSession("t2", "f".repeat(64));
    const res = await send("POST", "/api/tickers", { symbol: "not a symbol!" }, authHeaders(token));
    expect(res.status).toBe(422);
  });

  it("POST valid (pre-validated) symbol → 201; duplicate → 409; then DELETE → 204", async () => {
    const token = await seedSession("t3", "1".repeat(64));
    await exec(
      "INSERT OR REPLACE INTO symbol_validation_cache (symbol, valid, fetched_at) VALUES ('MSFT', 1, datetime('now'))",
    );

    const created = await send("POST", "/api/tickers", { symbol: "MSFT" }, authHeaders(token));
    expect(created.status).toBe(201);
    expect(((await created.json()) as { symbol: string }).symbol).toBe("MSFT");

    const dup = await send("POST", "/api/tickers", { symbol: "MSFT" }, authHeaders(token));
    expect(dup.status).toBe(409);

    const list = await get("/api/tickers", { Cookie: `b7dm_session=${token}` });
    expect(((await list.json()) as unknown[]).length).toBe(1);

    const del = await send("DELETE", "/api/tickers/MSFT", undefined, authHeaders(token));
    expect(del.status).toBe(204);
  });

  it("known-invalid cached symbol → 422 without network", async () => {
    const token = await seedSession("t4", "2".repeat(64));
    await exec(
      "INSERT OR REPLACE INTO symbol_validation_cache (symbol, valid, fetched_at) VALUES ('ZZZZZ', 0, datetime('now'))",
    );
    const res = await send("POST", "/api/tickers", { symbol: "ZZZZZ" }, authHeaders(token));
    expect(res.status).toBe(422);
  });
});

describe("screener (seeded cache)", () => {
  it("cached → 404 before any results", async () => {
    const res = await get("/api/screener/cached");
    expect(res.status).toBe(404);
  });

  it("cached → 200 after seeding", async () => {
    await seedScreenerResult();
    const res = await get("/api/screener/cached");
    expect(res.status).toBe(200);
    const body = (await res.json()) as { results: unknown[]; regime: { trend: string } };
    expect(body.results).toHaveLength(15);
    expect(body.regime.trend).toBe("bullish");
  });

  it("top: n validation + slice", async () => {
    expect((await get("/api/screener/top?n=0")).status).toBe(400);
    expect((await get("/api/screener/top?n=101")).status).toBe(400);
    const res = await get("/api/screener/top?n=5");
    const list = (await res.json()) as { ticker: string }[];
    expect(list).toHaveLength(5);
    expect(list[0].ticker).toBe("TK0");
  });

  it("share/:id → public payload; missing id → 404", async () => {
    const d = await db();
    const row = await d
      .prepare("SELECT id FROM screener_results ORDER BY id DESC LIMIT 1")
      .bind()
      .first<{ id: number }>();
    const res = await get(`/api/screener/share/${row!.id}`);
    expect(res.status).toBe(200);
    const body = (await res.json()) as { top_picks: unknown[] };
    expect(body.top_picks).toHaveLength(10);

    expect((await get("/api/screener/share/999999")).status).toBe(404);
  });

  it("history → entries with top-5 tickers", async () => {
    const res = await get("/api/screener/history?days=7");
    const list = (await res.json()) as { top_5_tickers: string[] }[];
    expect(list.length).toBeGreaterThanOrEqual(1);
    expect(list[0].top_5_tickers).toHaveLength(5);
  });

  it("export → CSV with attachment headers", async () => {
    const res = await get("/api/screener/export");
    expect(res.status).toBe(200);
    expect(res.headers.get("content-type")).toContain("text/csv");
    expect(res.headers.get("content-disposition")).toContain("attachment");
    const text = await res.text();
    expect(text.split("\n")[0]).toContain("ticker");
    expect(text).toContain("TK0");
  });

  it("run: >40 tickers → 413, empty → 422", async () => {
    const many = Array.from({ length: 41 }, (_, i) => `T${i}`);
    expect((await send("POST", "/api/screener/run", { tickers: many })).status).toBe(413);
    expect((await send("POST", "/api/screener/run", {})).status).toBe(422);
  });
});

describe("alerts", () => {
  it("requires auth", async () => {
    expect((await get("/api/alerts")).status).toBe(401);
  });

  it("create → 201, duplicate → 409, list, delete → 204", async () => {
    const token = await seedSession("a1", "3".repeat(64));
    const created = await send(
      "POST",
      "/api/alerts",
      { symbol: "NVDA", condition: "above", target: 500 },
      authHeaders(token),
    );
    expect(created.status).toBe(201);
    const alert = (await created.json()) as { id: number; triggered: boolean };
    expect(alert.triggered).toBe(false);

    const dup = await send(
      "POST",
      "/api/alerts",
      { symbol: "NVDA", condition: "above", target: 500 },
      authHeaders(token),
    );
    expect(dup.status).toBe(409);

    const list = await get("/api/alerts", { Cookie: `b7dm_session=${token}` });
    expect(((await list.json()) as unknown[]).length).toBe(1);

    const del = await send("DELETE", `/api/alerts/${alert.id}`, undefined, authHeaders(token));
    expect(del.status).toBe(204);
  });

  it("11th active alert → 429", async () => {
    const token = await seedSession("a2", "4".repeat(64));
    for (let i = 0; i < 10; i++) {
      const res = await send(
        "POST",
        "/api/alerts",
        { symbol: "AAPL", condition: "above", target: 100 + i },
        authHeaders(token),
      );
      expect(res.status).toBe(201);
    }
    const over = await send(
      "POST",
      "/api/alerts",
      { symbol: "AAPL", condition: "above", target: 999 },
      authHeaders(token),
    );
    expect(over.status).toBe(429);
  });

  it("invalid condition → 422", async () => {
    const token = await seedSession("a3", "5".repeat(64));
    const res = await send(
      "POST",
      "/api/alerts",
      { symbol: "AAPL", condition: "sideways", target: 100 },
      authHeaders(token),
    );
    expect(res.status).toBe(422);
  });
});

describe("preferences", () => {
  it("GET defaults + PATCH round-trip", async () => {
    const token = await seedSession("p1", "6".repeat(64));

    const initial = await get("/api/preferences", { Cookie: `b7dm_session=${token}` });
    expect(initial.status).toBe(200);
    expect(((await initial.json()) as { digest_frequency: string }).digest_frequency).toBe("none");

    const patched = await send(
      "PATCH",
      "/api/preferences",
      { digest_frequency: "daily", digest_email: "p1@example.com" },
      authHeaders(token),
    );
    expect(patched.status).toBe(200);
    const body = (await patched.json()) as { digest_frequency: string; digest_email: string };
    expect(body.digest_frequency).toBe("daily");
    expect(body.digest_email).toBe("p1@example.com");
  });

  it("invalid frequency → 422", async () => {
    const token = await seedSession("p2", "7".repeat(64));
    const res = await send(
      "PATCH",
      "/api/preferences",
      { digest_frequency: "hourly" },
      authHeaders(token),
    );
    expect(res.status).toBe(422);
  });
});

describe("hardening", () => {
  it("oversized body → 413", async () => {
    const big = JSON.stringify({ symbol: "AAPL", note: "x".repeat(100 * 1024) });
    const res = await mf.dispatchFetch(`${ORIGIN}/api/tickers`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Origin: ORIGIN },
      body: big,
    });
    expect(res.status).toBe(413);
  });

  it("API responses carry security headers", async () => {
    const res = await get("/api/health");
    expect(res.headers.get("x-content-type-options")).toBe("nosniff");
    expect(res.headers.get("x-robots-tag")).toContain("noindex");
    expect(res.headers.get("x-frame-options")).toBe("DENY");
  });
});

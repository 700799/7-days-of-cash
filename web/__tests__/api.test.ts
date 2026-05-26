import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  addTicker,
  deleteTicker,
  getCachedScreener,
  getMe,
  listTickers,
} from "@/lib/api";

function mockFetch(impl: (url: string, init?: RequestInit) => Response) {
  // @ts-expect-error - global fetch override
  global.fetch = vi.fn((url: string, init?: RequestInit) =>
    Promise.resolve(impl(url, init)),
  );
}

describe("api fetch wrapper", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("sends credentials: include and parses JSON on success", async () => {
    mockFetch(
      () =>
        new Response(JSON.stringify([{ symbol: "AAPL", added_at: "now" }]), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
    );
    const result = await listTickers();
    expect(result).toEqual([{ symbol: "AAPL", added_at: "now" }]);
    const call = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock
      .calls[0];
    const init = call[1] as RequestInit;
    expect(init.credentials).toBe("include");
  });

  it("returns null from getMe on 401", async () => {
    mockFetch(
      () =>
        new Response(JSON.stringify({ detail: "unauthenticated" }), {
          status: 401,
          headers: { "Content-Type": "application/json" },
        }),
    );
    const me = await getMe();
    expect(me).toBeNull();
  });

  it("throws ApiError with parsed body on 409", async () => {
    mockFetch(
      () =>
        new Response(JSON.stringify({ detail: "already exists" }), {
          status: 409,
          headers: { "Content-Type": "application/json" },
        }),
    );
    await expect(addTicker("AAPL")).rejects.toMatchObject({
      name: "ApiError",
      status: 409,
    });
    try {
      await addTicker("AAPL");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).message).toBe("already exists");
    }
  });

  it("handles 204 no-content responses", async () => {
    mockFetch(() => new Response(null, { status: 204 }));
    await expect(deleteTicker("AAPL")).resolves.toBeUndefined();
  });

  it("getCachedScreener fetches GET /api/screener/cached", async () => {
    const fakePayload = {
      regime: {},
      benchmarks: [],
      results: [{ ticker: "NVDA", ret_7d: 8.5, score: 87.3 }],
      ran_at: "2024-01-15T12:00:00Z",
    };
    mockFetch(
      () =>
        new Response(JSON.stringify(fakePayload), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
    );
    const result = await getCachedScreener();
    expect(result.results).toHaveLength(1);
    expect(result.results[0].ticker).toBe("NVDA");
    const call = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock
      .calls[0];
    expect(call[0]).toContain("/api/screener/cached");
    expect(call[1]?.method).toBeUndefined(); // GET = no method override
  });

  it("sets JSON content-type when body is provided", async () => {
    mockFetch(
      () =>
        new Response(
          JSON.stringify({ symbol: "AAPL", note: null, added_at: "now" }),
          { status: 201, headers: { "Content-Type": "application/json" } },
        ),
    );
    await addTicker("aapl");
    const call = (global.fetch as unknown as ReturnType<typeof vi.fn>).mock
      .calls[0];
    const init = call[1] as RequestInit;
    const headers = new Headers(init.headers);
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(JSON.parse(init.body as string)).toEqual({ symbol: "AAPL" });
  });
});

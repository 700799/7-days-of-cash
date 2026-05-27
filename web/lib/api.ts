// Typed API client for the Best7DaysMula FastAPI backend.
// All requests send cookies (`credentials: "include"`) for auth session.

const ENV_API_URL =
  typeof process !== "undefined" ? process.env.NEXT_PUBLIC_API_URL : undefined;

let warnedMissingApiUrl = false;
function resolveApiUrl(): string {
  if (ENV_API_URL) return ENV_API_URL;
  // In dev, fall back to localhost so the UI keeps working without an env file.
  if (
    typeof process !== "undefined" &&
    process.env.NODE_ENV === "development"
  ) {
    return "http://localhost:8000";
  }
  // In prod, fail loud rather than silently routing to localhost.
  if (typeof window !== "undefined" && !warnedMissingApiUrl) {
    warnedMissingApiUrl = true;
    // eslint-disable-next-line no-console
    console.error(
      "NEXT_PUBLIC_API_URL is not set; API calls will fail.",
    );
  }
  return "";
}

export const API_URL = resolveApiUrl();

export type User = {
  id: string;
  email: string;
  name: string;
  picture?: string;
};

export type Ticker = {
  symbol: string;
  note?: string | null;
  added_at: string;
};

export type NewsItem = {
  title: string;
  publisher: string;
  link: string;
  published_at: string;
  thumbnail?: string | null;
};

export type ScreenerResultRow = {
  ticker: string;
  price?: number;
  ret_7d?: number;
  score?: number;
  momentum?: number;
  breakout?: number;
  volume?: number;
  rs?: number;
  mean_reversion?: number;
  best_strategy?: string;
  vs_voo?: number;
  [key: string]: unknown;
};

export type Regime = {
  trend?: string;
  risk?: string;
  leadership?: string;
  [key: string]: unknown;
};

export type Benchmark = {
  symbol: string;
  ret_7d: number;
};

export type ScreenerPayload = {
  regime: Regime;
  benchmarks: Benchmark[];
  results: ScreenerResultRow[];
  ran_at: string;
};

export type ScreenerRunBody = {
  tickers?: string[];
  filters?: Record<string, unknown>;
  agents?: string[];
};

export type MoverHeadline = {
  title: string;
  link: string;
  publisher: string;
  published_at: string;
};

export type Mover = {
  symbol: string;
  price?: number | null;
  change_7d?: number | null;
  change_1d?: number | null;
  summary?: string | null;
  headlines: MoverHeadline[];
};

export type DigestFrequency = "none" | "daily" | "weekly";

export type Preferences = {
  digest_frequency: DigestFrequency;
  digest_email?: string | null;
  last_sent_at?: string | null;
};

export type PreferencesUpdate = {
  digest_frequency: DigestFrequency;
  digest_email?: string;
};

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(message: string, status: number, body: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const url = `${API_URL}${path}`;
  const headers = new Headers(init.headers || {});
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  headers.set("Accept", "application/json");

  const res = await fetch(url, {
    ...init,
    headers,
    credentials: "include",
  });

  if (res.status === 204) {
    return undefined as unknown as T;
  }

  const text = await res.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = text;
    }
  }

  if (!res.ok) {
    const msg =
      (body && typeof body === "object" && "detail" in (body as object)
        ? String((body as { detail: unknown }).detail)
        : res.statusText) || `HTTP ${res.status}`;
    throw new ApiError(msg, res.status, body);
  }

  return body as T;
}

// ----- auth -----
export const loginUrl = (): string =>
  `${API_URL}/api/auth/login/google`;

export async function getMe(): Promise<User | null> {
  try {
    return await request<User>("/api/auth/me");
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) return null;
    throw err;
  }
}

export async function logout(): Promise<void> {
  await request<void>("/api/auth/logout", { method: "POST" });
}

// ----- tickers -----
export function listTickers(): Promise<Ticker[]> {
  return request<Ticker[]>("/api/tickers");
}

export function addTicker(symbol: string, note?: string): Promise<Ticker> {
  return request<Ticker>("/api/tickers", {
    method: "POST",
    body: JSON.stringify({ symbol: symbol.toUpperCase(), note }),
  });
}

export function updateTicker(symbol: string, note: string): Promise<Ticker> {
  return request<Ticker>(`/api/tickers/${encodeURIComponent(symbol)}`, {
    method: "PATCH",
    body: JSON.stringify({ note }),
  });
}

export function deleteTicker(symbol: string): Promise<void> {
  return request<void>(`/api/tickers/${encodeURIComponent(symbol)}`, {
    method: "DELETE",
  });
}

// ----- news -----
export function getTickerNews(symbol: string): Promise<NewsItem[]> {
  return request<NewsItem[]>(
    `/api/news/ticker/${encodeURIComponent(symbol)}`,
  );
}

export function getMarketNews(): Promise<NewsItem[]> {
  return request<NewsItem[]>("/api/news/market");
}

// ----- screener -----
export function runScreener(
  body: ScreenerRunBody = {},
): Promise<ScreenerPayload> {
  return request<ScreenerPayload>("/api/screener/run", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getCachedScreener(): Promise<ScreenerPayload> {
  return request<ScreenerPayload>("/api/screener/cached");
}

// ----- defaults -----
export function getTickerDefaults(): Promise<string[]> {
  return request<string[]>("/api/tickers/defaults");
}

// ----- movers -----
export function getMovers(symbols: string[]): Promise<Mover[]> {
  const qs = symbols.length
    ? `?symbols=${encodeURIComponent(symbols.join(","))}`
    : "";
  return request<Mover[]>(`/api/movers${qs}`);
}

export function getMover(symbol: string): Promise<Mover> {
  return request<Mover>(`/api/movers/${encodeURIComponent(symbol)}`);
}

// ----- trending news -----
export function getTrendingNews(): Promise<NewsItem[]> {
  return request<NewsItem[]>("/api/news/trending");
}

// ----- preferences -----
export function getPreferences(): Promise<Preferences> {
  return request<Preferences>("/api/preferences");
}

export function updatePreferences(
  body: PreferencesUpdate,
): Promise<Preferences> {
  return request<Preferences>("/api/preferences", {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

// ----- billing -----
export type BillingStatus = {
  plan: "free" | "pro";
  status: string;
  period_end: string | null;
  publishable_key?: string;
};

export type PriceAlert = {
  id: number;
  symbol: string;
  condition: "above" | "below";
  target: number;
  triggered: boolean;
  created_at: string | null;
};

export function getBillingStatus(): Promise<BillingStatus> {
  return request<BillingStatus>("/api/billing/status");
}

export function createCheckoutSession(): Promise<{ url: string }> {
  return request<{ url: string }>("/api/billing/checkout", { method: "POST" });
}

export function getBillingPortalUrl(): Promise<{ url: string }> {
  return request<{ url: string }>("/api/billing/portal");
}

// ----- alerts -----
export function getAlerts(): Promise<PriceAlert[]> {
  return request<PriceAlert[]>("/api/alerts");
}

export function createAlert(
  symbol: string,
  condition: "above" | "below",
  target: number,
): Promise<PriceAlert> {
  return request<PriceAlert>("/api/alerts", {
    method: "POST",
    body: JSON.stringify({ symbol, condition, target }),
  });
}

export function deleteAlert(id: number): Promise<void> {
  return request<void>(`/api/alerts/${id}`, { method: "DELETE" });
}

// ----- screener extras -----
export function getScreenerHistory(days = 7): Promise<
  { id: number; ran_at: string; results_count: number; top_5_tickers: string[]; error: string | null }[]
> {
  return request(`/api/screener/history?days=${days}`);
}

export function getSharedScreenerResult(id: number): Promise<{
  id: number;
  ran_at: string;
  results_count: number;
  top_picks: ScreenerResultRow[];
}> {
  return request(`/api/screener/share/${id}`);
}

export const screenerExportUrl = (): string =>
  `${API_URL}/api/screener/export`;

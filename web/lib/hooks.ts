"use client";

import useSWR from "swr";
import {
  getCachedScreener,
  getAlerts,
  getBillingStatus,
  getMarketNews,
  getMe,
  getMover,
  getMovers,
  getPreferences,
  getTickerDefaults,
  getTickerNews,
  getTrendingNews,
  listTickers,
  type BillingStatus,
  type Mover,
  type NewsItem,
  type Preferences,
  type PriceAlert,
  type ScreenerPayload,
  type Ticker,
  type User,
} from "./api";

// Shared SWR defaults applied to every hook in this file.
// - revalidateOnFocus: false keeps the green-on-black terminal feel calm.
// - errorRetryInterval: 30s avoids hammering the backend during outages.
// - dedupingInterval: 60s prevents duplicate requests across components.
const BASE_SWR = {
  revalidateOnFocus: false as const,
  errorRetryInterval: 30_000,
  dedupingInterval: 60_000,
};

export function useMe() {
  const { data, error, isLoading, mutate } = useSWR<User | null>(
    "auth:me",
    () => getMe(),
    { ...BASE_SWR, shouldRetryOnError: false },
  );
  return { user: data ?? null, error, loading: isLoading, mutate };
}

export function useTickers(enabled: boolean = true) {
  const { data, error, isLoading, mutate } = useSWR<Ticker[]>(
    enabled ? "tickers:list" : null,
    () => listTickers(),
    { ...BASE_SWR, shouldRetryOnError: false },
  );
  return { tickers: data ?? [], error, loading: isLoading, mutate };
}

export function useMarketNews() {
  const { data, error, isLoading } = useSWR<NewsItem[]>(
    "news:market",
    () => getMarketNews(),
    { ...BASE_SWR },
  );
  return { news: data ?? [], error, loading: isLoading };
}

export function useTickerNews(symbol: string | null) {
  const { data, error, isLoading } = useSWR<NewsItem[]>(
    symbol ? ["news:ticker", symbol] : null,
    () => getTickerNews(symbol as string),
    { ...BASE_SWR },
  );
  return { news: data ?? [], error, loading: isLoading };
}

export function useDefaults() {
  const { data, error, isLoading } = useSWR<string[]>(
    "tickers:defaults",
    () => getTickerDefaults(),
    { ...BASE_SWR, shouldRetryOnError: false },
  );
  return { defaults: data ?? [], error, loading: isLoading };
}

export function useMovers(symbols: string[]) {
  // Stable cache key — sort symbols so order changes don't refetch.
  const sorted = [...symbols].map((s) => s.toUpperCase()).sort();
  const key = sorted.length ? ["movers", sorted.join(",")] : null;
  const { data, error, isLoading, mutate } = useSWR<Mover[]>(
    key,
    () => getMovers(sorted),
    {
      ...BASE_SWR,
      refreshInterval: 5 * 60 * 1000, // 5 minutes
    },
  );
  return { movers: data ?? [], error, loading: isLoading, mutate };
}

export function useMover(symbol: string | null) {
  const { data, error, isLoading } = useSWR<Mover>(
    symbol ? ["mover", symbol] : null,
    () => getMover(symbol as string),
    { ...BASE_SWR },
  );
  return { mover: data ?? null, error, loading: isLoading };
}

export function useTrendingNews() {
  const { data, error, isLoading } = useSWR<NewsItem[]>(
    "news:trending",
    () => getTrendingNews(),
    {
      ...BASE_SWR,
      refreshInterval: 30 * 60 * 1000, // 30 minutes
    },
  );
  return { news: data ?? [], error, loading: isLoading };
}

export function useCachedScreener() {
  const { data, error, isLoading } = useSWR<ScreenerPayload>(
    "screener:cached",
    () => getCachedScreener(),
    {
      ...BASE_SWR,
      // Refresh every 4 hours to stay in sync with cron
      refreshInterval: 4 * 60 * 60 * 1000,
      // Don't treat 404 as a retry-able error — it just means no cache yet
      onErrorRetry: (err, _key, _config, revalidate, { retryCount }) => {
        if (err?.status === 404) return;
        if (retryCount >= 3) return;
        setTimeout(() => revalidate({ retryCount }), 30_000);
      },
    },
  );
  return { payload: data ?? null, error, loading: isLoading };
}

export function usePreferences(enabled: boolean = true) {
  const { data, error, isLoading, mutate } = useSWR<Preferences>(
    enabled ? "preferences" : null,
    () => getPreferences(),
    { ...BASE_SWR, shouldRetryOnError: false },
  );
  return { preferences: data ?? null, error, loading: isLoading, mutate };
}

export function useBillingStatus(enabled: boolean = true) {
  const { data, error, isLoading, mutate } = useSWR<BillingStatus>(
    enabled ? "billing:status" : null,
    () => getBillingStatus(),
    {
      ...BASE_SWR,
      // Billing status doesn't change often; check once per hour
      refreshInterval: 60 * 60 * 1000,
      shouldRetryOnError: false,
      onErrorRetry: (err, _key, _config, revalidate, { retryCount }) => {
        if (err?.status === 401) return;
        if (retryCount >= 2) return;
        setTimeout(() => revalidate({ retryCount }), 30_000);
      },
    },
  );
  const plan = data?.plan ?? "free";
  const isPro = plan === "pro";
  return { status: data ?? null, plan, isPro, error, loading: isLoading, mutate };
}

export function useAlerts(enabled: boolean = true) {
  const { data, error, isLoading, mutate } = useSWR<PriceAlert[]>(
    enabled ? "alerts:list" : null,
    () => getAlerts(),
    { ...BASE_SWR, shouldRetryOnError: false },
  );
  return { alerts: data ?? [], error, loading: isLoading, mutate };
}

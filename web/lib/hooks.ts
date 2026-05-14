"use client";

import useSWR from "swr";
import {
  getMarketNews,
  getMe,
  getMover,
  getMovers,
  getPreferences,
  getTickerDefaults,
  getTickerNews,
  getTrendingNews,
  listTickers,
  type Mover,
  type NewsItem,
  type Preferences,
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

export function usePreferences(enabled: boolean = true) {
  const { data, error, isLoading, mutate } = useSWR<Preferences>(
    enabled ? "preferences" : null,
    () => getPreferences(),
    { ...BASE_SWR, shouldRetryOnError: false },
  );
  return { preferences: data ?? null, error, loading: isLoading, mutate };
}

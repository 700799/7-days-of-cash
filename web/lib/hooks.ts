"use client";

import useSWR from "swr";
import {
  getMarketNews,
  getMe,
  getTickerNews,
  listTickers,
  type NewsItem,
  type Ticker,
  type User,
} from "./api";

export function useMe() {
  const { data, error, isLoading, mutate } = useSWR<User | null>(
    "auth:me",
    () => getMe(),
    { shouldRetryOnError: false, revalidateOnFocus: false },
  );
  return { user: data ?? null, error, loading: isLoading, mutate };
}

export function useTickers(enabled: boolean = true) {
  const { data, error, isLoading, mutate } = useSWR<Ticker[]>(
    enabled ? "tickers:list" : null,
    () => listTickers(),
    { shouldRetryOnError: false },
  );
  return { tickers: data ?? [], error, loading: isLoading, mutate };
}

export function useMarketNews() {
  const { data, error, isLoading } = useSWR<NewsItem[]>(
    "news:market",
    () => getMarketNews(),
    { revalidateOnFocus: false },
  );
  return { news: data ?? [], error, loading: isLoading };
}

export function useTickerNews(symbol: string | null) {
  const { data, error, isLoading } = useSWR<NewsItem[]>(
    symbol ? ["news:ticker", symbol] : null,
    () => getTickerNews(symbol as string),
    { revalidateOnFocus: false },
  );
  return { news: data ?? [], error, loading: isLoading };
}

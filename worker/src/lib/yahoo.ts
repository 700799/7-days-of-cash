// Yahoo Finance client — replaces yfinance with direct fetch calls.
//
// Endpoints (public, unauthenticated):
//   Chart:  https://query1.finance.yahoo.com/v8/finance/chart/{sym}?range=35d&interval=1d
//   News:   https://query1.finance.yahoo.com/v1/finance/search?q={sym}&newsCount=N
//
// Each chart call is one subrequest; the cron slices the universe to stay
// inside the Workers free-plan budget (50 subrequests/invocation).

import type { Ohlcv } from "../engine/metrics";

const CHART_BASE = "https://query1.finance.yahoo.com/v8/finance/chart";
const SEARCH_BASE = "https://query1.finance.yahoo.com/v1/finance/search";
const UA =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36";

export interface NewsItem {
  title: string;
  publisher: string;
  link: string;
  published_at: string | null;
  thumbnail: string | null;
}

async function fetchJson(url: string, retries = 2): Promise<unknown | null> {
  let delay = 500;
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(url, { headers: { "User-Agent": UA, Accept: "application/json" } });
      if (res.ok) return await res.json();
      // 404 = unknown symbol — don't retry.
      if (res.status === 404) return null;
    } catch {
      /* network error — retry */
    }
    if (attempt < retries) {
      await new Promise((r) => setTimeout(r, delay));
      delay *= 2;
    }
  }
  return null;
}

interface ChartResponse {
  chart?: {
    result?: {
      timestamp?: number[];
      indicators?: {
        quote?: {
          open?: (number | null)[];
          high?: (number | null)[];
          low?: (number | null)[];
          close?: (number | null)[];
          volume?: (number | null)[];
        }[];
        adjclose?: { adjclose?: (number | null)[] }[];
      };
    }[];
  };
}

/**
 * Fetch daily OHLCV for one symbol. Mirrors yfinance auto_adjust=True by
 * scaling OHLC with the adjclose/close ratio when adjclose is present.
 * Returns null when the symbol is unknown or has < 2 bars.
 */
export async function fetchChart(symbol: string, range = "35d"): Promise<Ohlcv | null> {
  const url = `${CHART_BASE}/${encodeURIComponent(symbol)}?range=${range}&interval=1d`;
  const data = (await fetchJson(url)) as ChartResponse | null;
  const result = data?.chart?.result?.[0];
  const quote = result?.indicators?.quote?.[0];
  if (!result?.timestamp || !quote?.close) return null;

  const adj = result.indicators?.adjclose?.[0]?.adjclose;
  const open: number[] = [];
  const high: number[] = [];
  const low: number[] = [];
  const close: number[] = [];
  const volume: number[] = [];

  for (let i = 0; i < result.timestamp.length; i++) {
    const c = quote.close[i];
    const o = quote.open?.[i];
    const h = quote.high?.[i];
    const l = quote.low?.[i];
    const v = quote.volume?.[i];
    if (c == null || o == null || h == null || l == null) continue; // drop NaN rows
    const factor = adj?.[i] != null && c !== 0 ? (adj[i] as number) / c : 1;
    open.push(o * factor);
    high.push(h * factor);
    low.push(l * factor);
    close.push(c * factor);
    volume.push(v ?? 0);
  }
  if (close.length < 2) return null;
  return { open, high, low, close, volume };
}

interface SearchResponse {
  news?: {
    title?: string;
    publisher?: string;
    link?: string;
    providerPublishTime?: number;
    thumbnail?: { resolutions?: { url?: string }[] };
  }[];
}

/** Fetch recent news for a symbol/index query. */
export async function fetchNews(query: string, count = 8): Promise<NewsItem[]> {
  const url = `${SEARCH_BASE}?q=${encodeURIComponent(query)}&newsCount=${count}&quotesCount=0`;
  const data = (await fetchJson(url)) as SearchResponse | null;
  const items = data?.news ?? [];
  const out: NewsItem[] = [];
  for (const item of items) {
    if (!item.title || !item.link) continue;
    out.push({
      title: item.title,
      publisher: item.publisher ?? "",
      link: item.link,
      published_at:
        typeof item.providerPublishTime === "number"
          ? new Date(item.providerPublishTime * 1000).toISOString()
          : null,
      thumbnail: item.thumbnail?.resolutions?.[0]?.url ?? null,
    });
  }
  return out;
}

/** Cheap symbol existence check: does the chart endpoint return any bars? */
export async function symbolExists(symbol: string): Promise<boolean> {
  const bars = await fetchChart(symbol, "5d");
  return bars !== null && bars.close.length > 0;
}

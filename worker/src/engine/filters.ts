// Configurable filters — port of screener/filters.py.

import type { ScoredRecord } from "./orchestrator";

export interface FilterConfig {
  active_filters?: string[];
  min_price?: number;
  min_gain_7d?: number;
  min_avg_volume?: number;
  max_rsi?: number;
  exclude_extreme_volatility?: boolean;
  max_avg_range_pct?: number;
  min_dollar_vol?: number;
  min_pct_52w_high?: number;
  market_cap?: "all" | "small" | "mid" | "large";
  top_n?: number;
}

const DEFAULT_ACTIVE = new Set([
  "min_price",
  "min_gain_7d",
  "min_avg_volume",
  "max_rsi",
  "market_cap",
  "exclude_volatility",
  "min_dollar_vol",
]);

/** Apply AND-combined filters, sort by composite (fallback change_7d), take top_n. */
export function applyFilters(records: ScoredRecord[], config: FilterConfig = {}): ScoredRecord[] {
  if (records.length === 0) return [];

  const active = config.active_filters?.length
    ? new Set(config.active_filters)
    : DEFAULT_ACTIVE;

  const minPrice = config.min_price ?? 2.0;
  const minGain7d = config.min_gain_7d ?? 8.0;
  const minAvgVolume = config.min_avg_volume ?? 500_000;
  const maxRsi = config.max_rsi ?? 80;
  const excludeVol = config.exclude_extreme_volatility ?? true;
  const maxAvgRangePct = config.max_avg_range_pct ?? 50.0;
  const minDollarVol = config.min_dollar_vol ?? 5_000_000;
  const minPct52wHigh = config.min_pct_52w_high ?? -15.0;
  const marketCap = config.market_cap ?? "all";
  const topN = config.top_n ?? 25;

  const kept = records.filter((r) => {
    const rec = r as ScoredRecord & { market_cap_val?: number };
    if (active.has("min_price") && !(r.price >= minPrice)) return false;
    if (active.has("min_gain_7d") && !(r.change_7d >= minGain7d)) return false;
    if (active.has("min_avg_volume") && !(r.avg_vol_20d >= minAvgVolume)) return false;
    if (active.has("max_rsi") && !(r.rsi_14 <= maxRsi)) return false;
    if (active.has("exclude_volatility") && excludeVol && !(r.avg_range_pct <= maxAvgRangePct)) {
      return false;
    }
    if (
      active.has("min_dollar_vol") &&
      r.dollar_vol_20d !== undefined &&
      !(r.dollar_vol_20d >= minDollarVol)
    ) {
      return false;
    }
    if (
      active.has("near_52w_high") &&
      r.pct_from_52w_high !== undefined &&
      !(r.pct_from_52w_high >= minPct52wHigh)
    ) {
      return false;
    }
    if (active.has("market_cap") && marketCap !== "all" && rec.market_cap_val !== undefined) {
      const cap = rec.market_cap_val;
      if (marketCap === "small" && !(cap < 2e9)) return false;
      if (marketCap === "mid" && !(cap >= 2e9 && cap < 10e9)) return false;
      if (marketCap === "large" && !(cap >= 10e9)) return false;
    }
    return true;
  });

  const sortKey = kept.some((r) => r.composite_score !== undefined)
    ? "composite_score"
    : "change_7d";
  kept.sort((a, b) => {
    const av = sortKey === "composite_score" ? a.composite_score : a.change_7d;
    const bv = sortKey === "composite_score" ? b.composite_score : b.change_7d;
    return bv - av;
  });
  return kept.slice(0, topN);
}

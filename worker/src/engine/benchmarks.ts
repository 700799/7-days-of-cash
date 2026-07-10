// Benchmark metadata + market regime — port of screener/benchmarks.py.
// Fetching lives in lib/yahoo.ts; this module holds the meta + regime math.

export interface BenchmarkRow {
  ticker: string;
  label: string;
  asset: string;
  price?: number;
  change_5d?: number;
  change_7d?: number;
  change_20d?: number;
}

export const BENCHMARK_META: readonly { ticker: string; label: string; asset: string }[] = [
  { ticker: "VOO", label: "S&P 500", asset: "equity" },
  { ticker: "QQQ", label: "Nasdaq 100", asset: "equity" },
  { ticker: "VXF", label: "Extended Mkt", asset: "equity" },
  { ticker: "IWM", label: "Russell 2000", asset: "equity" },
  { ticker: "VTIAX", label: "Total Intl", asset: "intl" },
  { ticker: "GLD", label: "Gold", asset: "commodity" },
  { ticker: "TLT", label: "20+y Treasury", asset: "bond" },
];

export interface Regime {
  trend: "bullish" | "bearish" | "mixed";
  risk: "on" | "off" | "neutral";
  leadership: "growth" | "small-cap" | "defensive" | "broad";
}

/** Compute market regime from benchmark 7d changes (matches market_regime). */
export function marketRegime(benchmarks: Record<string, BenchmarkRow>): Regime {
  const c7 = (t: string): number => benchmarks[t]?.change_7d ?? 0.0;
  const voo = c7("VOO");
  const qqq = c7("QQQ");
  const iwm = c7("IWM");
  const tlt = c7("TLT");
  const gld = c7("GLD");

  let trend: Regime["trend"] = "mixed";
  if (voo > 1 && qqq > 1) trend = "bullish";
  else if (voo < -1 && qqq < -1) trend = "bearish";

  let risk: Regime["risk"] = "neutral";
  if (iwm > voo && qqq > voo) risk = "on";
  else if (tlt > voo && gld > voo) risk = "off";

  let leadership: Regime["leadership"] = "broad";
  if (qqq > voo + 1) leadership = "growth";
  else if (iwm > voo + 1) leadership = "small-cap";
  else if (tlt > 0 && voo < 0) leadership = "defensive";

  return { trend, risk, leadership };
}

/** Clamped-lookback percent changes over a close series (matches fetch_benchmarks). */
export function benchmarkChanges(close: number[]): {
  price: number;
  change_5d: number;
  change_7d: number;
  change_20d: number;
} | null {
  const n = close.length;
  if (n < 8) return null;
  const round2 = (v: number): number => Math.round(v * 100) / 100;
  const chg = (lb: number): number => {
    const l = Math.min(lb, n - 1);
    return (close[n - 1] / close[n - 1 - l] - 1) * 100;
  };
  return {
    price: round2(close[n - 1]),
    change_5d: round2(chg(5)),
    change_7d: round2(chg(7)),
    change_20d: round2(chg(20)),
  };
}

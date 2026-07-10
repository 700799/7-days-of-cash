// Per-ticker technical metrics — numerical port of screener/metrics.py.
//
// Parity contract: every formula matches the pandas implementation exactly,
// including EWM adjust=False recurrences (Wilder RSI/ATR, MACD) and
// trading-bar lookbacks clamped to n-1. Verified by test/engine.parity.test.ts
// against fixtures generated from the Python engine.

export interface Ohlcv {
  open: number[];
  high: number[];
  low: number[];
  close: number[];
  volume: number[];
}

export interface Metrics {
  ticker: string;
  price: number;
  change_5d: number;
  change_7d: number;
  change_20d: number;
  avg_vol_20d: number;
  rel_vol: number;
  vol_trend_5d: number;
  vol_trend_7d: number;
  dollar_vol_20d: number;
  ma_20: number;
  ma_50: number;
  ma_200: number;
  pct_from_ma20: number;
  pct_from_ma50: number;
  pct_from_52w_high: number;
  rsi_14: number;
  atr_14: number;
  atr_pct: number;
  macd_hist: number;
  avg_range_pct: number;
  gap_pct: number;
}

const round = (v: number, dp: number): number => {
  const f = 10 ** dp;
  return Math.round(v * f) / f;
};

const mean = (xs: number[]): number =>
  xs.length === 0 ? 0 : xs.reduce((a, b) => a + b, 0) / xs.length;

/** OLS slope over evenly spaced x (matches _linreg_slope). */
export function linregSlope(values: number[]): number {
  const n = values.length;
  if (n < 2) return 0.0;
  const xMean = (n - 1) / 2;
  const yMean = mean(values);
  let num = 0;
  let denom = 0;
  for (let i = 0; i < n; i++) {
    const xc = i - xMean;
    num += xc * (values[i] - yMean);
    denom += xc * xc;
  }
  return denom === 0 ? 0.0 : num / denom;
}

/** pandas EWM(alpha, adjust=False).mean() — returns full series. */
function ewmAlpha(values: number[], alpha: number): number[] {
  const out = new Array<number>(values.length);
  let s = values[0];
  out[0] = s;
  for (let i = 1; i < values.length; i++) {
    s = s + alpha * (values[i] - s);
    out[i] = s;
  }
  return out;
}

/** Wilder RSI via EWM(alpha=1/period, adjust=False), matching _rsi. */
export function rsi(close: number[], period = 14): number {
  const deltas: number[] = [];
  for (let i = 1; i < close.length; i++) deltas.push(close[i] - close[i - 1]);
  if (deltas.length < period) return 50.0;

  const gains = deltas.map((d) => (d > 0 ? d : 0));
  const losses = deltas.map((d) => (d < 0 ? -d : 0));
  const alpha = 1 / period;
  const avgGain = ewmAlpha(gains, alpha)[gains.length - 1];
  const avgLoss = ewmAlpha(losses, alpha)[losses.length - 1];
  if (avgLoss === 0) return 100.0;
  const rs = avgGain / avgLoss;
  return 100 - 100 / (1 + rs);
}

/** ATR via EWM(alpha=1/period, adjust=False) over true range, matching _atr. */
export function atr(high: number[], low: number[], close: number[], period = 14): number {
  const n = close.length;
  if (n < 2) return 0.0;
  // First row has no prev close → TR = high-low (pandas row-max ignores NaN).
  const tr: number[] = [Math.abs(high[0] - low[0])];
  for (let i = 1; i < n; i++) {
    tr.push(
      Math.max(
        Math.abs(high[i] - low[i]),
        Math.abs(high[i] - close[i - 1]),
        Math.abs(low[i] - close[i - 1]),
      ),
    );
  }
  if (tr.length < period) return 0.0; // min_periods gate → NaN in pandas → 0.0
  const series = ewmAlpha(tr, 1 / period);
  const last = series[series.length - 1];
  return Number.isFinite(last) ? last : 0.0;
}

/** MACD histogram (12/26/9 EMA, adjust=False), matching _macd_histogram. */
export function macdHistogram(close: number[], fast = 12, slow = 26, signal = 9): number {
  if (close.length < slow + signal) return 0.0;
  const alphaF = 2 / (fast + 1);
  const alphaS = 2 / (slow + 1);
  const alphaSig = 2 / (signal + 1);
  const emaFast = ewmAlpha(close, alphaF);
  const emaSlow = ewmAlpha(close, alphaS);
  const macdLine = emaFast.map((v, i) => v - emaSlow[i]);
  const signalLine = ewmAlpha(macdLine, alphaSig);
  return macdLine[macdLine.length - 1] - signalLine[signalLine.length - 1];
}

/**
 * Compute the full metric set for one ticker. Returns null when there is not
 * enough history (< 10 bars) or inputs are malformed — same as Python.
 */
export function computeMetrics(ticker: string, bars: Ohlcv): Metrics | null {
  try {
    const { open, high, low, close, volume } = bars;
    const n = close.length;
    if (n < 10) return null;

    const price = close[n - 1];

    const lb7 = Math.min(7, n - 1);
    const lb5 = Math.min(5, n - 1);
    const lb20 = Math.min(20, n - 1);
    const change5 = (close[n - 1] / close[n - 1 - lb5] - 1) * 100;
    const change7 = (close[n - 1] / close[n - 1 - lb7] - 1) * 100;
    const change20 = (close[n - 1] / close[n - 1 - lb20] - 1) * 100;

    const avgVol20 = n >= 20 ? mean(volume.slice(-20)) : mean(volume);
    const todayVol = volume[n - 1];
    const relVol = avgVol20 > 0 ? todayVol / avgVol20 : 0.0;
    const volTrend5 = n >= 5 ? linregSlope(volume.slice(-5)) : 0.0;
    const volTrend7 = n >= 7 ? linregSlope(volume.slice(-7)) : 0.0;
    const dollarVol20 = avgVol20 * price;

    const ma20 = n >= 20 ? mean(close.slice(-20)) : mean(close);
    const ma50 = n >= 50 ? mean(close.slice(-50)) : ma20;
    const ma200 = n >= 200 ? mean(close.slice(-200)) : ma50;
    const pctFromMa20 = ma20 > 0 ? (price / ma20 - 1) * 100 : 0;
    const pctFromMa50 = ma50 > 0 ? (price / ma50 - 1) * 100 : 0;

    const high52 = n >= 60 ? Math.max(...high.slice(-252)) : Math.max(...high);
    const pctFrom52wHigh = high52 > 0 ? (price / high52 - 1) * 100 : 0;

    const rsi14 = rsi(close, 14);
    const atr14 = atr(high, low, close, 14);
    const atrPct = price > 0 ? (atr14 / price) * 100 : 0;
    const macdHist = macdHistogram(close);

    const ranges = close.map((c, i) => (c !== 0 ? (high[i] - low[i]) / c : 0));
    const avgRangePct = mean(ranges.slice(-10)) * 100;

    let gapPct = 0.0;
    if (n >= 2) {
      const prevClose = close[n - 2];
      gapPct = prevClose > 0 ? (open[n - 1] / prevClose - 1) * 100 : 0;
    }

    return {
      ticker,
      price: round(price, 2),
      change_5d: round(change5, 2),
      change_7d: round(change7, 2),
      change_20d: round(change20, 2),
      avg_vol_20d: Math.round(avgVol20),
      rel_vol: round(relVol, 2),
      vol_trend_5d: round(volTrend5, 0),
      vol_trend_7d: round(volTrend7, 0),
      dollar_vol_20d: Math.round(dollarVol20),
      ma_20: round(ma20, 2),
      ma_50: round(ma50, 2),
      ma_200: round(ma200, 2),
      pct_from_ma20: round(pctFromMa20, 2),
      pct_from_ma50: round(pctFromMa50, 2),
      pct_from_52w_high: round(pctFrom52wHigh, 2),
      rsi_14: round(rsi14, 1),
      atr_14: round(atr14, 2),
      atr_pct: round(atrPct, 2),
      macd_hist: round(macdHist, 3),
      avg_range_pct: round(avgRangePct, 1),
      gap_pct: round(gapPct, 2),
    };
  } catch {
    return null;
  }
}

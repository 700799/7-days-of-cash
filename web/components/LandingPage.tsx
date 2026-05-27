"use client";

import { useAuth } from "./AuthProvider";

const DEMO_TICKERS = [
  { ticker: "NVDA", ret_7d: "+14.2%", score: "94.1", strategy: "MOMENTUM" },
  { ticker: "AVGO", ret_7d: "+11.8%", score: "91.3", strategy: "BREAKOUT" },
  { ticker: "SMH",  ret_7d: "+10.5%", score: "88.7", strategy: "VOLUME" },
  { ticker: "ASTS", ret_7d: "+9.1%",  score: "85.2", strategy: "MOMENTUM" },
  { ticker: "RKLB", ret_7d: "+8.6%",  score: "82.4", strategy: "REL. STRENGTH" },
];

const FEATURES = [
  {
    icon: "⬡",
    title: "5 Scoring Agents",
    body: "Momentum, breakout, volume surge, relative strength, and mean-reversion each vote independently. The composite score ranks every ticker.",
  },
  {
    icon: "◈",
    title: "700+ Tickers",
    body: "Full S&P 500 plus extended market. Screened against VOO, VXF, and VTIAX benchmarks so you know the true alpha — not just raw return.",
  },
  {
    icon: "◉",
    title: "4-Hour Refresh",
    body: "Pre-computed every 4 hours. Results load in < 100ms from cache — no waiting, no rate limits.",
  },
  {
    icon: "◎",
    title: "Email Digest",
    body: "Daily or weekly digest of your watchlist movers and screener leaders, delivered straight to your inbox.",
  },
  {
    icon: "▣",
    title: "Price Alerts",
    body: "Set price alerts on any ticker. Get notified by email when a stock crosses your target.",
  },
  {
    icon: "⊞",
    title: "CSV Export",
    body: "Download the full screener results as a CSV for import into Excel, Google Sheets, or your own analysis.",
  },
];

export function LandingPage() {
  const { login } = useAuth();

  return (
    <div className="min-h-screen bg-black text-b7-green font-mono">
      {/* ── Hero ───────────────────────────────────────────────────── */}
      <div className="max-w-4xl mx-auto px-4 pt-16 pb-8 text-center">
        <div className="text-b7-green-muted text-xs uppercase mb-4 tracking-widest">
          {`> best7daysmula`}
        </div>
        <h1 className="text-2xl sm:text-4xl font-bold text-b7-green mb-4 leading-tight">
          Find the Market's Strongest<br className="hidden sm:block" />
          7-Day Uptrends
        </h1>
        <p className="text-b7-green-dim text-sm sm:text-base max-w-2xl mx-auto mb-8">
          Multi-agent AI scores 700+ tickers for momentum, breakout, volume surge,
          relative strength, and mean-reversion. Refreshed every 4 hours.
          Free to use. Not financial advice.
        </p>
        <button
          type="button"
          onClick={login}
          className="px-8 py-3 border border-b7-green text-b7-green hover:bg-b7-green hover:text-black transition text-sm uppercase tracking-wide font-bold"
        >
          {`[ > Sign in free with Google ]`}
        </button>
      </div>

      {/* ── Live demo snapshot ──────────────────────────────────────── */}
      <div className="max-w-4xl mx-auto px-4 pb-12">
        <div className="border border-b7-green-border overflow-x-auto">
          <div className="px-3 py-1 border-b border-b7-green-border/40 bg-black flex items-center justify-between">
            <span className="text-b7-green-muted text-xs uppercase">
              {`> sample leaders — sign in to see today's real picks`}
            </span>
            <span className="text-b7-green-muted text-xs">◉ refreshed every 4h</span>
          </div>
          <table className="w-full text-xs">
            <thead className="border-b border-b7-green-border">
              <tr>
                {["TICKER", "7D %", "SCORE", "BEST STRAT"].map((h) => (
                  <th key={h} className="py-2 px-3 uppercase text-left text-b7-green">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {DEMO_TICKERS.map((r, idx) => (
                <tr
                  key={r.ticker}
                  className={`border-b border-green-500/10 ${idx === 0 ? "bg-b7-green/10" : ""}`}
                >
                  <td className="py-2 px-3 font-bold">
                    {idx === 0 ? `★ ${r.ticker}` : r.ticker}
                  </td>
                  <td className="py-2 px-3 text-b7-green">{r.ret_7d}</td>
                  <td className="py-2 px-3">{r.score}</td>
                  <td className="py-2 px-3 text-b7-green-muted uppercase text-xs">{r.strategy}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* ── Feature grid ────────────────────────────────────────────── */}
      <div className="max-w-4xl mx-auto px-4 pb-16">
        <div className="text-center mb-8">
          <span className="text-b7-green-muted text-xs uppercase tracking-widest">
            {`> everything included, free`}
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((f) => (
            <div key={f.title} className="border border-b7-green-border p-4 space-y-2">
              <div className="text-b7-green text-xl">{f.icon}</div>
              <div className="text-b7-green text-sm uppercase font-bold">{f.title}</div>
              <div className="text-b7-green-dim text-xs leading-relaxed">{f.body}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Bottom CTA ──────────────────────────────────────────────── */}
      <div className="max-w-4xl mx-auto px-4 pb-16 text-center">
        <div className="border border-b7-green-border p-8 space-y-4">
          <div className="text-b7-green text-sm uppercase">
            {`> ready to find the leaders?`}
          </div>
          <button
            type="button"
            onClick={login}
            className="px-8 py-3 border border-b7-green bg-b7-green text-black hover:bg-b7-green/90 transition text-sm uppercase font-bold"
          >
            Get started free →
          </button>
          <p className="text-b7-green-muted text-xs">
            Sign in with Google. No credit card. No setup.
          </p>
        </div>
      </div>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer className="border-t border-b7-green-border/40 max-w-4xl mx-auto px-4 py-8 text-center">
        <p className="text-b7-green-muted text-xs">
          Not financial advice. Past screener performance does not guarantee future results.
          Always do your own research.
        </p>
      </footer>
    </div>
  );
}

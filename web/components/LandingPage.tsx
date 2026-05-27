"use client";

import { useAuth } from "./AuthProvider";
import { createCheckoutSession } from "@/lib/api";
import { useState } from "react";

const DEMO_TICKERS = [
  { ticker: "NVDA", ret_7d: "+14.2%", score: "94.1", strategy: "MOMENTUM" },
  { ticker: "AVGO", ret_7d: "+11.8%", score: "91.3", strategy: "BREAKOUT" },
  { ticker: "SMH",  ret_7d: "+10.5%", score: "88.7", strategy: "VOLUME" },
  { ticker: "ASTS", ret_7d: "+9.1%",  score: "85.2", strategy: "MOMENTUM" },
  { ticker: "RKLB", ret_7d: "+8.6%",  score: "82.4", strategy: "REL. STRENGTH" },
];

const FREE_FEATURES = [
  "Cached full S&P 500 screener (refreshed every 4h)",
  "5-ticker watchlist",
  "Daily email digest",
  "Market regime + benchmark panel",
  "Trending news feed",
  "Per-ticker mover analysis",
];

const PRO_FEATURES = [
  "Everything in Free",
  "Unlimited watchlist tickers",
  "Live screener on your watchlist",
  "Weekly digest + custom digest email",
  "Price alerts (up to 10)",
  "CSV export of screener results",
  "Custom screener filter UI",
  "30-day screener history archive",
];

export function LandingPage() {
  const { login } = useAuth();
  const [upgrading, setUpgrading] = useState(false);

  async function handleUpgrade() {
    setUpgrading(true);
    try {
      const { url } = await createCheckoutSession();
      window.location.href = url;
    } catch {
      setUpgrading(false);
    }
  }

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
          Not financial advice.
        </p>
        <div className="flex flex-wrap items-center justify-center gap-3">
          <button
            type="button"
            onClick={login}
            className="px-6 py-2 border border-b7-green text-b7-green hover:bg-b7-green hover:text-black transition text-sm uppercase tracking-wide"
          >
            {`[ > SIGN IN FREE ]`}
          </button>
          <a
            href="#pricing"
            className="px-6 py-2 border border-b7-green-border text-b7-green-muted hover:text-b7-green transition text-sm uppercase tracking-wide"
          >
            See Pro plan ↓
          </a>
        </div>
      </div>

      {/* ── Live demo snapshot ──────────────────────────────────────── */}
      <div className="max-w-4xl mx-auto px-4 pb-12">
        <div className="border border-b7-green-border overflow-x-auto">
          <div className="px-3 py-1 border-b border-b7-green-border/40 bg-black flex items-center justify-between">
            <span className="text-b7-green-muted text-xs uppercase">
              {`> today's top picks (sample — sign in for live data)`}
            </span>
            <span className="text-b7-green-muted text-xs">◉ CACHED · 4h refresh</span>
          </div>
          <table className="w-full text-xs">
            <thead className="border-b border-b7-green-border">
              <tr>
                {["TICKER", "7D%", "SCORE", "BEST STRAT"].map((h) => (
                  <th
                    key={h}
                    className="py-2 px-3 uppercase text-left text-b7-green"
                  >
                    {h}
                  </th>
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
          <div className="px-3 py-2 text-b7-green-muted text-xs border-t border-b7-green-border/40">
            {`> demo data only — sign in to see today's real-time leaders`}
          </div>
        </div>
      </div>

      {/* ── Feature grid ────────────────────────────────────────────── */}
      <div className="max-w-4xl mx-auto px-4 pb-16">
        <div className="text-center mb-8">
          <span className="text-b7-green-muted text-xs uppercase tracking-widest">
            {`> how it works`}
          </span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {[
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
              body: "Pre-computed by Vercel Cron every 4 hours. Results load in < 100ms from Postgres cache — no waiting, no rate limits, no yfinance hammering.",
            },
          ].map((f) => (
            <div key={f.title} className="border border-b7-green-border p-4 space-y-2">
              <div className="text-b7-green text-xl">{f.icon}</div>
              <div className="text-b7-green text-sm uppercase font-bold">{f.title}</div>
              <div className="text-b7-green-dim text-xs leading-relaxed">{f.body}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Pricing ─────────────────────────────────────────────────── */}
      <div id="pricing" className="max-w-4xl mx-auto px-4 pb-16">
        <div className="text-center mb-8">
          <span className="text-b7-green-muted text-xs uppercase tracking-widest">
            {`> pricing`}
          </span>
          <p className="text-b7-green-dim text-xs mt-2">
            No credit card required for free tier. Cancel anytime.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {/* Free card */}
          <div className="border border-b7-green-border p-5 space-y-4">
            <div>
              <div className="text-b7-green text-sm uppercase font-bold">Free</div>
              <div className="text-b7-green text-2xl font-bold mt-1">$0<span className="text-b7-green-muted text-xs">/mo</span></div>
            </div>
            <ul className="space-y-2">
              {FREE_FEATURES.map((f) => (
                <li key={f} className="text-xs text-b7-green-dim flex gap-2">
                  <span className="text-b7-green flex-shrink-0">✓</span>
                  {f}
                </li>
              ))}
            </ul>
            <button
              type="button"
              onClick={login}
              className="w-full py-2 border border-b7-green-border text-b7-green-muted hover:text-b7-green transition text-xs uppercase"
            >
              Get started free →
            </button>
          </div>

          {/* Pro card */}
          <div className="border border-b7-green bg-b7-green/5 p-5 space-y-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-b7-green text-sm uppercase font-bold">Pro</span>
                <span className="text-[10px] bg-b7-green text-black px-1.5 py-0.5 uppercase">
                  Recommended
                </span>
              </div>
              <div className="text-b7-green text-2xl font-bold mt-1">$9<span className="text-b7-green-muted text-xs">/mo</span></div>
            </div>
            <ul className="space-y-2">
              {PRO_FEATURES.map((f) => (
                <li key={f} className="text-xs text-b7-green-dim flex gap-2">
                  <span className="text-b7-green flex-shrink-0">★</span>
                  {f}
                </li>
              ))}
            </ul>
            <button
              type="button"
              onClick={handleUpgrade}
              disabled={upgrading}
              className="w-full py-2 border border-b7-green bg-b7-green text-black hover:bg-b7-green/90 transition text-xs uppercase font-bold disabled:opacity-60"
            >
              {upgrading ? "Redirecting to Stripe…" : "Upgrade to Pro →"}
            </button>
          </div>
        </div>
      </div>

      {/* ── Footer ──────────────────────────────────────────────────── */}
      <footer className="border-t border-b7-green-border/40 max-w-4xl mx-auto px-4 py-8 text-center">
        <p className="text-b7-green-muted text-xs">
          Best7DaysMula is not financial advice. Past screener performance does not
          guarantee future results. Always do your own research.
        </p>
        <div className="flex items-center justify-center gap-4 mt-4 text-xs text-b7-green-muted">
          <a href="/privacy" className="hover:text-b7-green transition">Privacy</a>
          <span>·</span>
          <a href="/terms" className="hover:text-b7-green transition">Terms</a>
          <span>·</span>
          <a href="mailto:support@best7daysmula.com" className="hover:text-b7-green transition">Support</a>
        </div>
      </footer>
    </div>
  );
}

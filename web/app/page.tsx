"use client";

import { Download, Loader2, Play, RefreshCw } from "lucide-react";
import { useMemo, useState } from "react";
import { AuthButton } from "@/components/AuthButton";
import { useAuth } from "@/components/AuthProvider";
import { Banner } from "@/components/Banner";
import { BenchmarkBar } from "@/components/BenchmarkBar";
import { EmailDigestSettings } from "@/components/EmailDigestSettings";
import { LandingPage } from "@/components/LandingPage";
import { MoversList } from "@/components/MoversList";
import { NewsFeed } from "@/components/NewsFeed";
import { PriceAlerts } from "@/components/PriceAlerts";
import { RegimePanel } from "@/components/RegimePanel";
import { ScreenerResults } from "@/components/ScreenerResults";
import { TickerForm } from "@/components/TickerForm";
import { TickerPills } from "@/components/TickerPills";
import { TrendingNews } from "@/components/TrendingNews";
import { runScreener, screenerExportUrl, type ScreenerPayload } from "@/lib/api";
import { useCachedScreener, useDefaults, useTickers } from "@/lib/hooks";

export default function HomePage() {
  const { user, loading: authLoading } = useAuth();
  const signedIn = !!user;
  const { tickers } = useTickers(signedIn);
  const { defaults } = useDefaults();

  // Pre-computed results (loads instantly from Postgres cache, refreshed every 4h by cron)
  const { payload: cached, loading: cachedLoading } = useCachedScreener();

  // Live override — user-triggered run against their watchlist (Pro only)
  const [running, setRunning] = useState(false);
  const [livePayload, setLivePayload] = useState<ScreenerPayload | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  // Show live results if they exist, else fall back to pre-computed cache
  const payload = livePayload ?? cached;
  const isLive = !!livePayload;

  const watchSymbols = tickers.map((t) => t.symbol);
  const resultSymbols = (payload?.results ?? []).map((r) => r.ticker);

  // For anon users with no watchlist, defaults stand in as the effective watchlist.
  const effectiveSymbols = useMemo(() => {
    if (signedIn) return watchSymbols;
    if (watchSymbols.length > 0) return watchSymbols;
    return defaults;
  }, [signedIn, watchSymbols, defaults]);

  // Merge effective watchlist with screener results (deduped, uppercased).
  const mergedSymbols = useMemo(() => {
    const set = new Set<string>();
    for (const s of effectiveSymbols) set.add(s.toUpperCase());
    for (const s of resultSymbols) set.add(s.toUpperCase());
    return Array.from(set);
  }, [effectiveSymbols, resultSymbols]);

  async function handleRun() {
    setRunning(true);
    setRunError(null);
    try {
      const symbols = effectiveSymbols;
      const res = await runScreener(
        symbols.length > 0 ? { tickers: symbols } : {},
      );
      setLivePayload(res);
    } catch (err) {
      setRunError(err instanceof Error ? err.message : "screener failed");
    } finally {
      setRunning(false);
    }
  }

  function handleResetToCache() {
    setLivePayload(null);
    setRunError(null);
  }

  function fmtAge(ranAt: string): string {
    const diffMs = Date.now() - new Date(ranAt).getTime();
    const mins = Math.round(diffMs / 60_000);
    if (mins < 2) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.round(mins / 60);
    return `${hrs}h ago`;
  }

  // Show the landing/marketing page to visitors who are not signed in
  if (!authLoading && !signedIn) {
    return <LandingPage />;
  }

  return (
    <main className="relative min-h-screen pb-12">
      <Banner />

      <p className="text-center text-b7-green-dim mb-6 mt-2 px-4 text-xs sm:text-sm">
        Find the strongest 7-day uptrends. Volume-confirmed. Multi-agent scored.
        Refreshed every 4 hours.
      </p>

      <div className="absolute top-3 right-3 z-10">
        <AuthButton />
      </div>

      <div className="max-w-6xl mx-auto px-4 py-4 space-y-4">
        <TrendingNews />

        <RegimePanel regime={payload?.regime ?? null} />
        <BenchmarkBar benchmarks={payload?.benchmarks ?? []} />

        <section className="border border-b7-green-border p-3 space-y-2">
          <h2 className="text-b7-green uppercase text-sm">{`> WATCHLIST`}</h2>
          <TickerForm disabled={authLoading || !signedIn} />
          <TickerPills
            tickers={tickers}
            signedIn={signedIn}
            defaults={defaults}
          />
        </section>

        {/* Screener controls row */}
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={handleRun}
            disabled={running}
            aria-busy={running}
            title="Run live screener on your watchlist"
            className="inline-flex items-center gap-2 px-3 py-1 border border-b7-green-border text-b7-green hover:bg-b7-green/10 hover:text-b7-green-dim transition rounded-sm uppercase text-xs disabled:opacity-50"
          >
            {running ? (
              <>
                <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                <span>RUNNING…</span>
              </>
            ) : (
              <>
                <Play size={14} aria-hidden="true" />
                <span>[ &gt; RUN ON WATCHLIST ]</span>
              </>
            )}
          </button>

          {isLive && (
            <button
              type="button"
              onClick={handleResetToCache}
              className="inline-flex items-center gap-2 px-3 py-1 border border-b7-green-border/60 text-b7-green-muted hover:text-b7-green transition rounded-sm uppercase text-xs"
            >
              <RefreshCw size={12} aria-hidden="true" />
              <span>[ SHOW FULL MARKET ]</span>
            </button>
          )}

          {/* CSV export */}
          {payload && (
            <a
              href={screenerExportUrl()}
              download
              className="inline-flex items-center gap-1 px-3 py-1 border border-b7-green-border/60 text-b7-green-muted hover:text-b7-green transition rounded-sm uppercase text-xs"
              title="Download screener results as CSV"
            >
              <Download size={12} aria-hidden="true" />
              <span>[ CSV ]</span>
            </a>
          )}

          {/* Status badge */}
          {!running && payload?.ran_at && (
            <span className="text-b7-green-muted text-xs uppercase">
              {isLive ? (
                <span className="text-b7-green">● LIVE — watchlist</span>
              ) : (
                <span>
                  ○ CACHED — full S&P 500 ·{" "}
                  {fmtAge(payload.ran_at)}
                </span>
              )}
            </span>
          )}

          {runError && (
            <span className="text-red-400 text-xs uppercase">
              {`! ${runError}`}
            </span>
          )}
        </div>

        <ScreenerResults
          results={payload?.results ?? []}
          loading={running || (!payload && cachedLoading)}
        />

        <PriceAlerts />

        <MoversList symbols={mergedSymbols} />

        <EmailDigestSettings />

        <NewsFeed
          watchlist={effectiveSymbols}
          resultTickers={resultSymbols}
        />
      </div>
    </main>
  );
}

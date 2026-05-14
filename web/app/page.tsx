"use client";

import { Loader2, Play } from "lucide-react";
import { useMemo, useState } from "react";
import { AuthButton } from "@/components/AuthButton";
import { useAuth } from "@/components/AuthProvider";
import { Banner } from "@/components/Banner";
import { BenchmarkBar } from "@/components/BenchmarkBar";
import { EmailDigestSettings } from "@/components/EmailDigestSettings";
import { MoversList } from "@/components/MoversList";
import { NewsFeed } from "@/components/NewsFeed";
import { RegimePanel } from "@/components/RegimePanel";
import { ScreenerResults } from "@/components/ScreenerResults";
import { TickerForm } from "@/components/TickerForm";
import { TickerPills } from "@/components/TickerPills";
import { TrendingNews } from "@/components/TrendingNews";
import { runScreener, type ScreenerPayload } from "@/lib/api";
import { useDefaults, useTickers } from "@/lib/hooks";

export default function HomePage() {
  const { user, loading: authLoading } = useAuth();
  const signedIn = !!user;
  const { tickers } = useTickers(signedIn);
  const { defaults } = useDefaults();
  const [running, setRunning] = useState(false);
  const [payload, setPayload] = useState<ScreenerPayload | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

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
      setPayload(res);
    } catch (err) {
      setRunError(err instanceof Error ? err.message : "screener failed");
    } finally {
      setRunning(false);
    }
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

        <div>
          <button
            type="button"
            onClick={handleRun}
            disabled={running}
            aria-busy={running}
            className="inline-flex items-center gap-2 px-3 py-1 border border-b7-green-border text-b7-green hover:bg-green-500/10 hover:text-b7-green-dim transition rounded-sm uppercase text-xs disabled:opacity-50"
          >
            {running ? (
              <>
                <Loader2 size={14} className="animate-spin" aria-hidden="true" />
                <span>RUNNING…</span>
              </>
            ) : (
              <>
                <Play size={14} aria-hidden="true" />
                <span>[ &gt; RUN SCREENER ]</span>
              </>
            )}
          </button>
          {runError && (
            <span className="ml-3 text-red-400 text-xs uppercase">
              {`! ${runError}`}
            </span>
          )}
          {payload?.ran_at && (
            <span className="ml-3 text-b7-green-muted text-xs uppercase">
              {`last ran: ${new Date(payload.ran_at).toLocaleString()}`}
            </span>
          )}
        </div>

        <ScreenerResults results={payload?.results ?? []} loading={running} />

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

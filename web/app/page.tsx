"use client";

import { Play } from "lucide-react";
import { useState } from "react";
import { AuthButton } from "@/components/AuthButton";
import { useAuth } from "@/components/AuthProvider";
import { Banner } from "@/components/Banner";
import { BenchmarkBar } from "@/components/BenchmarkBar";
import { NewsFeed } from "@/components/NewsFeed";
import { RegimePanel } from "@/components/RegimePanel";
import { ScreenerResults } from "@/components/ScreenerResults";
import { TickerForm } from "@/components/TickerForm";
import { TickerPills } from "@/components/TickerPills";
import { runScreener, type ScreenerPayload } from "@/lib/api";
import { useTickers } from "@/lib/hooks";

export default function HomePage() {
  const { user, loading: authLoading } = useAuth();
  const signedIn = !!user;
  const { tickers } = useTickers(signedIn);
  const [running, setRunning] = useState(false);
  const [payload, setPayload] = useState<ScreenerPayload | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  async function handleRun() {
    setRunning(true);
    setRunError(null);
    try {
      const symbols = tickers.map((t) => t.symbol);
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

  const watchSymbols = tickers.map((t) => t.symbol);
  const resultSymbols = (payload?.results ?? []).map((r) => r.ticker);

  return (
    <main className="relative min-h-screen pb-12">
      <Banner />

      <div className="absolute top-3 right-3 z-10">
        <AuthButton />
      </div>

      <div className="max-w-6xl mx-auto px-4 py-4 space-y-4">
        <RegimePanel regime={payload?.regime ?? null} />
        <BenchmarkBar benchmarks={payload?.benchmarks ?? []} />

        <section className="border border-green-500/40 p-3 space-y-2">
          <h2 className="text-green-400 uppercase text-sm">{`> WATCHLIST`}</h2>
          <TickerForm disabled={authLoading || !signedIn} />
          <TickerPills tickers={tickers} signedIn={signedIn} />
        </section>

        <div>
          <button
            type="button"
            onClick={handleRun}
            disabled={running}
            className="inline-flex items-center gap-2 px-3 py-1 border border-green-500/60 text-green-400 hover:bg-green-500/10 hover:text-green-300 transition rounded-sm uppercase text-xs disabled:opacity-50"
          >
            <Play size={14} />
            {running ? "running…" : "[ > RUN SCREENER ]"}
          </button>
          {runError && (
            <span className="ml-3 text-red-400 text-xs uppercase">
              {`! ${runError}`}
            </span>
          )}
          {payload?.ran_at && (
            <span className="ml-3 text-green-500/60 text-xs uppercase">
              {`last ran: ${new Date(payload.ran_at).toLocaleString()}`}
            </span>
          )}
        </div>

        <ScreenerResults results={payload?.results ?? []} />

        <NewsFeed
          watchlist={watchSymbols}
          resultTickers={resultSymbols}
        />
      </div>
    </main>
  );
}

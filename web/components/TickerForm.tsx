"use client";

import { Plus } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useSWRConfig } from "swr";
import { addTicker, ApiError, type Ticker } from "@/lib/api";

type Props = {
  /** When true, submissions are blocked locally — used for unauthenticated users. */
  disabled?: boolean;
};

export function TickerForm({ disabled = false }: Props) {
  const [symbol, setSymbol] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const { mutate } = useSWRConfig();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const sym = symbol.trim().toUpperCase();
    if (!sym) {
      setError("symbol required");
      return;
    }
    if (disabled) {
      setError("sign in to save tickers");
      return;
    }

    setBusy(true);
    // Optimistic update
    const optimistic: Ticker = {
      symbol: sym,
      note: note.trim() || null,
      added_at: new Date().toISOString(),
    };
    try {
      await mutate(
        "tickers:list",
        async (current: Ticker[] | undefined) => {
          const created = await addTicker(sym, note.trim() || undefined);
          const list = current ?? [];
          return [...list.filter((t) => t.symbol !== sym), created];
        },
        {
          optimisticData: (current?: Ticker[]) => [
            ...(current ?? []).filter((t) => t.symbol !== sym),
            optimistic,
          ],
          rollbackOnError: true,
          revalidate: false,
        },
      );
      setSymbol("");
      setNote("");
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) setError("ticker already in watchlist");
        else if (err.status === 422) setError("invalid ticker symbol");
        else setError(err.message || "failed to add ticker");
      } else {
        setError("network error");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="border border-green-500/40 p-3 bg-black"
      aria-label="add ticker"
    >
      <h3 className="text-green-400 uppercase text-sm mb-2">{`> ADD TICKER`}</h3>
      <div className="flex flex-col sm:flex-row gap-2">
        <input
          aria-label="ticker symbol"
          name="symbol"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          placeholder="AAPL"
          className="bg-black border border-green-500/40 text-green-400 px-2 py-1 uppercase placeholder:text-green-700 focus:outline-none focus:border-green-400 w-32"
          maxLength={10}
          autoComplete="off"
        />
        <input
          aria-label="note"
          name="note"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="optional note"
          className="bg-black border border-green-500/40 text-green-400 px-2 py-1 placeholder:text-green-700 focus:outline-none focus:border-green-400 flex-1"
          maxLength={200}
          autoComplete="off"
        />
        <button
          type="submit"
          disabled={busy}
          className="inline-flex items-center gap-2 px-3 py-1 border border-green-500/60 text-green-400 hover:bg-green-500/10 hover:text-green-300 transition rounded-sm uppercase text-xs disabled:opacity-50"
        >
          <Plus size={14} />
          {busy ? "adding…" : "[ + ADD ]"}
        </button>
      </div>
      {error && (
        <div role="alert" className="mt-2 text-red-400 text-xs uppercase">
          {`! ${error}`}
        </div>
      )}
    </form>
  );
}

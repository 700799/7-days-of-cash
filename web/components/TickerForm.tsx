"use client";

import { Plus } from "lucide-react";
import { useEffect, useRef, useState, type FormEvent } from "react";
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
  const [success, setSuccess] = useState<string | null>(null);
  const successTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { mutate } = useSWRConfig();

  // Clean up success flash timer on unmount.
  useEffect(() => {
    return () => {
      if (successTimerRef.current) clearTimeout(successTimerRef.current);
    };
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
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
      setSuccess(`✓ Added ${sym}`);
      if (successTimerRef.current) clearTimeout(successTimerRef.current);
      successTimerRef.current = setTimeout(() => setSuccess(null), 2000);
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setError("Already in your watchlist.");
        } else if (err.status === 422) {
          setError("Couldn't find that symbol — check spelling?");
        } else {
          setError(err.message || "failed to add ticker");
        }
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
      className="border border-b7-green-border p-3 bg-black"
      aria-label="add ticker"
    >
      <h3 className="text-b7-green uppercase text-sm mb-2">{`> ADD TICKER`}</h3>
      <div className="flex flex-col sm:flex-row gap-2">
        <input
          aria-label="ticker symbol"
          name="symbol"
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          placeholder="AAPL"
          className="bg-black border border-b7-green-border text-b7-green px-2 py-1 uppercase placeholder:text-green-700 focus:outline-none focus:ring-2 focus:ring-b7-green focus:border-b7-green w-32"
          maxLength={10}
          autoComplete="off"
        />
        <input
          aria-label="note"
          name="note"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="optional note"
          className="bg-black border border-b7-green-border text-b7-green px-2 py-1 placeholder:text-green-700 focus:outline-none focus:ring-2 focus:ring-b7-green focus:border-b7-green flex-1"
          maxLength={200}
          autoComplete="off"
        />
        <button
          type="submit"
          disabled={busy}
          className="inline-flex items-center gap-2 px-3 py-1 border border-b7-green-border text-b7-green hover:bg-green-500/10 hover:text-b7-green-dim transition rounded-sm uppercase text-xs disabled:opacity-50"
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
      {success && (
        <div
          role="status"
          data-testid="ticker-form-success"
          className="mt-2 text-b7-green-dim text-xs uppercase"
        >
          {success}
        </div>
      )}
    </form>
  );
}

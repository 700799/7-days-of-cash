"use client";

import { Check, Pencil, X } from "lucide-react";
import { useState } from "react";
import { useSWRConfig } from "swr";
import {
  deleteTicker,
  updateTicker,
  type Ticker,
} from "@/lib/api";

type Props = {
  tickers: Ticker[];
  signedIn: boolean;
};

export function TickerPills({ tickers, signedIn }: Props) {
  const { mutate } = useSWRConfig();
  const [editing, setEditing] = useState<string | null>(null);
  const [editNote, setEditNote] = useState<string>("");

  async function handleDelete(symbol: string) {
    if (typeof window !== "undefined") {
      const ok = window.confirm(`Remove ${symbol} from watchlist?`);
      if (!ok) return;
    }
    await mutate(
      "tickers:list",
      async (current: Ticker[] | undefined) => {
        await deleteTicker(symbol);
        return (current ?? []).filter((t) => t.symbol !== symbol);
      },
      {
        optimisticData: (current?: Ticker[]) =>
          (current ?? []).filter((t) => t.symbol !== symbol),
        rollbackOnError: true,
        revalidate: false,
      },
    );
  }

  function startEdit(t: Ticker) {
    setEditing(t.symbol);
    setEditNote(t.note ?? "");
  }

  async function saveEdit(symbol: string) {
    await mutate(
      "tickers:list",
      async (current: Ticker[] | undefined) => {
        const updated = await updateTicker(symbol, editNote);
        return (current ?? []).map((t) =>
          t.symbol === symbol ? updated : t,
        );
      },
      {
        optimisticData: (current?: Ticker[]) =>
          (current ?? []).map((t) =>
            t.symbol === symbol ? { ...t, note: editNote } : t,
          ),
        rollbackOnError: true,
        revalidate: false,
      },
    );
    setEditing(null);
    setEditNote("");
  }

  if (tickers.length === 0) {
    return (
      <div className="text-green-500/60 text-xs uppercase mt-2">
        {signedIn
          ? `> NO TICKERS ADDED — add one above`
          : `> NO TICKERS ADDED — sign in to save your watchlist`}
      </div>
    );
  }

  return (
    <div className="mt-2 space-y-2">
      <div className="flex flex-wrap gap-2" data-testid="ticker-pills">
        {tickers.map((t) => (
          <div key={t.symbol} className="flex flex-col gap-1">
            <span
              className="inline-flex items-center gap-2 px-3 py-1 border border-green-500/60 text-green-400 hover:bg-green-500/10 hover:text-green-300 transition rounded-sm uppercase text-xs"
              data-testid={`pill-${t.symbol}`}
            >
              <button
                type="button"
                onClick={() => startEdit(t)}
                className="uppercase tracking-wider"
                aria-label={`edit ${t.symbol}`}
                title={t.note ?? ""}
              >
                {t.symbol}
              </button>
              <button
                type="button"
                onClick={() => startEdit(t)}
                aria-label={`edit note for ${t.symbol}`}
                className="opacity-60 hover:opacity-100"
              >
                <Pencil size={10} />
              </button>
              <button
                type="button"
                onClick={() => handleDelete(t.symbol)}
                aria-label={`remove ${t.symbol}`}
                className="hover:text-red-400"
              >
                <X size={12} />
              </button>
            </span>
            {editing === t.symbol && (
              <div className="flex items-center gap-1 ml-1">
                <input
                  aria-label={`note for ${t.symbol}`}
                  value={editNote}
                  onChange={(e) => setEditNote(e.target.value)}
                  className="bg-black border border-green-500/40 text-green-400 px-2 py-0.5 text-xs focus:outline-none focus:border-green-400 w-40"
                  maxLength={200}
                />
                <button
                  type="button"
                  onClick={() => saveEdit(t.symbol)}
                  aria-label={`save note for ${t.symbol}`}
                  className="text-green-400 hover:text-green-300"
                >
                  <Check size={14} />
                </button>
                <button
                  type="button"
                  onClick={() => setEditing(null)}
                  aria-label="cancel"
                  className="text-green-500/60 hover:text-red-400"
                >
                  <X size={14} />
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getSharedScreenerResult } from "@/lib/api";
import type { ScreenerResultRow } from "@/lib/api";

type SharedResult = {
  id: number;
  ran_at: string;
  results_count: number;
  top_picks: ScreenerResultRow[];
};

function fmtPct(v: unknown): string {
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

export default function SharedResultPage() {
  const params = useParams();
  const id = Number(params.id);
  const [data, setData] = useState<SharedResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    getSharedScreenerResult(id)
      .then(setData)
      .catch((e) => setError(e.message ?? "Not found"))
      .finally(() => setLoading(false));
  }, [id]);

  function formatDate(iso: string) {
    try {
      return new Date(iso).toLocaleString("en-US", {
        weekday: "short", month: "short", day: "numeric",
        hour: "2-digit", minute: "2-digit", timeZoneName: "short",
      });
    } catch {
      return iso;
    }
  }

  return (
    <main className="min-h-screen bg-black text-b7-green font-mono max-w-4xl mx-auto px-4 py-8">
      <div className="mb-6">
        <a href="/" className="text-b7-green-muted text-xs uppercase hover:text-b7-green transition">
          ← Back to screener
        </a>
      </div>

      {loading && (
        <div className="text-b7-green-muted text-xs animate-pulse">Loading screener result…</div>
      )}

      {error && (
        <div className="border border-red-800 p-3 text-red-400 text-xs">
          {`! ${error}`}
        </div>
      )}

      {data && (
        <div className="space-y-4">
          <div>
            <h1 className="text-b7-green uppercase text-sm">
              {`> SCREENER RESULT #${data.id}`}
            </h1>
            <p className="text-b7-green-muted text-xs mt-1">
              Run at {formatDate(data.ran_at)} · {data.results_count} total leaders
            </p>
          </div>

          <div className="border border-b7-green-border overflow-x-auto">
            <div className="px-3 py-1 border-b border-b7-green-border/40 bg-black">
              <span className="text-b7-green-muted text-xs uppercase">
                {`> Top ${data.top_picks.length} picks from this run`}
              </span>
            </div>
            <table className="w-full text-xs">
              <thead className="border-b border-b7-green-border">
                <tr>
                  {["#", "TICKER", "7D%", "SCORE", "vs VOO", "BEST STRAT"].map((h) => (
                    <th key={h} className="py-2 px-3 uppercase text-left text-b7-green">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.top_picks.map((r, idx) => (
                  <tr
                    key={r.ticker}
                    className={`border-b border-green-500/10 ${idx === 0 ? "bg-b7-green/10" : ""}`}
                  >
                    <td className="py-2 px-3 text-b7-green-muted">{idx + 1}</td>
                    <td className="py-2 px-3 font-bold">
                      <a
                        href={`https://finance.yahoo.com/quote/${r.ticker}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hover:underline"
                      >
                        {idx === 0 ? `★ ${r.ticker}` : r.ticker}
                      </a>
                    </td>
                    <td className={`py-2 px-3 ${Number(r.ret_7d) >= 0 ? "text-b7-green" : "text-red-400"}`}>
                      {fmtPct(r.ret_7d)}
                    </td>
                    <td className="py-2 px-3">{Number(r.score ?? r.composite_score).toFixed(1)}</td>
                    <td className={`py-2 px-3 ${Number(r.vs_voo) >= 0 ? "text-b7-green" : "text-red-400"}`}>
                      {fmtPct(r.vs_voo)}
                    </td>
                    <td className="py-2 px-3 uppercase text-b7-green-muted">
                      {String(r.best_strategy ?? "—")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="text-b7-green-muted text-xs">
            Not financial advice. Historical screener picks do not guarantee future performance.{" "}
            <a href="/" className="text-b7-green hover:underline">Run the live screener →</a>
          </p>
        </div>
      )}
    </main>
  );
}

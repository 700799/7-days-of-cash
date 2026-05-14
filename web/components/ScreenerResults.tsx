"use client";

import clsx from "clsx";
import { useMemo, useState } from "react";
import type { ScreenerResultRow } from "@/lib/api";

type Props = {
  results: ScreenerResultRow[];
};

type SortKey =
  | "ticker"
  | "price"
  | "ret_7d"
  | "score"
  | "momentum"
  | "breakout"
  | "volume"
  | "rs"
  | "mean_reversion"
  | "vs_voo";

const COLUMNS: { key: SortKey; label: string; numeric: boolean }[] = [
  { key: "ticker", label: "TICKER", numeric: false },
  { key: "price", label: "PRICE", numeric: true },
  { key: "ret_7d", label: "7D%", numeric: true },
  { key: "score", label: "SCORE", numeric: true },
  { key: "momentum", label: "MOM", numeric: true },
  { key: "breakout", label: "BRK", numeric: true },
  { key: "volume", label: "VOL", numeric: true },
  { key: "rs", label: "RS", numeric: true },
  { key: "mean_reversion", label: "MR", numeric: true },
];

function fmtNum(v: unknown, digits = 2): string {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return n.toFixed(digits);
}

function fmtPct(v: unknown): string {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  if (!Number.isFinite(n)) return "—";
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

function pctClass(v: unknown): string {
  const n = Number(v);
  if (!Number.isFinite(n)) return "text-green-500/40";
  return n >= 0 ? "text-green-400" : "text-red-400";
}

export function ScreenerResults({ results }: Props) {
  const [sortKey, setSortKey] = useState<SortKey>("score");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  const sorted = useMemo(() => {
    const copy = [...results];
    copy.sort((a, b) => {
      const av = (a as Record<string, unknown>)[sortKey];
      const bv = (b as Record<string, unknown>)[sortKey];
      if (typeof av === "string" && typeof bv === "string") {
        return sortDir === "asc"
          ? av.localeCompare(bv)
          : bv.localeCompare(av);
      }
      const an = Number(av);
      const bn = Number(bv);
      const aF = Number.isFinite(an) ? an : -Infinity;
      const bF = Number.isFinite(bn) ? bn : -Infinity;
      return sortDir === "asc" ? aF - bF : bF - aF;
    });
    return copy;
  }, [results, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "ticker" ? "asc" : "desc");
    }
  }

  if (results.length === 0) {
    return (
      <div className="text-green-500/60 text-xs uppercase border border-green-500/40 p-3">
        {`> NO RESULTS — run the screener to populate`}
      </div>
    );
  }

  return (
    <div className="border border-green-500/40 overflow-x-auto">
      <table className="w-full text-xs">
        <thead className="sticky top-0 bg-black border-b border-green-500/40">
          <tr>
            {COLUMNS.map((c) => (
              <th
                key={c.key}
                className={clsx(
                  "px-2 py-1 uppercase text-left text-green-400 cursor-pointer select-none",
                  c.numeric && "text-right",
                )}
                onClick={() => toggleSort(c.key)}
              >
                {c.label}
                {sortKey === c.key && (
                  <span className="ml-1">{sortDir === "asc" ? "▲" : "▼"}</span>
                )}
              </th>
            ))}
            <th className="px-2 py-1 uppercase text-left text-green-400">
              BEST STRAT
            </th>
            <th
              className="px-2 py-1 uppercase text-right text-green-400 cursor-pointer"
              onClick={() => toggleSort("vs_voo")}
            >
              vs VOO
              {sortKey === "vs_voo" && (
                <span className="ml-1">{sortDir === "asc" ? "▲" : "▼"}</span>
              )}
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((r) => (
            <tr
              key={r.ticker}
              className="border-b border-green-500/10 hover:bg-green-500/5"
            >
              <td className="px-2 py-1 uppercase text-green-300">
                {r.ticker}
              </td>
              <td className="px-2 py-1 text-right">{fmtNum(r.price)}</td>
              <td
                className={clsx("px-2 py-1 text-right", pctClass(r.ret_7d))}
              >
                {fmtPct(r.ret_7d)}
              </td>
              <td className="px-2 py-1 text-right">{fmtNum(r.score, 2)}</td>
              <td className="px-2 py-1 text-right">
                {fmtNum(r.momentum, 2)}
              </td>
              <td className="px-2 py-1 text-right">
                {fmtNum(r.breakout, 2)}
              </td>
              <td className="px-2 py-1 text-right">
                {fmtNum(r.volume, 2)}
              </td>
              <td className="px-2 py-1 text-right">{fmtNum(r.rs, 2)}</td>
              <td className="px-2 py-1 text-right">
                {fmtNum(r.mean_reversion, 2)}
              </td>
              <td className="px-2 py-1 uppercase">
                {String(r.best_strategy ?? "—")}
              </td>
              <td
                className={clsx("px-2 py-1 text-right", pctClass(r.vs_voo))}
              >
                {fmtPct(r.vs_voo)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

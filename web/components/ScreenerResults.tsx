"use client";

import clsx from "clsx";
import { useMemo, useState } from "react";
import type { ScreenerResultRow } from "@/lib/api";

type Props = {
  results: ScreenerResultRow[];
  loading?: boolean;
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

const COLUMNS: {
  key: SortKey;
  label: string;
  numeric: boolean;
  title: string;
}[] = [
  { key: "ticker", label: "TICKER", numeric: false, title: "Ticker symbol" },
  { key: "price", label: "PRICE", numeric: true, title: "Latest close price" },
  { key: "ret_7d", label: "7D%", numeric: true, title: "7-day price change" },
  {
    key: "score",
    label: "SCORE",
    numeric: true,
    title: "Weighted composite (all agents)",
  },
  {
    key: "momentum",
    label: "MOM",
    numeric: true,
    title: "Momentum agent score (0-100)",
  },
  {
    key: "breakout",
    label: "BRK",
    numeric: true,
    title: "Breakout agent score",
  },
  {
    key: "volume",
    label: "VOL",
    numeric: true,
    title: "Volume Surge agent score",
  },
  { key: "rs", label: "RS", numeric: true, title: "Relative Strength score" },
  {
    key: "mean_reversion",
    label: "MR",
    numeric: true,
    title: "Mean Reversion score",
  },
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
  if (!Number.isFinite(n)) return "text-b7-green-muted";
  return n >= 0 ? "text-b7-green" : "text-red-400";
}

function SkeletonRow() {
  return (
    <tr
      className="border-b border-green-500/10 animate-pulse"
      data-testid="screener-skeleton-row"
    >
      {Array.from({ length: 11 }).map((_, i) => (
        <td key={i} className="py-2 px-3">
          <span className="block h-3 bg-green-500/10 rounded-sm" />
        </td>
      ))}
    </tr>
  );
}

export function ScreenerResults({ results, loading = false }: Props) {
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

  if (loading) {
    return (
      <div className="border border-b7-green-border overflow-x-auto">
        <div className="overflow-x-auto">
          <table className="w-full text-xs" data-testid="screener-loading">
            <thead className="sticky top-0 bg-black border-b border-b7-green-border">
              <tr>
                {COLUMNS.map((c) => (
                  <th
                    key={c.key}
                    title={c.title}
                    className={clsx(
                      "py-2 px-3 uppercase text-left text-b7-green",
                      c.numeric && "text-right",
                    )}
                  >
                    {c.label}
                  </th>
                ))}
                <th
                  className="py-2 px-3 uppercase text-left text-b7-green"
                  title="Highest-scoring agent for this stock"
                >
                  BEST STRAT
                </th>
                <th
                  className="py-2 px-3 uppercase text-right text-b7-green"
                  title="Alpha vs S&P 500 over 7 days"
                >
                  vs VOO
                </th>
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 5 }).map((_, i) => (
                <SkeletonRow key={i} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="text-b7-green-muted text-xs uppercase border border-b7-green-border p-3">
        {`> NO RESULTS — run the screener to populate`}
      </div>
    );
  }

  return (
    <div className="border border-b7-green-border overflow-x-auto">
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-black border-b border-b7-green-border">
            <tr>
              {COLUMNS.map((c) => (
                <th
                  key={c.key}
                  title={c.title}
                  className={clsx(
                    "py-2 px-3 uppercase text-left text-b7-green cursor-pointer select-none",
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
              <th
                className="py-2 px-3 uppercase text-left text-b7-green"
                title="Highest-scoring agent for this stock"
              >
                BEST STRAT
              </th>
              <th
                className="py-2 px-3 uppercase text-right text-b7-green cursor-pointer"
                title="Alpha vs S&P 500 over 7 days"
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
                className="border-b border-green-500/10 even:bg-green-950/10 hover:bg-green-500/5"
              >
                <td className="py-2 px-3 uppercase text-b7-green-dim">
                  {r.ticker}
                </td>
                <td className="py-2 px-3 text-right">{fmtNum(r.price)}</td>
                <td
                  className={clsx("py-2 px-3 text-right", pctClass(r.ret_7d))}
                >
                  {fmtPct(r.ret_7d)}
                </td>
                <td className="py-2 px-3 text-right">{fmtNum(r.score, 2)}</td>
                <td className="py-2 px-3 text-right">
                  {fmtNum(r.momentum, 2)}
                </td>
                <td className="py-2 px-3 text-right">
                  {fmtNum(r.breakout, 2)}
                </td>
                <td className="py-2 px-3 text-right">
                  {fmtNum(r.volume, 2)}
                </td>
                <td className="py-2 px-3 text-right">{fmtNum(r.rs, 2)}</td>
                <td className="py-2 px-3 text-right">
                  {fmtNum(r.mean_reversion, 2)}
                </td>
                <td className="py-2 px-3 uppercase">
                  {String(r.best_strategy ?? "—")}
                </td>
                <td
                  className={clsx("py-2 px-3 text-right", pctClass(r.vs_voo))}
                >
                  {fmtPct(r.vs_voo)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

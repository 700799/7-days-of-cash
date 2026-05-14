"use client";

import clsx from "clsx";
import type { Mover } from "@/lib/api";

type Props = { mover: Mover };

function arrowFor(change: number | null | undefined): {
  glyph: "▲" | "▼" | "▬";
  klass: string;
} {
  if (change === null || change === undefined || !Number.isFinite(change)) {
    return { glyph: "▬", klass: "text-b7-green-muted" };
  }
  if (change > 0) return { glyph: "▲", klass: "text-b7-green" };
  if (change < 0) return { glyph: "▼", klass: "text-red-400" };
  return { glyph: "▬", klass: "text-b7-green-muted" };
}

function fmtPct(v: number | null | undefined): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`;
}

function fmtPrice(v: number | null | undefined): string {
  if (v === null || v === undefined || !Number.isFinite(v)) return "—";
  return `$${v.toFixed(2)}`;
}

export function MoverBullet({ mover }: Props) {
  const { glyph, klass } = arrowFor(mover.change_7d);
  const firstHeadline = mover.headlines?.[0];
  const link = firstHeadline?.link;

  const symbolContent = (
    <span className="font-bold text-b7-green uppercase tracking-wider">
      {mover.symbol}
    </span>
  );

  return (
    <div className="flex flex-col gap-1 py-1" data-testid={`mover-${mover.symbol}`}>
      <div className="flex items-baseline gap-2 text-xs">
        <span className="text-b7-green-muted">•</span>
        <span
          aria-label={
            mover.change_7d == null
              ? "flat"
              : mover.change_7d > 0
                ? "up"
                : mover.change_7d < 0
                  ? "down"
                  : "flat"
          }
          data-testid={`arrow-${mover.symbol}`}
          className={clsx("text-sm", klass)}
        >
          {glyph}
        </span>
        {link ? (
          <a
            href={link}
            target="_blank"
            rel="noopener noreferrer"
            className="hover:underline"
            data-testid={`mover-link-${mover.symbol}`}
          >
            {symbolContent}
          </a>
        ) : (
          symbolContent
        )}
        <span
          className={clsx(
            "uppercase",
            (mover.change_7d ?? 0) >= 0 ? "text-b7-green" : "text-red-400",
          )}
        >
          {fmtPct(mover.change_7d)}
        </span>
        <span className="text-b7-green-muted uppercase">over 7d</span>
        <span className="text-b7-green-muted">({fmtPrice(mover.price)})</span>
      </div>
      {mover.summary && (
        <div className="text-b7-green-dim text-xs pl-6 leading-relaxed">
          {mover.summary}
        </div>
      )}
    </div>
  );
}

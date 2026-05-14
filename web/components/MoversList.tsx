"use client";

import { useMovers } from "@/lib/hooks";
import { MoverBullet } from "./MoverBullet";

type Props = {
  symbols: string[];
};

function SkeletonBullet() {
  return (
    <div className="flex flex-col gap-1 py-1 animate-pulse">
      <div className="flex items-baseline gap-2 text-xs">
        <span className="text-green-500/30">•</span>
        <span className="text-green-500/30">▬</span>
        <span className="h-3 w-12 bg-green-500/20 inline-block" />
        <span className="h-3 w-10 bg-green-500/10 inline-block" />
      </div>
      <div className="pl-6 h-3 w-3/4 bg-green-500/10" />
    </div>
  );
}

export function MoversList({ symbols }: Props) {
  const { movers, loading, error } = useMovers(symbols);

  return (
    <section
      className="border border-b7-green-border p-3 space-y-2"
      data-testid="movers-list"
    >
      <h2 className="text-b7-green uppercase text-sm">{`> WHY THEY MOVED`}</h2>

      {symbols.length === 0 && (
        <div className="text-b7-green-muted text-xs uppercase">
          {`> No symbols to analyze yet.`}
        </div>
      )}

      {symbols.length > 0 && loading && (
        <div className="space-y-1" data-testid="movers-loading">
          <SkeletonBullet />
          <SkeletonBullet />
          <SkeletonBullet />
        </div>
      )}

      {symbols.length > 0 && error && (
        <div className="text-red-400 text-xs uppercase">
          {`! Failed to load movers`}
        </div>
      )}

      {symbols.length > 0 && !loading && !error && movers.length === 0 && (
        <div className="text-green-500/60 text-xs uppercase">
          {`> No movers to display.`}
        </div>
      )}

      {!loading && movers.length > 0 && (
        <div className="space-y-1">
          {movers.map((m) => (
            <MoverBullet key={m.symbol} mover={m} />
          ))}
        </div>
      )}
    </section>
  );
}

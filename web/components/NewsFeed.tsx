"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import { useMemo, useState } from "react";
import { useMarketNews, useTickerNews } from "@/lib/hooks";
import { NewsCard } from "./NewsCard";

type Props = {
  watchlist: string[];
  resultTickers: string[];
};

function MarketSection() {
  const { news, loading, error } = useMarketNews();
  return (
    <section className="space-y-2">
      <h3 className="text-green-400 uppercase text-sm">{`> MARKET NEWS`}</h3>
      {loading && (
        <div className="text-green-500/60 text-xs uppercase">loading…</div>
      )}
      {error && (
        <div className="text-red-400 text-xs uppercase">! failed to load</div>
      )}
      {!loading && !error && news.length === 0 && (
        <div className="text-green-500/60 text-xs uppercase">no news</div>
      )}
      <div className="grid sm:grid-cols-2 gap-2">
        {news.map((n, i) => (
          <NewsCard key={`${n.link}-${i}`} item={n} />
        ))}
      </div>
    </section>
  );
}

function TickerSection({
  symbol,
  defaultOpen,
}: {
  symbol: string;
  defaultOpen: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const { news, loading, error } = useTickerNews(open ? symbol : null);

  return (
    <section className="border border-green-500/30">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="w-full flex items-center justify-between px-2 py-1 text-green-400 uppercase text-sm hover:bg-green-500/5"
      >
        <span>{`> NEWS — ${symbol}`}</span>
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
      </button>
      {open && (
        <div className="p-2 space-y-2">
          {loading && (
            <div className="text-green-500/60 text-xs uppercase">loading…</div>
          )}
          {error && (
            <div className="text-red-400 text-xs uppercase">
              ! failed to load
            </div>
          )}
          {!loading && !error && news.length === 0 && (
            <div className="text-green-500/60 text-xs uppercase">no news</div>
          )}
          <div className="grid sm:grid-cols-2 gap-2">
            {news.map((n, i) => (
              <NewsCard key={`${n.link}-${i}`} item={n} />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

export function NewsFeed({ watchlist, resultTickers }: Props) {
  const symbols = useMemo(() => {
    const set = new Set<string>();
    for (const s of watchlist) set.add(s.toUpperCase());
    for (const s of resultTickers) set.add(s.toUpperCase());
    return Array.from(set);
  }, [watchlist, resultTickers]);

  return (
    <div className="space-y-4">
      <MarketSection />
      <div className="space-y-2">
        {symbols.map((sym, i) => (
          <TickerSection key={sym} symbol={sym} defaultOpen={i < 3} />
        ))}
      </div>
    </div>
  );
}

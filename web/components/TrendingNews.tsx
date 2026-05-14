"use client";

import { useTrendingNews } from "@/lib/hooks";
import { NewsCard } from "./NewsCard";

export function TrendingNews() {
  const { news, loading, error } = useTrendingNews();

  return (
    <section
      className="border border-green-500/40 p-3 space-y-2"
      data-testid="trending-news"
    >
      <h2 className="text-green-400 uppercase text-sm">
        {`> TRENDING MARKET NEWS — TOP 5`}
      </h2>

      {loading && (
        <div className="text-green-500/60 text-xs uppercase">loading…</div>
      )}

      {error && (
        <div className="text-red-400 text-xs uppercase">
          {`! Failed to load trending news`}
        </div>
      )}

      {!loading && !error && news.length === 0 && (
        <div className="text-green-500/60 text-xs uppercase">
          {`> No trending stories right now.`}
        </div>
      )}

      {news.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
          {news.slice(0, 5).map((n, i) => (
            <NewsCard key={`${n.link}-${i}`} item={n} />
          ))}
        </div>
      )}
    </section>
  );
}

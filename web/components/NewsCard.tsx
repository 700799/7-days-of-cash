import Image from "next/image";
import { formatDistanceToNow, parseISO } from "date-fns";
import type { NewsItem } from "@/lib/api";

type Props = { item: NewsItem };

function relativeTime(iso: string): string {
  try {
    const d = parseISO(iso);
    if (Number.isNaN(d.getTime())) return iso;
    return `${formatDistanceToNow(d)} ago`;
  } catch {
    return iso;
  }
}

export function NewsCard({ item }: Props) {
  return (
    <article className="border border-green-500/30 p-2 flex gap-3 hover:bg-green-500/5">
      {item.thumbnail && (
        <div className="relative w-16 h-16 shrink-0 border border-green-500/30 overflow-hidden">
          <Image
            src={item.thumbnail}
            alt=""
            fill
            sizes="64px"
            className="object-cover"
            unoptimized
          />
        </div>
      )}
      <div className="flex flex-col gap-1 min-w-0">
        <a
          href={item.link}
          target="_blank"
          rel="noopener noreferrer"
          className="text-b7-green-dim hover:text-b7-green underline-offset-2 hover:underline text-sm truncate"
        >
          {item.title}
        </a>
        <div className="flex items-center gap-2 text-xs text-b7-green-muted uppercase">
          <span>{item.publisher}</span>
          <span>·</span>
          <span>{relativeTime(item.published_at)}</span>
        </div>
      </div>
    </article>
  );
}

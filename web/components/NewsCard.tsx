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
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={item.thumbnail}
          alt=""
          className="w-16 h-16 object-cover border border-green-500/30 shrink-0"
        />
      )}
      <div className="flex flex-col gap-1 min-w-0">
        <a
          href={item.link}
          target="_blank"
          rel="noopener noreferrer"
          className="text-green-300 hover:text-green-200 underline-offset-2 hover:underline text-sm truncate"
        >
          {item.title}
        </a>
        <div className="flex items-center gap-2 text-[10px] text-green-500/70 uppercase">
          <span>{item.publisher}</span>
          <span>·</span>
          <span>{relativeTime(item.published_at)}</span>
        </div>
      </div>
    </article>
  );
}

import clsx from "clsx";
import type { Benchmark } from "@/lib/api";

type Props = {
  benchmarks: Benchmark[];
};

const ORDER = ["VOO", "QQQ", "VXF", "IWM", "VTIAX", "GLD", "TLT"];

export function BenchmarkBar({ benchmarks }: Props) {
  const map = new Map(benchmarks.map((b) => [b.symbol.toUpperCase(), b]));
  const ordered = ORDER.map((sym) => map.get(sym)).filter(
    (b): b is Benchmark => Boolean(b),
  );
  const extras = benchmarks.filter(
    (b) => !ORDER.includes(b.symbol.toUpperCase()),
  );
  const all = [...ordered, ...extras];

  return (
    <div className="border border-b7-green-border/40 bg-black flex flex-wrap items-stretch">
      <div className="px-3 py-1 border-r border-b7-green-border/40 flex items-center text-b7-green-dim uppercase text-xs">
        {`> BENCH 7D`}
      </div>
      {all.length === 0 && (
        <div className="px-3 py-1 text-b7-green-muted text-xs uppercase">
          no data
        </div>
      )}
      {all.map((b) => {
        const positive = b.ret_7d >= 0;
        return (
          <div
            key={b.symbol}
            className="flex items-center gap-2 px-3 py-1 border-r border-green-500/20 last:border-r-0"
          >
            <span className="text-b7-green-dim uppercase text-xs">
              {b.symbol}
            </span>
            <span
              className={clsx(
                "text-xs",
                positive ? "text-b7-green-dim" : "text-red-400",
              )}
            >
              {`${positive ? "+" : ""}${b.ret_7d.toFixed(2)}%`}
            </span>
          </div>
        );
      })}
    </div>
  );
}

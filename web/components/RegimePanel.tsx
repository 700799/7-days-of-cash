import type { Regime } from "@/lib/api";

type Props = {
  regime: Regime | null;
};

function Cell({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="flex flex-col gap-0.5 px-3 py-1 min-h-[80px] justify-center border-r border-green-500/20 last:border-r-0">
      <span className="text-b7-green-muted uppercase text-xs">{label}</span>
      <span className="text-b7-green-dim uppercase text-sm">
        {value ? String(value) : "—"}
      </span>
    </div>
  );
}

export function RegimePanel({ regime }: Props) {
  return (
    <div className="border border-green-500/40 bg-black flex flex-wrap items-stretch">
      <div className="px-3 py-1 border-r border-green-500/40 flex items-center text-green-400 uppercase text-xs">
        {`> REGIME`}
      </div>
      <Cell label="trend" value={regime?.trend} />
      <Cell label="risk" value={regime?.risk} />
      <Cell label="leadership" value={regime?.leadership} />
    </div>
  );
}

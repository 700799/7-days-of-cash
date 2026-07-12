import { HerdBadge } from "./HerdBadge";

const MEANINGS: [string, string][] = [
  ["EARLY", "uptrend forming, money flowing in, not stretched"],
  ["ACCELERATING", "strong week with volume/flow confirmation"],
  ["CROWDED", "3+ ATRs stretched, RSI 78+/MFI 85+, or climax volume"],
  ["DISTRIBUTION", "2+ selling-pressure signals while price holds up"],
  ["NEUTRAL", "no dominant crowd signal"],
];

export function HerdLegend() {
  return (
    <div className="legend" aria-label="Herd state legend">
      {MEANINGS.map(([state, meaning]) => (
        <div key={state}>
          <HerdBadge state={state} />
          <span>{meaning}</span>
        </div>
      ))}
    </div>
  );
}

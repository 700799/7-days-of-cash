const TOOLTIPS: Record<string, string> = {
  EARLY: "Uptrend forming, money flowing in, not stretched: crowd starting to arrive",
  ACCELERATING: "Strong week with volume/flow confirmation: crowd piling in",
  CROWDED: "3+ ATRs stretched, RSI 78+/MFI 85+, or climax volume: late-stage crowd",
  DISTRIBUTION: "2+ selling-pressure signals while price holds up: crowd leaving",
  NEUTRAL: "No dominant crowd signal",
};

// Lifecycle position, used only to pick the flip arrow direction.
const RANK: Record<string, number> = {
  NEUTRAL: 0,
  EARLY: 1,
  ACCELERATING: 2,
  CROWDED: 3,
  DISTRIBUTION: 4,
};

export function HerdBadge({ state, prev }: { state: string | null; prev?: string | null }) {
  const known = state !== null && state in TOOLTIPS;
  const label = known ? state : "—";
  const slug = known ? state.toLowerCase() : "neutral";
  const title = known ? TOOLTIPS[state] : "No herd data for this run";

  const flipped = known && prev != null && prev !== state && prev in RANK;
  const arrow = flipped ? (RANK[state] > RANK[prev] ? "↑" : RANK[state] < RANK[prev] ? "↓" : "→") : null;

  return (
    <>
      <span className={`badge hs-${slug}`} title={title} aria-label={known ? `herd state: ${state}` : "no herd data"}>
        {label}
      </span>
      {flipped && (
        <span className="flip" aria-label={`herd state changed from ${prev}`}>
          {arrow} was {prev}
        </span>
      )}
    </>
  );
}

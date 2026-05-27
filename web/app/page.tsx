import { getLatestRun, getResults, type Result } from "@/lib/db";

export const dynamic = "force-dynamic";

function pct(v: number | null): string {
  if (v === null) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

function fmt(v: number | null, digits = 2): string {
  return v === null ? "—" : v.toFixed(digits);
}

function cls(v: number | null): string {
  if (v === null) return "";
  return v >= 0 ? "pos" : "neg";
}

export default async function Page() {
  let run: Awaited<ReturnType<typeof getLatestRun>> = null;
  let results: Result[] = [];
  let error: string | null = null;

  try {
    run = await getLatestRun();
    if (run) results = await getResults(run.id);
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <main>
      <h1>&gt; BEST 7 DAYS — MULA</h1>
      <div className="sub">Multi-agent 7-day uptrend stock screener</div>

      {error && (
        <div className="error">
          Could not load data: {error}
          <br />
          Set <code>DATABASE_URL</code> and let the screener cron write a run.
        </div>
      )}

      {!error && !run && (
        <div className="empty">
          No screener runs yet. The first scheduled run will populate this board.
        </div>
      )}

      {!error && run && (
        <>
          <div className="meta">
            <span>
              <span className="k">Updated: </span>
              {new Date(run.run_at).toUTCString()}
            </span>
            <span>
              <span className="k">Leaders: </span>
              {run.result_count}
            </span>
            <span>
              <span className="k">Scanned: </span>
              {run.universe_size.toLocaleString()}
            </span>
            {run.regime?.trend && <span className="badge">trend: {run.regime.trend}</span>}
            {run.regime?.risk && <span className="badge">risk: {run.regime.risk}</span>}
            {run.regime?.leadership && (
              <span className="badge">lead: {run.regime.leadership}</span>
            )}
          </div>

          {results.length === 0 ? (
            <div className="empty">Last run found no leaders passing the filters.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th className="l">Ticker</th>
                  <th>Price</th>
                  <th>7d</th>
                  <th>5d</th>
                  <th>20d</th>
                  <th>RelVol</th>
                  <th>RSI</th>
                  <th>Score</th>
                  <th className="l">Strategy</th>
                  <th className="l">Reasons</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r) => (
                  <tr key={r.rank}>
                    <td>{r.rank}</td>
                    <td className="l ticker">{r.ticker}</td>
                    <td>{fmt(r.price)}</td>
                    <td className={cls(r.change_7d)}>{pct(r.change_7d)}</td>
                    <td className={cls(r.change_5d)}>{pct(r.change_5d)}</td>
                    <td className={cls(r.change_20d)}>{pct(r.change_20d)}</td>
                    <td>{fmt(r.rel_vol)}</td>
                    <td>{fmt(r.rsi_14, 1)}</td>
                    <td>{fmt(r.composite_score, 1)}</td>
                    <td className="l">{r.best_strategy ?? "—"}</td>
                    <td className="l reasons">{r.top_reasons || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </main>
  );
}

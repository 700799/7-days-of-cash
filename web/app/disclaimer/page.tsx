import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Disclaimer",
  description:
    "Best7DaysMula is not financial advice. Read the full disclaimer before using the screener.",
  alternates: { canonical: "/disclaimer" },
};

export default function DisclaimerPage() {
  return (
    <main className="prose">
      <h1>&gt; DISCLAIMER</h1>

      <h2>Not financial advice</h2>
      <p>
        Best7DaysMula is a software tool that surfaces statistical patterns in publicly
        available US equity market data. Nothing on this site constitutes investment,
        financial, legal, tax, or other professional advice. The operators of this site are
        not registered investment advisors, broker-dealers, or financial planners.
      </p>

      <h2>No guarantee of accuracy</h2>
      <p>
        Market data is sourced from third-party providers (Yahoo Finance via yfinance) and
        may be delayed, incomplete, or inaccurate. We make no representations or warranties
        about the accuracy, completeness, or timeliness of any data shown. Computed metrics
        (RSI, relative volume, composite scores) are the output of automated heuristics and
        may contain errors.
      </p>

      <h2>Past performance is not predictive</h2>
      <p>
        Stocks identified as "leaders" or assigned high composite scores have shown strength
        over a recent lookback window. Past price action does not predict future returns.
        Strong recent gainers frequently underperform going forward; this is widely
        documented in academic finance and is not a defect of this screener.
      </p>

      <h2>You can lose money</h2>
      <p>
        Trading equities involves substantial risk, including total loss of capital.
        Short-term momentum strategies in particular carry elevated risk of sudden reversal.
        Never invest money you cannot afford to lose. Consult a qualified, independent
        financial advisor before making investment decisions.
      </p>

      <h2>No fiduciary relationship</h2>
      <p>
        Use of this site does not create any advisory, fiduciary, or professional
        relationship between you and the operators of this site.
      </p>

      <h2>Use at your own risk</h2>
      <p>
        You are solely responsible for any decisions you make based on information from this
        site. The operators disclaim all liability for any losses, damages, or claims
        arising from use of, or reliance on, content shown here.
      </p>
    </main>
  );
}

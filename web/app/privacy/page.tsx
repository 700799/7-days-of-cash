import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Privacy",
  description: "Privacy policy for Best7DaysMula.",
  alternates: { canonical: "/privacy" },
};

export default function PrivacyPage() {
  return (
    <main className="prose">
      <h1>&gt; PRIVACY</h1>

      <h2>What we collect</h2>
      <p>
        Best7DaysMula is a read-only public dashboard. We do not require accounts and do not
        ask you for personal information. The only data we process is the data publicly
        scraped from market data providers (Yahoo Finance, Wikipedia ticker lists) about
        publicly traded companies.
      </p>

      <h2>Server logs</h2>
      <p>
        Our hosting provider (Vercel) automatically records standard request metadata
        (IP address, user-agent, requested path, response status, timestamp) for operational
        purposes including security, abuse prevention, and performance debugging. These logs
        are retained per Vercel's standard retention policy and are not sold, shared, or
        used for marketing.
      </p>

      <h2>Cookies</h2>
      <p>
        We do not set any tracking, advertising, or analytics cookies. The site may use
        strictly necessary cookies set by the hosting platform (Vercel) for security and
        load balancing.
      </p>

      <h2>Watchlist</h2>
      <p>
        If a watchlist feature is enabled, your saved tickers are stored in your browser's
        local storage and never transmitted to our servers.
      </p>

      <h2>Third parties</h2>
      <p>
        Stock data is sourced from Yahoo Finance and Wikipedia. Visiting external links from
        this site is governed by those sites' own privacy policies.
      </p>

      <h2>Contact</h2>
      <p>
        For privacy questions or data requests, open an issue at{" "}
        <a
          href="https://github.com/700799/7-days-of-cash/issues"
          target="_blank"
          rel="noopener noreferrer"
        >
          github.com/700799/7-days-of-cash/issues
        </a>
        .
      </p>
    </main>
  );
}

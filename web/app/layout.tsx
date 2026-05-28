import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import "./globals.css";

const siteUrl =
  process.env.NEXT_PUBLIC_SITE_URL ??
  (process.env.VERCEL_PROJECT_PRODUCTION_URL
    ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`
    : "http://localhost:3000");

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: {
    default: "Best 7 Days — Mula",
    template: "%s — Best 7 Days Mula",
  },
  description:
    "Multi-agent 7-day uptrend stock screener. Volume-confirmed, benchmark-compared, refreshed every 30 minutes during US market hours.",
  applicationName: "Best 7 Days Mula",
  keywords: [
    "stock screener",
    "7-day uptrend",
    "momentum stocks",
    "relative strength",
    "volume surge",
    "S&P 500 screener",
  ],
  authors: [{ name: "Best7DaysMula contributors" }],
  openGraph: {
    type: "website",
    siteName: "Best 7 Days Mula",
    title: "Best 7 Days — Mula",
    description:
      "Find stocks trending strongly upward over the last 7 trading days, confirmed by rising volume.",
    url: siteUrl,
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "Best 7 Days — Mula",
    description:
      "Find stocks trending strongly upward over the last 7 trading days, confirmed by rising volume.",
  },
  robots: { index: true, follow: true },
  alternates: { canonical: "/" },
};

export const viewport: Viewport = {
  themeColor: "#000000",
  colorScheme: "dark",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        {children}
        <footer className="site-footer">
          <p className="disclaimer">
            <strong>Not financial advice.</strong> Educational and informational use only.
            Past performance does not predict future results. Always do your own research.
          </p>
          <nav aria-label="Footer">
            <Link href="/">Leaderboard</Link>
            <Link href="/disclaimer">Disclaimer</Link>
            <Link href="/privacy">Privacy</Link>
            <Link href="/terms">Terms</Link>
            <a
              href="https://github.com/700799/7-days-of-cash"
              target="_blank"
              rel="noopener noreferrer"
            >
              Source
            </a>
          </nav>
        </footer>
      </body>
    </html>
  );
}

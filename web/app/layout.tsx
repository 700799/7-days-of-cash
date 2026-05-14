import type { Metadata, Viewport } from "next";
import { JetBrains_Mono } from "next/font/google";
import { AuthProvider } from "@/components/AuthProvider";
import "./globals.css";

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Best7DaysMula — 7-day uptrend screener",
  description:
    "Find the strongest 7-day uptrends. Volume-confirmed. Multi-agent scored. Refreshed every 4 hours.",
  openGraph: {
    title: "Best7DaysMula — 7-day uptrend screener",
    description:
      "Find the strongest 7-day uptrends. Volume-confirmed. Multi-agent scored. Refreshed every 4 hours.",
    type: "website",
  },
  twitter: { card: "summary" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#000000",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body
        className={`${mono.variable} font-mono bg-black text-b7-green min-h-screen`}
      >
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}

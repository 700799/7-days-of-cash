import type { Metadata } from "next";
import { AuthProvider } from "@/components/AuthProvider";
import "./globals.css";

export const metadata: Metadata = {
  title: "BEST 7 DAYS MULA",
  description:
    "Multi-agent stock screener for short-term uptrends with volume confirmation.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-black text-green-400 font-mono min-h-screen">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}

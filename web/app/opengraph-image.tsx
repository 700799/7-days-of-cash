import { ImageResponse } from "next/og";

export const runtime = "edge";
export const alt = "Best 7 Days Mula — multi-agent 7-day uptrend stock screener";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "flex-start",
          background: "#000000",
          color: "#19ff19",
          fontFamily: "monospace",
          padding: "80px",
        }}
      >
        <div style={{ fontSize: 28, color: "#0a0", letterSpacing: "0.2em" }}>
          $ python main.py
        </div>
        <div
          style={{
            fontSize: 120,
            fontWeight: 800,
            lineHeight: 1.05,
            marginTop: 24,
            letterSpacing: "-0.02em",
          }}
        >
          BEST 7 DAYS
        </div>
        <div
          style={{
            fontSize: 120,
            fontWeight: 800,
            lineHeight: 1.05,
            letterSpacing: "-0.02em",
          }}
        >
          MULA.
        </div>
        <div style={{ fontSize: 36, color: "#0a0", marginTop: 40 }}>
          Multi-agent 7-day uptrend screener
        </div>
        <div
          style={{
            display: "flex",
            gap: 16,
            marginTop: 32,
            fontSize: 22,
            color: "#19ff19",
          }}
        >
          <span style={{ border: "1px solid #0a4d0a", padding: "6px 14px" }}>
            volume-confirmed
          </span>
          <span style={{ border: "1px solid #0a4d0a", padding: "6px 14px" }}>
            benchmark-compared
          </span>
          <span style={{ border: "1px solid #0a4d0a", padding: "6px 14px" }}>
            refreshed every 30m
          </span>
        </div>
      </div>
    ),
    size,
  );
}

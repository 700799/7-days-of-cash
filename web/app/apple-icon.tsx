import { ImageResponse } from "next/og";

export const runtime = "edge";
export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "#000000",
          color: "#19ff19",
          fontFamily: "monospace",
        }}
      >
        <div style={{ fontSize: 100, fontWeight: 900, lineHeight: 1 }}>7d</div>
        <div style={{ fontSize: 20, marginTop: 6, color: "#0a0" }}>MULA</div>
      </div>
    ),
    size,
  );
}

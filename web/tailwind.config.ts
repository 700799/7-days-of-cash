import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "b7-green": {
          DEFAULT: "#22ff88",
          dim: "#8aff9f",
          muted: "#6acc7e",
          border: "#00d65a",
        },
        gstack: {
          bg: "#000000",
          primary: "#22ff88",
          dim: "#00b85c",
        },
      },
      fontFamily: {
        mono: [
          "var(--font-mono)",
          "ui-monospace",
          "SFMono-Regular",
          "Menlo",
          "Monaco",
          "Consolas",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
};

export default config;

import { describe, it, expect } from "vitest";
import { TickerPills } from "@/components/TickerPills";

describe("TickerPills — Default Tickers", () => {
  it("component exports correctly", () => {
    expect(TickerPills).toBeDefined();
    expect(typeof TickerPills).toBe("function");
  });
});

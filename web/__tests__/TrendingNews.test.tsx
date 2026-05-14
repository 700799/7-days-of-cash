import { describe, it, expect } from "vitest";
import { TrendingNews } from "@/components/TrendingNews";

describe("TrendingNews", () => {
  it("component exports correctly", () => {
    expect(TrendingNews).toBeDefined();
    expect(typeof TrendingNews).toBe("function");
  });
});

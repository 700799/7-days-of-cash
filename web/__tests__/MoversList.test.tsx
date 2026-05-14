import { describe, it, expect } from "vitest";
import { MoversList } from "@/components/MoversList";

describe("MoversList", () => {
  it("component exports correctly", () => {
    expect(MoversList).toBeDefined();
    expect(typeof MoversList).toBe("function");
  });
});

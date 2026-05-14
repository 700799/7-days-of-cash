import { describe, it, expect } from "vitest";
import { MoverBullet } from "@/components/MoverBullet";

describe("MoverBullet", () => {
  it("component exports correctly", () => {
    expect(MoverBullet).toBeDefined();
    expect(typeof MoverBullet).toBe("function");
  });
});

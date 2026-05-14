import { describe, it, expect } from "vitest";
import { EmailDigestSettings } from "@/components/EmailDigestSettings";

describe("EmailDigestSettings", () => {
  it("component exports correctly", () => {
    expect(EmailDigestSettings).toBeDefined();
    expect(typeof EmailDigestSettings).toBe("function");
  });
});

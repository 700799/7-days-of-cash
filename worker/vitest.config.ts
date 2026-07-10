import { defineConfig } from "vitest/config";

// The engine is pure TypeScript (no Workers APIs), so plain node vitest is
// enough and much faster than workers-pool. Route-level tests that need D1 can
// switch to @cloudflare/vitest-pool-workers via a second project later.
export default defineConfig({
  test: {
    include: ["test/**/*.test.ts"],
    environment: "node",
  },
});

/**
 * Contrast regression test.
 *
 * This test ensures that the Tailwind color palette maintains WCAG AA
 * contrast ratios on the gstack dark background (#000).
 */

import { describe, it, expect } from "vitest";
import tailwindConfig from "../tailwind.config";

describe("Color Contrast (WCAG AA)", () => {
  // Approximate luminance calculation per WCAG
  function getLuminance(hexColor: string): number {
    const hex = hexColor.replace("#", "");
    const r = parseInt(hex.substring(0, 2), 16) / 255;
    const g = parseInt(hex.substring(2, 4), 16) / 255;
    const b = parseInt(hex.substring(4, 6), 16) / 255;

    const luminance = (c: number) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
    return 0.2126 * luminance(r) + 0.7152 * luminance(g) + 0.0722 * luminance(b);
  }

  function getContrastRatio(foreground: string, background: string): number {
    const l1 = getLuminance(foreground);
    const l2 = getLuminance(background);
    const lighter = Math.max(l1, l2);
    const darker = Math.min(l1, l2);
    return (lighter + 0.05) / (darker + 0.05);
  }

  const darkBg = "#000000";
  const config = tailwindConfig as any;
  const colors = config.theme?.extend?.colors || {};

  it("b7-green DEFAULT has >= 4.5:1 contrast (body text minimum)", () => {
    const contrast = getContrastRatio(colors["b7-green"].DEFAULT, darkBg);
    expect(contrast).toBeGreaterThanOrEqual(4.5);
  });

  it("b7-green dim has >= 4.5:1 contrast (secondary text minimum)", () => {
    const contrast = getContrastRatio(colors["b7-green"].dim, darkBg);
    expect(contrast).toBeGreaterThanOrEqual(4.5);
  });

  it("b7-green muted has >= 3:1 contrast (labels OK)", () => {
    const contrast = getContrastRatio(colors["b7-green"].muted, darkBg);
    // Labels can be 3:1 per WCAG
    expect(contrast).toBeGreaterThanOrEqual(3);
  });

  it("new palette has no opacity on body text colors", () => {
    const config_str = JSON.stringify(colors["b7-green"]);
    // Ensure no /80, /90, /60 opacity on body text colors
    expect(config_str).not.toContain("/");
  });

  it("gstack palette colors also defined", () => {
    const gstackColors = colors.gstack;
    expect(gstackColors).toBeDefined();
    expect(gstackColors.bg).toBe("#000000");
  });

  it("font family includes monospace fallbacks", () => {
    const fontFamily = config.theme?.extend?.fontFamily?.mono;
    expect(fontFamily).toBeDefined();
    expect(fontFamily.length).toBeGreaterThan(0);
  });
});

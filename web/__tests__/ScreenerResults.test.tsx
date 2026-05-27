/**
 * Tests for ScreenerResults component.
 *
 * Covers: loading state, empty state, data rendering, sorting,
 * top-row highlighting, copy-to-clipboard, and Yahoo Finance links.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ScreenerResults } from "@/components/ScreenerResults";
import type { ScreenerResultRow } from "@/lib/api";

const FAKE_ROWS: ScreenerResultRow[] = [
  {
    ticker: "NVDA",
    price: 950.12,
    ret_7d: 8.4,
    score: 92.0,
    momentum: 88.0,
    breakout: 85.0,
    volume: 80.0,
    rs: 90.0,
    mean_reversion: 60.0,
    best_strategy: "momentum",
    vs_voo: 5.2,
    change_7d: 8.4,
  },
  {
    ticker: "AAPL",
    price: 210.5,
    ret_7d: 4.1,
    score: 78.0,
    momentum: 72.0,
    breakout: 70.0,
    volume: 65.0,
    rs: 75.0,
    mean_reversion: 55.0,
    best_strategy: "breakout",
    vs_voo: 1.3,
    change_7d: 4.1,
  },
  {
    ticker: "MSFT",
    price: 420.0,
    ret_7d: -1.2,
    score: 55.0,
    momentum: 50.0,
    breakout: 45.0,
    volume: 40.0,
    rs: 52.0,
    mean_reversion: 70.0,
    best_strategy: "mean_reversion",
    vs_voo: -2.1,
    change_7d: -1.2,
  },
];

describe("ScreenerResults — loading state", () => {
  it("shows loading skeleton when loading=true", () => {
    render(<ScreenerResults results={[]} loading={true} />);
    expect(screen.getByTestId("screener-loading")).toBeTruthy();
  });

  it("shows skeleton rows during loading", () => {
    render(<ScreenerResults results={[]} loading={true} />);
    const skeletons = screen.getAllByTestId("screener-skeleton-row");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("does not show data table while loading", () => {
    render(<ScreenerResults results={[]} loading={true} />);
    expect(screen.queryByText("NVDA")).toBeNull();
  });
});

describe("ScreenerResults — empty state", () => {
  it("shows no-results message when results empty and not loading", () => {
    render(<ScreenerResults results={[]} />);
    expect(screen.getByText(/NO RESULTS/i)).toBeTruthy();
  });

  it("no-results message mentions screener frequency", () => {
    render(<ScreenerResults results={[]} />);
    expect(screen.getByText(/4h/i)).toBeTruthy();
  });
});

describe("ScreenerResults — data display", () => {
  it("renders all ticker symbols", () => {
    render(<ScreenerResults results={FAKE_ROWS} />);
    expect(screen.getByText(/NVDA/)).toBeTruthy();
    expect(screen.getByText(/AAPL/)).toBeTruthy();
    expect(screen.getByText(/MSFT/)).toBeTruthy();
  });

  it("renders column headers", () => {
    render(<ScreenerResults results={FAKE_ROWS} />);
    expect(screen.getByText("7D%")).toBeTruthy();
    expect(screen.getByText("SCORE")).toBeTruthy();
    expect(screen.getByText("BEST STRAT")).toBeTruthy();
  });

  it("shows result count in leaders badge", () => {
    render(<ScreenerResults results={FAKE_ROWS} />);
    expect(screen.getByText(/3 leaders/)).toBeTruthy();
  });

  it("renders positive pct with + prefix", () => {
    render(<ScreenerResults results={FAKE_ROWS} />);
    expect(screen.getByText("+8.40%")).toBeTruthy();
  });

  it("renders negative pct without + prefix", () => {
    render(<ScreenerResults results={FAKE_ROWS} />);
    expect(screen.getByText("-1.20%")).toBeTruthy();
  });

  it("top result has star prefix", () => {
    render(<ScreenerResults results={FAKE_ROWS} />);
    expect(screen.getByText(/★ NVDA/)).toBeTruthy();
  });

  it("top result links to Yahoo Finance", () => {
    render(<ScreenerResults results={FAKE_ROWS} />);
    const link = screen.getByTitle("View NVDA on Yahoo Finance");
    expect(link.getAttribute("href")).toContain("finance.yahoo.com");
    expect(link.getAttribute("href")).toContain("NVDA");
  });

  it("links open in new tab", () => {
    render(<ScreenerResults results={FAKE_ROWS} />);
    const link = screen.getByTitle("View NVDA on Yahoo Finance");
    expect(link.getAttribute("target")).toBe("_blank");
  });
});

describe("ScreenerResults — sorting", () => {
  it("clicking score header twice reverses sort", () => {
    render(<ScreenerResults results={FAKE_ROWS} />);
    const scoreHeader = screen.getByTitle("Weighted composite (all agents)");
    // Default is desc by score; click once → asc
    fireEvent.click(scoreHeader);
    // MSFT (55) should now be first if ascending
    const rows = screen.getAllByRole("row");
    // row[0] is header; row[1] is first data row
    expect(rows[1].textContent).toContain("MSFT");
  });

  it("clicking ticker header sorts alphabetically", () => {
    render(<ScreenerResults results={FAKE_ROWS} />);
    const tickerHeader = screen.getByTitle("Ticker symbol");
    fireEvent.click(tickerHeader);
    const rows = screen.getAllByRole("row");
    expect(rows[1].textContent).toContain("AAPL");
  });
});

describe("ScreenerResults — copy symbols", () => {
  beforeEach(() => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  it("copy button is visible", () => {
    render(<ScreenerResults results={FAKE_ROWS} />);
    expect(screen.getByTitle(/copy all ticker/i)).toBeTruthy();
  });

  it("clicking copy button calls clipboard.writeText", async () => {
    render(<ScreenerResults results={FAKE_ROWS} />);
    const btn = screen.getByTitle(/copy all ticker/i);
    fireEvent.click(btn);
    expect(navigator.clipboard.writeText).toHaveBeenCalled();
  });

  it("copy text includes all ticker symbols", async () => {
    render(<ScreenerResults results={FAKE_ROWS} />);
    const btn = screen.getByTitle(/copy all ticker/i);
    fireEvent.click(btn);
    const written = (navigator.clipboard.writeText as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(written).toContain("NVDA");
    expect(written).toContain("AAPL");
    expect(written).toContain("MSFT");
  });
});

import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SWRConfig } from "swr";
import { TickerPills } from "@/components/TickerPills";
import * as api from "@/lib/api";
import type { Ticker } from "@/lib/api";

const tickers: Ticker[] = [
  { symbol: "AAPL", note: null, added_at: "2026-05-01T00:00:00Z" },
  { symbol: "MSFT", note: "cloud", added_at: "2026-05-02T00:00:00Z" },
];

function renderPills(list: Ticker[] = tickers, signedIn = true) {
  return render(
    <SWRConfig value={{ provider: () => new Map() }}>
      <TickerPills tickers={list} signedIn={signedIn} />
    </SWRConfig>,
  );
}

describe("TickerPills", () => {
  it("renders a pill per ticker", () => {
    renderPills();
    expect(screen.getByTestId("pill-AAPL")).toBeInTheDocument();
    expect(screen.getByTestId("pill-MSFT")).toBeInTheDocument();
  });

  it("calls deleteTicker when × is clicked and confirmed", async () => {
    const spy = vi.spyOn(api, "deleteTicker").mockResolvedValue();
    vi.spyOn(window, "confirm").mockReturnValue(true);

    renderPills();
    const user = userEvent.setup();
    await user.click(screen.getByLabelText(/remove AAPL/i));

    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith("AAPL");
    });
  });

  it("shows empty state for signed in users with no tickers", () => {
    renderPills([], true);
    expect(screen.getByText(/add one above/i)).toBeInTheDocument();
  });

  it("shows sign-in prompt for anon users with no tickers", () => {
    renderPills([], false);
    expect(screen.getByText(/sign in to save/i)).toBeInTheDocument();
  });
});

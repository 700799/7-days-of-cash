import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { SWRConfig } from "swr";
import { TickerForm } from "@/components/TickerForm";
import * as api from "@/lib/api";

function renderForm(props: Partial<React.ComponentProps<typeof TickerForm>> = {}) {
  return render(
    <SWRConfig value={{ provider: () => new Map() }}>
      <TickerForm {...props} />
    </SWRConfig>,
  );
}

describe("TickerForm", () => {
  it("calls addTicker with uppercase symbol on submit", async () => {
    const spy = vi
      .spyOn(api, "addTicker")
      .mockResolvedValue({
        symbol: "AAPL",
        note: "buy dip",
        added_at: "2026-05-14T00:00:00Z",
      });

    renderForm();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/ticker symbol/i), "aapl");
    await user.type(screen.getByLabelText(/^note$/i), "buy dip");
    await user.click(screen.getByRole("button", { name: /add/i }));

    await waitFor(() => {
      expect(spy).toHaveBeenCalledWith("AAPL", "buy dip");
    });
  });

  it("displays an error message on 409 duplicate", async () => {
    vi.spyOn(api, "addTicker").mockRejectedValue(
      new api.ApiError("dup", 409, { detail: "dup" }),
    );

    renderForm();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/ticker symbol/i), "AAPL");
    await user.click(screen.getByRole("button", { name: /add/i }));

    const alert = await screen.findByRole("alert");
    expect(alert.textContent?.toLowerCase()).toContain("already");
  });

  it("blocks submission when disabled (anon user)", async () => {
    const spy = vi.spyOn(api, "addTicker");
    renderForm({ disabled: true });

    const user = userEvent.setup();
    await user.type(screen.getByLabelText(/ticker symbol/i), "AAPL");
    await user.click(screen.getByRole("button", { name: /add/i }));

    expect(spy).not.toHaveBeenCalled();
    const alert = await screen.findByRole("alert");
    expect(alert.textContent?.toLowerCase()).toContain("sign in");
  });
});

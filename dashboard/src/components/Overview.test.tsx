import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { CHAIN_OK, STATS, makeClient } from "../test/fixtures";
import { Overview } from "./Overview";

function setup(client = makeClient(), onOpenRule = vi.fn(), onAuthError = vi.fn()) {
  render(<Overview client={client} onOpenRule={onOpenRule} onAuthError={onAuthError} />);
  return { client, onOpenRule, onAuthError };
}

describe("Overview", () => {
  it("shows the headline numbers", async () => {
    setup();
    expect(await screen.findByText("1,284")).toBeInTheDocument();
    expect(screen.getByText("213")).toBeInTheDocument();
    expect(screen.getByText("16.6%")).toBeInTheDocument();
  });

  it("shows chain status with a label, not just a colour", async () => {
    setup();
    expect(await screen.findByText(/chain verified/i)).toBeInTheDocument();
    expect(screen.getByText(/1,284 records/i)).toBeInTheDocument();
  });

  it("reports a broken chain and where it broke", async () => {
    const client = makeClient({
      chain: vi.fn().mockResolvedValue({ ...CHAIN_OK, ok: false, first_bad_seq: 3, reason: "x" }),
    });
    setup(client);
    expect(await screen.findByText(/chain broken at record #3/i)).toBeInTheDocument();
  });

  it("shows an empty state and a dash for the rate when there are no calls", async () => {
    const empty = { ...STATS, total: 0, blocked: 0, by_day: [], top_rules: [] };
    setup(makeClient({ stats: vi.fn().mockResolvedValue(empty) }));
    expect(await screen.findByText(/no calls in this period yet/i)).toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("refetches stats when the date range changes", async () => {
    const { client } = setup();
    await screen.findByText("1,284");
    await userEvent.click(screen.getByRole("radio", { name: /30 days/i }));
    await waitFor(() => expect(client.stats).toHaveBeenCalledWith(30));
  });

  it("keeps the previous data on screen, dimmed, while refetching", async () => {
    let resolveSecond: (v: typeof STATS) => void = () => {};
    const stats = vi
      .fn()
      .mockResolvedValueOnce(STATS)
      .mockReturnValueOnce(new Promise((r) => (resolveSecond = r)));
    setup(makeClient({ stats }));
    await screen.findByText("1,284");
    await userEvent.click(screen.getByRole("radio", { name: /30 days/i }));
    expect(screen.getByText("1,284")).toBeInTheDocument(); // still there, no skeleton
    expect(screen.getByTestId("scoped-content")).toHaveAttribute("aria-busy", "true");
    resolveSecond({ ...STATS, total: 99 });
    expect(await screen.findByText("99")).toBeInTheDocument();
    expect(screen.getByTestId("scoped-content")).toHaveAttribute("aria-busy", "false");
  });

  it("lets you read the calls-per-day values as a table (no hover needed)", async () => {
    setup();
    await screen.findByText("1,284");
    await userEvent.click(screen.getAllByRole("button", { name: /show as table/i })[0]);
    const table = screen.getByRole("table", { name: /calls per day/i });
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(4); // header + 3 days
    expect(within(rows[1]).getByText("Nov 18")).toBeInTheDocument();
    expect(within(rows[1]).getByText("170")).toBeInTheDocument(); // allowed = 200 - 30
    expect(within(rows[1]).getByText("30")).toBeInTheDocument();
  });

  it("lists top rules with a plain-English description and opens the events view on click", async () => {
    const { onOpenRule } = setup();
    await screen.findByText("1,284");
    await userEvent.click(screen.getAllByRole("button", { name: /show as table/i })[1]);
    const table = screen.getByRole("table", { name: /top triggered rules/i });
    expect(within(table).getByText("120")).toBeInTheDocument();
    await userEvent.click(within(table).getByRole("button", { name: /INJ_IGNORE_PREVIOUS/i }));
    expect(onOpenRule).toHaveBeenCalledWith("INJ_IGNORE_PREVIOUS");
  });

  it("renders untrusted rule ids as text, never as HTML", async () => {
    const evil = '<img src=x onerror="window.pwned=1">';
    const stats = { ...STATS, top_rules: [{ rule_id: evil, count: 5 }] };
    const { container } = render(
      <Overview
        client={makeClient({ stats: vi.fn().mockResolvedValue(stats) })}
        onOpenRule={vi.fn()}
        onAuthError={vi.fn()}
      />,
    );
    await screen.findByText("1,284");
    await userEvent.click(screen.getAllByRole("button", { name: /show as table/i })[1]);
    expect(screen.getByText(evil)).toBeInTheDocument();
    expect(container.querySelector("img")).toBeNull();
  });

  it("calls onAuthError when the API rejects the key", async () => {
    const { AuthError } = await import("../api");
    const client = makeClient({ stats: vi.fn().mockRejectedValue(new AuthError()) });
    const { onAuthError } = setup(client);
    await waitFor(() => expect(onAuthError).toHaveBeenCalled());
  });

  it("shows a readable error (not a blank page) when the API is down", async () => {
    const client = makeClient({ stats: vi.fn().mockRejectedValue(new Error("boom")) });
    setup(client);
    expect(await screen.findByRole("alert")).toHaveTextContent(/could not load/i);
  });
});

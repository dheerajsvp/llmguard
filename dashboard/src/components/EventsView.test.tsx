import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ApiError } from "../api";
import { makeClient, makeEvent, page } from "../test/fixtures";
import { EventsView } from "./EventsView";

function setup(client = makeClient(), initialRule?: string) {
  const onAuthError = vi.fn();
  render(<EventsView client={client} initialRule={initialRule} onAuthError={onAuthError} />);
  return { client, onAuthError };
}

describe("EventsView", () => {
  it("lists events with a text status, rules and redaction summary", async () => {
    setup();
    const table = await screen.findByRole("table", { name: /audit events/i });
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(3); // header + 2
    expect(within(rows[1]).getByText("Blocked")).toBeInTheDocument();
    expect(within(rows[1]).getByText(/INJ_IGNORE_PREVIOUS/)).toBeInTheDocument();
    expect(within(rows[2]).getByText("Allowed")).toBeInTheDocument();
    expect(within(rows[2]).getByText("PAN ×1, PHONE ×2")).toBeInTheDocument();
    expect(screen.getByText(/showing 1–2 of 2/i)).toBeInTheDocument();
  });

  it("filters by status and resets to the first page", async () => {
    const { client } = setup();
    await screen.findByRole("table", { name: /audit events/i });
    await userEvent.selectOptions(screen.getByLabelText(/status/i), "blocked");
    await waitFor(() =>
      expect(client.events).toHaveBeenLastCalledWith({
        limit: 50,
        offset: 0,
        blocked: true,
        ruleId: undefined,
      }),
    );
  });

  it("filters by rule", async () => {
    const { client } = setup();
    await screen.findByRole("table", { name: /audit events/i });
    await userEvent.selectOptions(screen.getByLabelText(/rule/i), "INJ_REVEAL_PROMPT");
    await waitFor(() =>
      expect(client.events).toHaveBeenLastCalledWith(
        expect.objectContaining({ ruleId: "INJ_REVEAL_PROMPT", offset: 0 }),
      ),
    );
  });

  it("starts with the rule chosen on the overview", async () => {
    const { client } = setup(makeClient(), "INJ_REVEAL_PROMPT");
    await waitFor(() =>
      expect(client.events).toHaveBeenCalledWith(
        expect.objectContaining({ ruleId: "INJ_REVEAL_PROMPT" }),
      ),
    );
    expect(screen.getByLabelText(/rule/i)).toHaveValue("INJ_REVEAL_PROMPT");
  });

  it("paginates, disabling Previous on the first page and Next on the last", async () => {
    const events = vi.fn().mockImplementation(async ({ offset }: { offset: number }) =>
      page([makeEvent(offset + 1)], 120, offset),
    );
    setup(makeClient({ events }));
    await screen.findByText(/showing 1–1 of 120/i);
    expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: /next/i }));
    await waitFor(() => expect(events).toHaveBeenLastCalledWith(expect.objectContaining({ offset: 50 })));
    await userEvent.click(screen.getByRole("button", { name: /next/i }));
    await screen.findByText(/showing 101–101 of 120/i);
    expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
  });

  it("shows an empty state when nothing matches", async () => {
    setup(makeClient({ events: vi.fn().mockResolvedValue(page([], 0)) }));
    expect(await screen.findByText(/no events match/i)).toBeInTheDocument();
  });

  it("opens a detail panel with hashes and the privacy note, then closes it", async () => {
    const { client } = setup();
    const table = await screen.findByRole("table", { name: /audit events/i });
    await userEvent.click(within(table).getAllByRole("row")[1]);
    const dialog = await screen.findByRole("dialog", { name: /event details/i });
    await waitFor(() => expect(client.event).toHaveBeenCalledWith("req-2-aaaaaaaa-bbbb"));
    expect(within(dialog).getByText("c".repeat(64))).toBeInTheDocument();
    expect(within(dialog).getByText("b".repeat(64))).toBeInTheDocument();
    expect(within(dialog).getByText(/never stored/i)).toBeInTheDocument();
    await userEvent.click(within(dialog).getByRole("button", { name: /close/i }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("is keyboard accessible: rows open details with Enter", async () => {
    setup();
    const table = await screen.findByRole("table", { name: /audit events/i });
    within(table).getAllByRole("row")[1].focus();
    await userEvent.keyboard("{Enter}");
    expect(await screen.findByRole("dialog", { name: /event details/i })).toBeInTheDocument();
  });

  it("shows 'event not found' when the detail request 404s", async () => {
    const event = vi.fn().mockRejectedValue(new ApiError(404));
    setup(makeClient({ event }));
    const table = await screen.findByRole("table", { name: /audit events/i });
    await userEvent.click(within(table).getAllByRole("row")[1]);
    expect(await screen.findByText(/event not found/i)).toBeInTheDocument();
  });

  it("renders untrusted rule ids as text, never as HTML", async () => {
    const evil = "<b id='x'>bold</b>";
    const events = vi.fn().mockResolvedValue(page([makeEvent(2, { rule_ids: [evil] })]));
    const { container } = render(
      <EventsView client={makeClient({ events })} onAuthError={vi.fn()} />,
    );
    expect(await screen.findByText(evil)).toBeInTheDocument();
    expect(container.querySelector("#x")).toBeNull();
  });

  it("reports auth errors upward", async () => {
    const { AuthError } = await import("../api");
    const { onAuthError } = setup(makeClient({ events: vi.fn().mockRejectedValue(new AuthError()) }));
    await waitFor(() => expect(onAuthError).toHaveBeenCalled());
  });
});

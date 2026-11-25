import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { CHAIN_OK, STATS, makeEvent, page } from "./test/fixtures";

const GOOD = "good-admin-key-0123456789";
const STORAGE_KEY = "llmguard.adminKey";

function installFetch(opts: { rejectAll?: number } = {}) {
  const fn = vi.fn(async (url: string, init?: { headers?: Record<string, string> }) => {
    const key = init?.headers?.["X-API-Key"];
    const status = opts.rejectAll ?? (key === GOOD ? 200 : 401);
    let body: unknown = {};
    if (url.startsWith("/api/stats")) body = STATS;
    else if (url.startsWith("/api/chain")) body = CHAIN_OK;
    else if (url.startsWith("/api/events")) body = page([makeEvent(2), makeEvent(1)]);
    return { ok: status === 200, status, json: async () => body };
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

async function signIn(key = GOOD) {
  await userEvent.type(screen.getByLabelText(/admin key/i), key);
  await userEvent.click(screen.getByRole("button", { name: /connect/i }));
}

afterEach(() => vi.unstubAllGlobals());

describe("App", () => {
  it("asks for the admin key first and calls the API with nothing until then", () => {
    const fetchFn = installFetch();
    render(<App />);
    expect(screen.getByLabelText(/admin key/i)).toHaveAttribute("type", "password");
    expect(fetchFn).not.toHaveBeenCalled();
  });

  it("rejects a wrong key with a message and stores nothing", async () => {
    installFetch();
    render(<App />);
    await signIn("wrong-key-0123456789abc");
    expect(await screen.findByRole("alert")).toHaveTextContent(/key was rejected/i);
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("accepts a good key, shows the overview and keeps the key in sessionStorage only", async () => {
    installFetch();
    render(<App />);
    await signIn();
    expect(await screen.findByText("1,284")).toBeInTheDocument();
    expect(sessionStorage.getItem(STORAGE_KEY)).toBe(GOOD);
    expect(localStorage.length).toBe(0);
  });

  it("never renders the key anywhere in the page", async () => {
    installFetch();
    const { container } = render(<App />);
    await signIn();
    await screen.findByText("1,284");
    expect(container.innerHTML).not.toContain(GOOD);
  });

  it("restores a session from sessionStorage", async () => {
    installFetch();
    sessionStorage.setItem(STORAGE_KEY, GOOD);
    render(<App />);
    expect(await screen.findByText("1,284")).toBeInTheDocument();
  });

  it("signs out: clears the key and returns to the key screen", async () => {
    installFetch();
    render(<App />);
    await signIn();
    await screen.findByText("1,284");
    await userEvent.click(screen.getByRole("button", { name: /sign out/i }));
    expect(screen.getByLabelText(/admin key/i)).toBeInTheDocument();
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("returns to the key screen if the key stops working", async () => {
    installFetch({ rejectAll: 403 });
    sessionStorage.setItem(STORAGE_KEY, GOOD);
    render(<App />);
    expect(await screen.findByLabelText(/admin key/i)).toBeInTheDocument();
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it("switches between Overview and Events", async () => {
    installFetch();
    sessionStorage.setItem(STORAGE_KEY, GOOD);
    render(<App />);
    await screen.findByText("1,284");
    await userEvent.click(screen.getByRole("tab", { name: /events/i }));
    expect(await screen.findByRole("table", { name: /audit events/i })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: /overview/i }));
    expect(await screen.findByText("1,284")).toBeInTheDocument();
  });

  it("opens Events filtered by a rule picked on the Overview", async () => {
    const fetchFn = installFetch();
    sessionStorage.setItem(STORAGE_KEY, GOOD);
    render(<App />);
    await screen.findByText("1,284");
    await userEvent.click(screen.getAllByRole("button", { name: /show as table/i })[1]);
    await userEvent.click(screen.getByRole("button", { name: /INJ_IGNORE_PREVIOUS/i }));
    await waitFor(() =>
      expect(fetchFn.mock.calls.some(([u]) => String(u).includes("rule_id=INJ_IGNORE_PREVIOUS"))).toBe(true),
    );
    expect(screen.getByRole("tab", { name: /events/i })).toHaveAttribute("aria-selected", "true");
  });
});

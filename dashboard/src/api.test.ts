import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, AuthError, createClient } from "./api";

function mockFetch(status: number, body: unknown = {}) {
  const fn = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

afterEach(() => vi.unstubAllGlobals());

describe("api client", () => {
  it("sends the key in the X-API-Key header and returns the JSON", async () => {
    const fetchFn = mockFetch(200, { total: 3 });
    const result = await createClient("secret-key-0123456789").stats(7);
    expect(result).toEqual({ total: 3 });
    const [url, init] = fetchFn.mock.calls[0];
    expect(url).toBe("/api/stats?days=7");
    expect(init.headers["X-API-Key"]).toBe("secret-key-0123456789");
  });

  it("never puts the key in the URL", async () => {
    const fetchFn = mockFetch(200, {});
    await createClient("secret-key-0123456789").chain();
    expect(String(fetchFn.mock.calls[0][0])).not.toContain("secret");
  });

  it("builds the events query and omits unset filters", async () => {
    const fetchFn = mockFetch(200, {});
    const client = createClient("k".repeat(20));
    await client.events({ limit: 50, offset: 0 });
    await client.events({ limit: 25, offset: 50, blocked: true, ruleId: "INJ_X" });
    expect(fetchFn.mock.calls[0][0]).toBe("/api/events?limit=50&offset=0");
    expect(fetchFn.mock.calls[1][0]).toBe("/api/events?limit=25&offset=50&blocked=true&rule_id=INJ_X");
  });

  it("encodes the request id in the path", async () => {
    const fetchFn = mockFetch(200, {});
    await createClient("k".repeat(20)).event("a/b c");
    expect(fetchFn.mock.calls[0][0]).toBe("/api/events/a%2Fb%20c");
  });

  it.each([401, 403])("throws AuthError on %i", async (status) => {
    mockFetch(status);
    await expect(createClient("k".repeat(20)).stats(7)).rejects.toBeInstanceOf(AuthError);
  });

  it("throws ApiError with status on other failures, without the response body", async () => {
    mockFetch(500, { detail: "secret internals" });
    const err = await createClient("k".repeat(20)).stats(7).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(500);
    expect((err as ApiError).message).not.toContain("secret internals");
  });

  it("maps a 404 to ApiError with status 404", async () => {
    mockFetch(404);
    const err = await createClient("k".repeat(20)).event("x").catch((e: unknown) => e);
    expect((err as ApiError).status).toBe(404);
  });
});

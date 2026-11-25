import { vi } from "vitest";
import type { ApiClient, Chain, EventOut, EventsPage, Stats } from "../api";

export const STATS: Stats = {
  since: "2026-11-14T00:00:00Z",
  total: 1284,
  blocked: 213,
  by_day: [
    { day: "2026-11-18", total: 200, blocked: 30 },
    { day: "2026-11-19", total: 0, blocked: 0 },
    { day: "2026-11-20", total: 1084, blocked: 183 },
  ],
  top_rules: [
    { rule_id: "INJ_IGNORE_PREVIOUS", count: 120 },
    { rule_id: "INJ_REVEAL_PROMPT", count: 60 },
  ],
};

export const CHAIN_OK: Chain = {
  ok: true,
  checked: 1284,
  first_bad_seq: null,
  reason: "",
  head: { seq: 1284, hash: "f".repeat(64) },
};

export function makeEvent(n: number, over: Partial<EventOut> = {}): EventOut {
  return {
    seq: n,
    created_at: "2026-11-20T10:00:00Z",
    request_id: `req-${n}-aaaaaaaa-bbbb`,
    blocked: n % 2 === 0,
    rule_ids: n % 2 === 0 ? ["INJ_IGNORE_PREVIOUS"] : [],
    redactions: n % 2 === 0 ? {} : { PAN: 1, PHONE: 2 },
    prompt_sha256: "a".repeat(64),
    prev_hash: "b".repeat(64),
    hash: "c".repeat(64),
    ...over,
  };
}

export function page(events: EventOut[], total = events.length, offset = 0): EventsPage {
  return { events, total, limit: 50, offset };
}

export function makeClient(over: Partial<ApiClient> = {}): ApiClient {
  return {
    stats: vi.fn().mockResolvedValue(STATS),
    chain: vi.fn().mockResolvedValue(CHAIN_OK),
    events: vi.fn().mockResolvedValue(page([makeEvent(2), makeEvent(1)])),
    event: vi.fn().mockImplementation(async (id: string) => makeEvent(2, { request_id: id })),
    ...over,
  };
}

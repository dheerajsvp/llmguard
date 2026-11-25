// Typed client for the llmguard read API. Everything here mirrors src/llmguard/api/app.py.

export interface DayCount {
  day: string; // ISO date, e.g. "2026-11-20"
  total: number;
  blocked: number;
}

export interface RuleCount {
  rule_id: string;
  count: number;
}

export interface Stats {
  since: string;
  total: number;
  blocked: number;
  by_day: DayCount[];
  top_rules: RuleCount[];
}

export interface EventOut {
  seq: number;
  created_at: string;
  request_id: string;
  blocked: boolean;
  rule_ids: string[];
  redactions: Record<string, number>;
  prompt_sha256: string;
  prev_hash: string;
  hash: string;
}

export interface EventsPage {
  events: EventOut[];
  total: number;
  limit: number;
  offset: number;
}

export interface Chain {
  ok: boolean;
  checked: number;
  first_bad_seq: number | null;
  reason: string;
  head: { seq: number; hash: string } | null;
}

export interface EventsQuery {
  limit: number;
  offset: number;
  blocked?: boolean;
  ruleId?: string;
}

export interface ApiClient {
  stats(days: number): Promise<Stats>;
  events(query: EventsQuery): Promise<EventsPage>;
  event(requestId: string): Promise<EventOut>;
  chain(): Promise<Chain>;
}

/** The server said the key is missing, wrong, or for the wrong role (401/403). */
export class AuthError extends Error {
  constructor() {
    super("Not authorized");
    this.name = "AuthError";
  }
}

/** Any other failure. The message is fixed: we never surface response bodies. */
export class ApiError extends Error {
  readonly status: number;
  constructor(status: number) {
    super(`Request failed (${status})`);
    this.name = "ApiError";
    this.status = status;
  }
}

export function createClient(key: string): ApiClient {
  async function get<T>(path: string): Promise<T> {
    // The key goes in a header, never in the URL (URLs end up in logs and history).
    const res = await fetch(path, { headers: { "X-API-Key": key, Accept: "application/json" } });
    if (res.status === 401 || res.status === 403) throw new AuthError();
    if (!res.ok) throw new ApiError(res.status);
    return (await res.json()) as T;
  }

  return {
    stats: (days) => get<Stats>(`/api/stats?days=${days}`),
    chain: () => get<Chain>("/api/chain"),
    event: (id) => get<EventOut>(`/api/events/${encodeURIComponent(id)}`),
    events: ({ limit, offset, blocked, ruleId }) => {
      const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
      if (blocked !== undefined) params.set("blocked", String(blocked));
      if (ruleId) params.set("rule_id", ruleId);
      return get<EventsPage>(`/api/events?${params.toString()}`);
    },
  };
}

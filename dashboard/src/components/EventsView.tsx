import { useState, type KeyboardEvent } from "react";
import type { ApiClient, EventOut } from "../api";
import { formatTime, shortId, summarizeRedactions } from "../format";
import { useApiData } from "../hooks";
import { RULE_IDS, describeRule } from "../ruleLabels";
import { EventDetail } from "./EventDetail";
import { StatusIcon } from "./StatTile";

const PAGE_SIZE = 50;

type Status = "all" | "blocked" | "allowed";

interface Props {
  client: ApiClient;
  initialRule?: string;
  onAuthError: () => void;
}

export function EventsView({ client, initialRule, onAuthError }: Props) {
  const [status, setStatus] = useState<Status>("all");
  const [rule, setRule] = useState<string>(initialRule ?? "");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);

  const blocked = status === "all" ? undefined : status === "blocked";
  const ruleId = rule || undefined;
  const page = useApiData(
    () => client.events({ limit: PAGE_SIZE, offset, blocked, ruleId }),
    [client, offset, blocked, ruleId],
    onAuthError,
  );
  const data = page.data;
  const rules = rule && !RULE_IDS.includes(rule) ? [...RULE_IDS, rule] : RULE_IDS;

  function open(e: EventOut) {
    setSelected(e.request_id);
  }

  function onKey(ev: KeyboardEvent, e: EventOut) {
    if (ev.key === "Enter" || ev.key === " ") {
      ev.preventDefault();
      open(e);
    }
  }

  return (
    <div>
      <div className="filters">
        <label className="field">
          Status
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value as Status);
              setOffset(0);
            }}
          >
            <option value="all">All</option>
            <option value="blocked">Blocked</option>
            <option value="allowed">Allowed</option>
          </select>
        </label>
        <label className="field">
          Rule
          <select
            value={rule}
            onChange={(e) => {
              setRule(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">All rules</option>
            {rules.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
        </label>
      </div>

      {page.error ? (
        <p role="alert" className="alert">
          Could not load events. Check that the API is running, then reload.
        </p>
      ) : null}

      <div aria-busy={page.loading} className={page.loading && data ? "dimmed" : ""}>
        {data && data.events.length === 0 ? (
          <p className="empty">No events match these filters.</p>
        ) : null}
        {data && data.events.length > 0 ? (
          <>
            <div className="table-wrap">
              <table aria-label="Audit events" className="events">
                <thead>
                  <tr>
                    <th scope="col">Time</th>
                    <th scope="col">Request</th>
                    <th scope="col">Status</th>
                    <th scope="col">Rules</th>
                    <th scope="col">Redactions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.events.map((e) => (
                    <tr key={e.request_id} tabIndex={0} onClick={() => open(e)} onKeyDown={(ev) => onKey(ev, e)}>
                      <td>{formatTime(e.created_at)}</td>
                      <td className="mono">{shortId(e.request_id)}</td>
                      <td>
                        <span className={`status ${e.blocked ? "status-blocked" : "status-allowed"}`}>
                          <StatusIcon ok={!e.blocked} />
                          {e.blocked ? "Blocked" : "Allowed"}
                        </span>
                      </td>
                      <td>
                        {e.rule_ids.length === 0
                          ? "—"
                          : e.rule_ids.map((r) => (
                              <span key={r} className="tag mono" title={describeRule(r)}>
                                {r}
                              </span>
                            ))}
                      </td>
                      <td>{summarizeRedactions(e.redactions)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pager">
              <span className="muted">
                Showing {data.offset + 1}–{data.offset + data.events.length} of {data.total.toLocaleString("en-US")}
              </span>
              <span>
                <button type="button" disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
                  Previous
                </button>
                <button type="button" disabled={offset + PAGE_SIZE >= data.total} onClick={() => setOffset(offset + PAGE_SIZE)}>
                  Next
                </button>
              </span>
            </div>
          </>
        ) : null}
      </div>

      {selected ? (
        <EventDetail client={client} requestId={selected} onClose={() => setSelected(null)} onAuthError={onAuthError} />
      ) : null}
    </div>
  );
}

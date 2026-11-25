import { useEffect, useRef } from "react";
import { ApiError, type ApiClient } from "../api";
import { formatTime, summarizeRedactions } from "../format";
import { useApiData } from "../hooks";
import { describeRule } from "../ruleLabels";

interface Props {
  client: ApiClient;
  requestId: string;
  onClose: () => void;
  onAuthError: () => void;
}

export function EventDetail({ client, requestId, onClose, onAuthError }: Props) {
  const { data, error } = useApiData(() => client.event(requestId), [client, requestId], onAuthError);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div className="backdrop" onClick={onClose}>
      <aside
        className="panel"
        role="dialog"
        aria-modal="true"
        aria-label="Event details"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="card-head">
          <h2>Event details</h2>
          <button type="button" ref={closeRef} onClick={onClose}>
            Close
          </button>
        </header>

        {error ? (
          <p role="alert" className="alert">
            {error instanceof ApiError && error.status === 404 ? "Event not found." : "Could not load this event."}
          </p>
        ) : null}
        {!data && !error ? <p className="muted">Loading…</p> : null}

        {data ? (
          <>
            <dl>
              <dt>Status</dt>
              <dd>{data.blocked ? "Blocked" : "Allowed"}</dd>
              <dt>Time</dt>
              <dd>{formatTime(data.created_at)}</dd>
              <dt>Request id</dt>
              <dd className="mono">{data.request_id}</dd>
              <dt>Rules fired</dt>
              <dd>
                {data.rule_ids.length === 0 ? (
                  "None"
                ) : (
                  <ul className="plain">
                    {data.rule_ids.map((r) => (
                      <li key={r}>
                        <span className="mono">{r}</span>
                        <span className="muted"> {describeRule(r) === r ? "" : `· ${describeRule(r)}`}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </dd>
              <dt>Personal data redacted</dt>
              <dd>{summarizeRedactions(data.redactions)}</dd>
              <dt>Record number</dt>
              <dd>#{data.seq}</dd>
              <dt>Prompt fingerprint (SHA-256)</dt>
              <dd className="mono hash">{data.prompt_sha256}</dd>
              <dt>Previous record hash</dt>
              <dd className="mono hash">{data.prev_hash}</dd>
              <dt>This record hash</dt>
              <dd className="mono hash">{data.hash}</dd>
            </dl>
            <p className="muted note">
              The prompt and reply are never stored. Only a fingerprint of the redacted prompt is
              kept, so a call can be matched to a prompt you already hold without the log
              revealing it.
            </p>
          </>
        ) : null}
      </aside>
    </div>
  );
}

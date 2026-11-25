import type { ReactNode } from "react";

interface Props {
  label: string;
  value: ReactNode;
  detail?: ReactNode;
  tone?: "good" | "critical";
  icon?: ReactNode;
}

/** A single headline number: label above, value large, optional detail below. */
export function StatTile({ label, value, detail, tone, icon }: Props) {
  return (
    <div className="tile">
      <div className="tile-label">{label}</div>
      <div className={`tile-value${tone ? ` tone-${tone}` : ""}`}>
        {icon}
        <span>{value}</span>
      </div>
      {detail ? <div className="tile-detail">{detail}</div> : null}
    </div>
  );
}

/** Status is never colour alone: each tone ships with its own icon shape and a text label. */
export function StatusIcon({ ok }: { ok: boolean }) {
  return (
    <svg className="status-icon" viewBox="0 0 16 16" width="18" height="18" aria-hidden="true">
      {ok ? (
        <path d="M3 8.5l3.2 3.2L13 5" fill="none" stroke="currentColor" strokeWidth="2" />
      ) : (
        <path d="M4 4l8 8M12 4l-8 8" fill="none" stroke="currentColor" strokeWidth="2" />
      )}
    </svg>
  );
}

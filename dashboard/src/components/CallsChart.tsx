import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { DayCount } from "../api";
import { compact, formatDay } from "../format";

interface Row {
  label: string;
  allowed: number;
  blocked: number;
}

function toRows(days: DayCount[]): Row[] {
  return days.map((d) => ({
    label: formatDay(d.day),
    allowed: d.total - d.blocked,
    blocked: d.blocked,
  }));
}

function CallsTooltip({ active, payload }: { active?: boolean; payload?: ReadonlyArray<{ payload?: unknown }> }) {
  const row = payload?.[0]?.payload as Row | undefined;
  if (!active || !row) return null;
  // Values lead, names follow. Text is rendered by React, so labels are never parsed as HTML.
  return (
    <div className="tooltip">
      <div className="tooltip-title">{row.label}</div>
      <div className="tooltip-row">
        <span className="swatch swatch-accent" aria-hidden="true" />
        <strong>{compact(row.blocked)}</strong> <span className="muted">blocked</span>
      </div>
      <div className="tooltip-row">
        <span className="swatch swatch-allowed" aria-hidden="true" />
        <strong>{compact(row.allowed)}</strong> <span className="muted">allowed</span>
      </div>
    </div>
  );
}

export function CallsChart({ days }: { days: DayCount[] }) {
  const rows = toRows(days);
  return (
    <>
      <ul className="legend" aria-label="Legend">
        <li>
          <span className="swatch swatch-accent" aria-hidden="true" /> Blocked
        </li>
        <li>
          <span className="swatch swatch-allowed" aria-hidden="true" /> Allowed
        </li>
      </ul>
      <ResponsiveContainer width="100%" height={260} initialDimension={{ width: 640, height: 260 }}>
        <BarChart data={rows} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--grid)" />
          <XAxis dataKey="label" tickLine={false} axisLine={{ stroke: "var(--axis)" }} tick={{ fill: "var(--muted)", fontSize: 12 }} interval="preserveStartEnd" />
          <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={44} tickFormatter={compact} tick={{ fill: "var(--muted)", fontSize: 12 }} />
          <Tooltip content={CallsTooltip} cursor={{ fill: "var(--grid)", opacity: 0.6 }} />
          {/* Stacked: the 2px surface-coloured stroke is the gap between segments. */}
          <Bar dataKey="allowed" stackId="calls" fill="var(--allowed)" stroke="var(--surface)" strokeWidth={2} maxBarSize={24} />
          <Bar dataKey="blocked" stackId="calls" fill="var(--accent)" stroke="var(--surface)" strokeWidth={2} maxBarSize={24} radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </>
  );
}

export function CallsTable({ days }: { days: DayCount[] }) {
  return (
    <div className="table-wrap">
      <table aria-label="Calls per day">
        <thead>
          <tr>
            <th scope="col">Day</th>
            <th scope="col" className="num">Allowed</th>
            <th scope="col" className="num">Blocked</th>
            <th scope="col" className="num">Total</th>
          </tr>
        </thead>
        <tbody>
          {days.map((d) => (
            <tr key={d.day}>
              <th scope="row">{formatDay(d.day)}</th>
              <td className="num">{compact(d.total - d.blocked)}</td>
              <td className="num">{compact(d.blocked)}</td>
              <td className="num">{compact(d.total)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

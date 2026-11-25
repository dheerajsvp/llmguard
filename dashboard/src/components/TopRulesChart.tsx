import { Bar, BarChart, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { RuleCount } from "../api";
import { compact } from "../format";
import { RULE_LABELS } from "../ruleLabels";

function RuleTooltip({ active, payload }: { active?: boolean; payload?: ReadonlyArray<{ payload?: unknown }> }) {
  const row = payload?.[0]?.payload as RuleCount | undefined;
  if (!active || !row) return null;
  return (
    <div className="tooltip">
      <div className="tooltip-row">
        <strong>{compact(row.count)}</strong> <span className="muted">calls</span>
      </div>
      <div className="tooltip-title">{row.rule_id}</div>
      {RULE_LABELS[row.rule_id] ? <div className="muted">{RULE_LABELS[row.rule_id]}</div> : null}
    </div>
  );
}

interface Props {
  rules: RuleCount[];
  onOpenRule: (ruleId: string) => void;
}

/** Ranked horizontal bars, one hue: the length carries the value, so no colour ramp is needed. */
export function TopRulesChart({ rules, onOpenRule }: Props) {
  const height = rules.length * 36 + 24;
  return (
    <ResponsiveContainer width="100%" height={height} initialDimension={{ width: 640, height }}>
      <BarChart data={rules} layout="vertical" margin={{ top: 4, right: 40, bottom: 4, left: 0 }}>
        <XAxis type="number" hide />
        <YAxis type="category" dataKey="rule_id" width={190} tickLine={false} axisLine={{ stroke: "var(--axis)" }} tick={{ fill: "var(--secondary)", fontSize: 12 }} />
        <Tooltip content={RuleTooltip} cursor={{ fill: "var(--grid)", opacity: 0.6 }} />
        <Bar
          dataKey="count"
          fill="var(--accent)"
          radius={[0, 4, 4, 0]}
          maxBarSize={20}
          cursor="pointer"
          onClick={(_, index) => onOpenRule(rules[index].rule_id)}
        >
          <LabelList dataKey="count" position="right" formatter={(v: unknown) => compact(Number(v))} fill="var(--secondary)" fontSize={12} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function TopRulesTable({ rules, onOpenRule }: Props) {
  return (
    <div className="table-wrap">
      <table aria-label="Top triggered rules">
        <thead>
          <tr>
            <th scope="col">Rule</th>
            <th scope="col">What it means</th>
            <th scope="col" className="num">Calls</th>
          </tr>
        </thead>
        <tbody>
          {rules.map((r) => (
            <tr key={r.rule_id}>
              <th scope="row">
                <button type="button" className="link-button mono" onClick={() => onOpenRule(r.rule_id)}>
                  {r.rule_id}
                </button>
              </th>
              <td>{RULE_LABELS[r.rule_id] ?? "No description yet"}</td>
              <td className="num">{compact(r.count)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

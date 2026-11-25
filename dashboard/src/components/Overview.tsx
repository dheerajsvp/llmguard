import { useState } from "react";
import type { ApiClient } from "../api";
import { compact, percent } from "../format";
import { useApiData } from "../hooks";
import { CallsChart, CallsTable } from "./CallsChart";
import { ChartCard } from "./ChartCard";
import { StatTile, StatusIcon } from "./StatTile";
import { TopRulesChart, TopRulesTable } from "./TopRulesChart";

const RANGES = [7, 30, 90] as const;

interface Props {
  client: ApiClient;
  onOpenRule: (ruleId: string) => void;
  onAuthError: () => void;
}

export function Overview({ client, onOpenRule, onAuthError }: Props) {
  const [days, setDays] = useState<number>(7);
  const stats = useApiData(() => client.stats(days), [client, days], onAuthError);
  const chain = useApiData(() => client.chain(), [client], onAuthError);
  const data = stats.data;

  return (
    <div>
      {/* One filter row above everything it scopes. */}
      <div className="filters" role="radiogroup" aria-label="Date range">
        {RANGES.map((d) => (
          <label key={d} className={`chip${days === d ? " chip-on" : ""}`}>
            <input type="radio" name="range" checked={days === d} onChange={() => setDays(d)} />
            {d} days
          </label>
        ))}
      </div>

      {stats.error ? (
        <p role="alert" className="alert">
          Could not load statistics. Check that the API is running, then reload.
        </p>
      ) : null}

      <div data-testid="scoped-content" aria-busy={stats.loading} className={stats.loading && data ? "dimmed" : ""}>
        <div className="tiles">
          <StatTile label="Calls" value={data ? compact(data.total) : "…"} detail={`last ${days} days`} />
          <StatTile label="Blocked" value={data ? compact(data.blocked) : "…"} detail="injection or policy" />
          <StatTile label="Block rate" value={data ? percent(data.blocked, data.total) : "…"} />
          <IntegrityTile chain={chain.data} failed={Boolean(chain.error)} />
        </div>

        {data && data.total === 0 ? (
          <p className="empty">No calls in this period yet. Send a request to /v1/chat and it will appear here.</p>
        ) : data ? (
          <div className="charts">
            <ChartCard
              title="Calls per day"
              subtitle="Blocked calls highlighted against all other calls"
              summary={`Calls per day over the last ${days} days: ${data.total} calls, ${data.blocked} blocked.`}
              chart={<CallsChart days={data.by_day} />}
              table={<CallsTable days={data.by_day} />}
            />
            {data.top_rules.length > 0 ? (
              <ChartCard
                title="Top triggered rules"
                subtitle="Select a rule to see its events"
                summary={`Top triggered rules: ${data.top_rules.map((r) => `${r.rule_id} ${r.count}`).join(", ")}.`}
                chart={<TopRulesChart rules={data.top_rules} onOpenRule={onOpenRule} />}
                table={<TopRulesTable rules={data.top_rules} onOpenRule={onOpenRule} />}
              />
            ) : (
              <section className="card">
                <h2>Top triggered rules</h2>
                <p className="muted">No rules fired in this period.</p>
              </section>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function IntegrityTile({ chain, failed }: { chain: import("../api").Chain | undefined; failed: boolean }) {
  if (failed) return <StatTile label="Integrity" value="Could not verify" />;
  if (!chain) return <StatTile label="Integrity" value="Checking…" />;
  if (chain.ok) {
    return (
      <StatTile
        label="Integrity"
        tone="good"
        icon={<StatusIcon ok />}
        value="Chain verified"
        detail={`${compact(chain.checked)} records`}
      />
    );
  }
  return (
    <StatTile
      label="Integrity"
      tone="critical"
      icon={<StatusIcon ok={false} />}
      value={`Chain broken at record #${chain.first_bad_seq}`}
      detail="The audit log may have been altered"
    />
  );
}

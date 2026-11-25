import { useState, type ReactNode } from "react";

interface Props {
  title: string;
  subtitle: string;
  /** Plain-text summary for screen readers; the table twin carries the full data. */
  summary: string;
  chart: ReactNode;
  table: ReactNode;
}

/** A chart plus its table twin. Tooltips enhance; the table guarantees every value is reachable. */
export function ChartCard({ title, subtitle, summary, chart, table }: Props) {
  const [asTable, setAsTable] = useState(false);
  return (
    <section className="card" aria-labelledby={`${title}-h`}>
      <header className="card-head">
        <div>
          <h2 id={`${title}-h`}>{title}</h2>
          <p className="muted">{subtitle}</p>
        </div>
        <button type="button" className="link-button" onClick={() => setAsTable((v) => !v)}>
          {asTable ? "Show as chart" : "Show as table"}
        </button>
      </header>
      {asTable ? (
        table
      ) : (
        <div role="img" aria-label={summary}>
          {chart}
        </div>
      )}
    </section>
  );
}

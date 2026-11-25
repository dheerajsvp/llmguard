const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const COMPACT = new Intl.NumberFormat("en-US", { notation: "compact", maximumFractionDigits: 1 });

/** 1,284 / 12.9K / 4.2M: full digits under 10,000, compact above. */
export function compact(n: number): string {
  return n < 10_000 ? n.toLocaleString("en-US") : COMPACT.format(n);
}

/** "16.6%", or a dash when there is nothing to divide by. */
export function percent(part: number, total: number): string {
  return total === 0 ? "—" : `${((part / total) * 100).toFixed(1)}%`;
}

export function shortId(id: string): string {
  return id.slice(0, 8);
}

/** "2026-11-20" -> "Nov 20". Parsed by hand so the timezone can never shift the day. */
export function formatDay(iso: string): string {
  const [, month, day] = iso.split("-").map(Number);
  return `${MONTHS[month - 1]} ${day}`;
}

export function formatTime(iso: string): string {
  return new Date(iso).toLocaleString();
}

export function summarizeRedactions(redactions: Record<string, number>): string {
  const parts = Object.entries(redactions).map(([type, count]) => `${type} ×${count}`);
  return parts.length ? parts.join(", ") : "None";
}

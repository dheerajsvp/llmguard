import { useState, type FormEvent } from "react";

interface Props {
  onConnect: (key: string) => Promise<"ok" | "rejected" | "unreachable">;
}

export function KeyGate({ onConnect }: Props) {
  const [key, setKey] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const result = await onConnect(key.trim());
    setBusy(false);
    if (result === "rejected") setError("That key was rejected. Check it and try again.");
    if (result === "unreachable") setError("Could not reach the server. Is the API running?");
    if (result === "ok") setKey("");
  }

  return (
    <main className="gate">
      <form className="card gate-card" onSubmit={submit}>
        <h1>llmguard dashboard</h1>
        <p className="muted">
          Enter an admin key to view the audit log. It is kept for this browser tab only and is
          cleared when you close the tab or sign out.
        </p>
        <label htmlFor="admin-key">Admin key</label>
        <input
          id="admin-key"
          type="password"
          autoComplete="off"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          required
        />
        {error ? (
          <p role="alert" className="alert">
            {error}
          </p>
        ) : null}
        <button type="submit" className="primary" disabled={busy || key.trim() === ""}>
          {busy ? "Connecting…" : "Connect"}
        </button>
      </form>
    </main>
  );
}

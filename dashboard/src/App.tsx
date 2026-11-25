import { useCallback, useMemo, useState } from "react";
import { AuthError, createClient } from "./api";
import { EventsView } from "./components/EventsView";
import { KeyGate } from "./components/KeyGate";
import { Overview } from "./components/Overview";

const STORAGE_KEY = "llmguard.adminKey";

// sessionStorage: survives a reload but is cleared when the tab closes. Safer than
// localStorage, which would keep an admin key on disk indefinitely.
function readKey(): string | null {
  try {
    return sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function writeKey(key: string | null): void {
  try {
    if (key) sessionStorage.setItem(STORAGE_KEY, key);
    else sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    /* storage blocked: the key then lives in memory only, which is fine */
  }
}

type View = "overview" | "events";

export function App() {
  const [key, setKey] = useState<string | null>(readKey);
  const [view, setView] = useState<View>("overview");
  const [rule, setRule] = useState<string | undefined>();

  const client = useMemo(() => (key ? createClient(key) : null), [key]);

  const signOut = useCallback(() => {
    writeKey(null);
    setKey(null);
    setView("overview");
    setRule(undefined);
  }, []);

  async function connect(candidate: string): Promise<"ok" | "rejected" | "unreachable"> {
    try {
      await createClient(candidate).chain(); // cheap admin-only call: proves the key works
    } catch (err) {
      return err instanceof AuthError ? "rejected" : "unreachable";
    }
    writeKey(candidate);
    setKey(candidate);
    return "ok";
  }

  if (!client) return <KeyGate onConnect={connect} />;

  return (
    <div className="app">
      <header className="topbar">
        <h1>llmguard</h1>
        <div role="tablist" aria-label="Sections">
          <button
            role="tab"
            type="button"
            aria-selected={view === "overview"}
            onClick={() => setView("overview")}
          >
            Overview
          </button>
          <button
            role="tab"
            type="button"
            aria-selected={view === "events"}
            onClick={() => {
              setRule(undefined);
              setView("events");
            }}
          >
            Events
          </button>
        </div>
        <button type="button" className="link-button" onClick={signOut}>
          Sign out
        </button>
      </header>
      <main>
        {view === "overview" ? (
          <Overview
            client={client}
            onAuthError={signOut}
            onOpenRule={(r) => {
              setRule(r);
              setView("events");
            }}
          />
        ) : (
          <EventsView key={rule ?? "all"} client={client} initialRule={rule} onAuthError={signOut} />
        )}
      </main>
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { AuthError } from "./api";

export interface ApiState<T> {
  /** The latest data. Kept while a refetch is in flight, so the screen never blanks. */
  data: T | undefined;
  error: Error | null;
  loading: boolean;
}

/**
 * Runs `load` now and whenever `deps` change. A refetch keeps the previous `data`
 * (the UI dims it) instead of showing a skeleton. A 401/403 is reported through
 * `onAuthError` so the app can send the user back to the key screen.
 */
export function useApiData<T>(
  load: () => Promise<T>,
  deps: readonly unknown[],
  onAuthError: () => void,
): ApiState<T> {
  const [state, setState] = useState<ApiState<T>>({ data: undefined, error: null, loading: true });
  const authRef = useRef(onAuthError);
  authRef.current = onAuthError;

  useEffect(() => {
    let cancelled = false; // ignore answers that arrive after we asked for something newer
    setState((s) => ({ ...s, loading: true }));
    load().then(
      (data) => {
        if (!cancelled) setState({ data, error: null, loading: false });
      },
      (err: unknown) => {
        if (cancelled) return;
        if (err instanceof AuthError) {
          authRef.current();
          return;
        }
        setState((s) => ({
          ...s,
          error: err instanceof Error ? err : new Error("Unknown error"),
          loading: false,
        }));
      },
    );
    return () => {
      cancelled = true;
    };
    // `load` is a fresh closure every render; `deps` says when it actually matters.
  }, deps);

  return state;
}

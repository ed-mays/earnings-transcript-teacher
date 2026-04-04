import { useState, useCallback, useRef } from "react";

interface LazySectionState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  trigger: () => void;
}

/**
 * Lazily fetches data on first trigger() call. Subsequent calls are no-ops —
 * re-expanding a section renders instantly from cached state.
 */
export function useLazySection<T>(fetchFn: () => Promise<T>): LazySectionState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fetchRef = useRef(fetchFn);
  fetchRef.current = fetchFn;
  const hasTriggered = useRef(false);

  const trigger = useCallback(() => {
    if (hasTriggered.current) return;
    hasTriggered.current = true;
    setLoading(true);
    fetchRef.current()
      .then((result) => {
        setData(result);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load");
      })
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error, trigger };
}

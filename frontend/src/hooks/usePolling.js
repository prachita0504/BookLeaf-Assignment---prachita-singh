// Fetches data, then re-fetches every `intervalMs` while the browser tab is visible.
// This is what makes ticket updates appear in near real time without a page refresh.
import { useCallback, useEffect, useRef, useState } from "react";

export default function usePolling(fetcher, intervalMs, deps = []) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const refresh = useCallback(async () => {
    try {
      setData(await fetcherRef.current());
      setError(null);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    refresh();
    const tick = () => document.visibilityState === "visible" && refresh();
    const id = intervalMs ? setInterval(tick, intervalMs) : null;
    document.addEventListener("visibilitychange", tick); // refresh as soon as the user comes back
    return () => {
      if (id) clearInterval(id);
      document.removeEventListener("visibilitychange", tick);
    };
    // `deps` lets callers restart polling when e.g. the filters or the ticket number change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [intervalMs, refresh, ...deps]);

  return { data, setData, error, loading, refresh };
}

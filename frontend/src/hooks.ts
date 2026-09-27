import { useCallback, useEffect, useState, type DependencyList } from "react";
import { useSearchParams } from "react-router-dom";
import { api, type Review } from "./api";

export interface AsyncState<T> {
  data: T | undefined;
  error: Error | undefined;
  loading: boolean;
  reload: () => void;
}

/** Runs fn when deps change; keeps the previous data visible while reloading. */
export function useAsync<T>(fn: () => Promise<T>, deps: DependencyList): AsyncState<T> {
  const [state, setState] = useState<{ data?: T; error?: Error; loading: boolean }>({ loading: true });
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: undefined }));
    fn().then(
      (data) => !cancelled && setState({ data, loading: false }),
      (error: Error) => !cancelled && setState({ error, loading: false }),
    );
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);
  return { data: state.data, error: state.error, loading: state.loading, reload };
}

/** The review shown on the dashboard/findings pages: ?review=<id>, else the latest. */
export function useReviewSelection() {
  const reviews = useAsync(api.reviews, []);
  const [params, setParams] = useSearchParams();
  const requested = Number(params.get("review")) || null;
  const list: Review[] = reviews.data ?? [];
  const selected = list.find((r) => r.id === requested) ?? list[0] ?? null;

  const select = useCallback(
    (id: number) =>
      setParams((p) => {
        p.set("review", String(id));
        p.delete("page");
        return p;
      }),
    [setParams],
  );

  return { reviews: list, selected, loading: reviews.loading, error: reviews.error, reload: reviews.reload, select };
}

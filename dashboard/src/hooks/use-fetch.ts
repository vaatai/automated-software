"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";

interface State<T> {
  data: T | null;
  error: string | null;
  loading: boolean;
}

type Action<T> =
  | { type: "loading" }
  | { type: "success"; data: T }
  | { type: "error"; error: string };

function reducer<T>(state: State<T>, action: Action<T>): State<T> {
  switch (action.type) {
    case "loading":
      return { ...state, loading: true };
    case "success":
      return { data: action.data, error: null, loading: false };
    case "error":
      return { ...state, error: action.error, loading: false };
  }
}

interface UseFetchResult<T> extends State<T> {
  refetch: () => void;
}

export function useFetch<T>(
  fetcher: () => Promise<T>,
  deps: unknown[] = [],
  interval?: number,
): UseFetchResult<T> {
  const [state, dispatch] = useReducer(reducer<T>, {
    data: null,
    error: null,
    loading: true,
  });
  const mountedRef = useRef(true);

  const depsKey = JSON.stringify(deps);
  const fetcherRef = useRef(fetcher);
  const [refetchCount, forceRefetch] = useReducer((x: number) => x + 1, 0);

  useEffect(() => {
    fetcherRef.current = fetcher;
  }, [fetcher]);

  useEffect(() => {
    mountedRef.current = true;
    let cancelled = false;

    async function doFetch() {
      dispatch({ type: "loading" });
      try {
        const result = await fetcherRef.current();
        if (!cancelled && mountedRef.current) {
          dispatch({ type: "success", data: result });
        }
      } catch (e) {
        if (!cancelled && mountedRef.current) {
          dispatch({
            type: "error",
            error: e instanceof Error ? e.message : "Unknown error",
          });
        }
      }
    }

    doFetch();

    return () => {
      cancelled = true;
      mountedRef.current = false;
    };
  }, [depsKey, refetchCount]);

  useEffect(() => {
    if (!interval) return;
    const id = setInterval(() => {
      fetcherRef.current().then(
        (result) => { if (mountedRef.current) dispatch({ type: "success", data: result }); },
        (e) => { if (mountedRef.current) dispatch({ type: "error", error: e instanceof Error ? e.message : "Unknown error" }); },
      );
    }, interval);
    return () => clearInterval(id);
  }, [interval, depsKey]);

  const refetch = useCallback(() => forceRefetch(), [forceRefetch]);

  return { ...state, refetch } as UseFetchResult<T>;
}

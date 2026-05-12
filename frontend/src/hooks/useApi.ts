import { useState, useCallback } from "react";
import { AxiosError } from "axios";

interface UseApiState<T> {
  data: T | null;
  isLoading: boolean;
  error: Error | AxiosError | null;
  isSuccess: boolean;
}

export function useApi<T, Args extends unknown[] = unknown[]>(
  apiFunction: (...args: Args) => Promise<T>,
  initialData: T | null = null
) {
  const [state, setState] = useState<UseApiState<T>>({
    data: initialData,
    isLoading: false,
    error: null,
    isSuccess: false,
  });

  const execute = useCallback(
    async (...args: Args): Promise<T | null> => {
      setState((prev) => ({ ...prev, isLoading: true, error: null, isSuccess: false }));
      try {
        const result = await apiFunction(...args);
        setState({ data: result, isLoading: false, error: null, isSuccess: true });
        return result;
      } catch (error) {
        setState((prev) => ({
          ...prev,
          isLoading: false,
          error: error as Error | AxiosError,
          isSuccess: false,
        }));
        return null;
      }
    },
    [apiFunction]
  );

  const reset = useCallback(() => {
    setState({ data: initialData, isLoading: false, error: null, isSuccess: false });
  }, [initialData]);

  return {
    ...state,
    execute,
    reset,
    // Helper to manually set data (e.g. optimistic updates)
    setData: (data: T) => setState((prev) => ({ ...prev, data })),
  };
}

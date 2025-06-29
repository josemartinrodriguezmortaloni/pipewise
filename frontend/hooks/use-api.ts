"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { toast } from "sonner";
import { tokenStorage } from "@/lib/auth";
import { useAuth } from "./use-auth";

interface UseApiOptions<T> {
  onSuccess?: (data: T) => void;
  onError?: (error: Error) => void;
}

export function useApi<T>(
  endpoint: string,
  options: RequestInit = {},
  handlers: UseApiOptions<T> = {}
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const { token, logout } = useAuth();

  const handlersRef = useRef(handlers);

  useEffect(() => {
    handlersRef.current = handlers;
  }, [handlers]);

  const execute = useCallback(
    async (dynamicEndpoint?: string, body?: any) => {
      setLoading(true);
      setError(null);

      const finalEndpoint = dynamicEndpoint || endpoint;
      const apiUrl = `/api/v1${finalEndpoint}`;

      if (!token) {
        const err = new Error("No access token found. Please log in.");
        setError(err);
        toast.error(err.message);
        if (handlersRef.current.onError) handlersRef.current.onError(err);
        return;
      }

      try {
        const response = await fetch(apiUrl, {
          ...options,
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
            ...options.headers,
          },
          body: body ? JSON.stringify(body) : undefined,
        });

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(
            errorData.detail || `Request failed: ${response.status}`
          );
        }

        const result: T = await response.json();
        setData(result);
        if (handlersRef.current.onSuccess) {
          handlersRef.current.onSuccess(result);
        }
        return result;
      } catch (err: any) {
        setError(err);
        toast.error(err.message || "An unexpected error occurred.");
        if (handlersRef.current.onError) {
          handlersRef.current.onError(err);
        }
      } finally {
        setLoading(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [endpoint, JSON.stringify(options), token]
  );

  return { data, loading, error, execute };
}

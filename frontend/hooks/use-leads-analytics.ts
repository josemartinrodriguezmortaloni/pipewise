import { useState, useEffect } from "react";

interface LeadsAnalyticsData {
  date: string;
  web_leads: number;
  social_leads: number;
  total_leads: number;
}

interface LeadsAnalyticsResponse {
  data: LeadsAnalyticsData[];
  timerange: string;
  total_days: number;
  date_range: {
    start: string;
    end: string;
  };
}

interface UseLeadsAnalyticsResult {
  data: LeadsAnalyticsData[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useLeadsAnalytics(
  timerange: string = "90d"
): UseLeadsAnalyticsResult {
  const [data, setData] = useState<LeadsAnalyticsData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch(
        `/api/analytics/leads?timerange=${timerange}`
      );

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const result: LeadsAnalyticsResponse = await response.json();
      setData(result.data);
    } catch (err) {
      console.error("Error fetching leads analytics:", err);
      setError(
        err instanceof Error ? err.message : "Failed to fetch leads analytics"
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    fetchData(controller.signal);

    return () => controller.abort();
  }, [timerange]);

  const refetch = () => {
    fetchData();
  };

  return {
    data,
    loading,
    error,
    refetch,
  };
}

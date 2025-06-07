import { useEffect, useState } from "react";

// Tipos
interface Lead {
  id: string;
  name: string;
  email: string;
  company: string;
  phone?: string;
  status: string;
  qualified: boolean;
  contacted: boolean;
  meeting_scheduled: boolean;
  source?: string;
  owner_id?: string;
  created_at: string;
  updated_at?: string;
}

interface LeadsResponse {
  leads: Lead[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

interface UseLeadsOptions {
  page?: number;
  per_page?: number;
  status_filter?: string;
  refreshInterval?: number;
}

interface UseLeadsReturn {
  leads: Lead[];
  total: number;
  page: number;
  totalPages: number;
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

const REFRESH_INTERVAL_MS = 5_000; // 5 segundos

/**
 * Hook para gestionar leads desde la API
 */
export function useLeads(options: UseLeadsOptions = {}): UseLeadsReturn {
  const {
    page = 1,
    per_page = 50,
    status_filter,
    refreshInterval = REFRESH_INTERVAL_MS,
  } = options;

  const [leads, setLeads] = useState<Lead[]>([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /**
   * Función para obtener leads desde la API
   */
  const fetchLeads = async (): Promise<void> => {
    try {
      setError(null);

      // Construir URL con parámetros
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: per_page.toString(),
      });

      if (status_filter) {
        params.append("status_filter", status_filter);
      }

      const response = await fetch(`/api/leads?${params}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          // En producción, añadir: 'Authorization': `Bearer ${token}`
        },
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data: LeadsResponse = await response.json();

      setLeads(data.leads);
      setTotal(data.total);
      setTotalPages(data.total_pages);
    } catch (err) {
      console.error("Error fetching leads:", err);
      setError(err instanceof Error ? err.message : "Unknown error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  // Cargar datos iniciales y configurar polling
  useEffect(() => {
    fetchLeads();

    // Configurar polling si refreshInterval > 0
    let intervalId: NodeJS.Timeout | null = null;

    if (refreshInterval > 0) {
      intervalId = setInterval(fetchLeads, refreshInterval);
    }

    // Cleanup
    return () => {
      if (intervalId) {
        clearInterval(intervalId);
      }
    };
  }, [page, per_page, status_filter, refreshInterval]);

  return {
    leads,
    total,
    page,
    totalPages,
    isLoading,
    error,
    refetch: fetchLeads,
  };
}

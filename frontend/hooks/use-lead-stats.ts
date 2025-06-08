import { useEffect, useState } from "react";
import { authenticatedFetch } from "@/lib/auth";

// Interfaces
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
  updated_at?: string | null;
}

interface LeadStats {
  totalLeads: number;
  contactedLeads: number;
  qualifiedLeads: number;
  meetingsScheduled: number;
  contactRate: number;
  qualificationRate: number;
  meetingRate: number;
  automationImpact: {
    messagesAutomated: number;
    timesSaved: number; // in hours
    costSavings: number; // in USD
  };
  isLoading: boolean;
  error: string | null;
}

const REFRESH_INTERVAL_MS = 30_000; // 30 seconds

/**
 * Hook para obtener estadísticas de leads y métricas de automatización
 */
export function useLeadStats(): LeadStats {
  const [stats, setStats] = useState<Omit<LeadStats, "isLoading" | "error">>({
    totalLeads: 0,
    contactedLeads: 0,
    qualifiedLeads: 0,
    meetingsScheduled: 0,
    contactRate: 0,
    qualificationRate: 0,
    meetingRate: 0,
    automationImpact: {
      messagesAutomated: 0,
      timesSaved: 0,
      costSavings: 0,
    },
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = async (): Promise<void> => {
    try {
      setError(null);

      // Obtener leads desde la API
      const response = await authenticatedFetch("/api/leads?per_page=1000");

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      const leads: Lead[] = data.leads || [];

      // Calcular estadísticas
      const totalLeads = leads.length;
      const contactedLeads = leads.filter((lead) => lead.contacted).length;
      const qualifiedLeads = leads.filter((lead) => lead.qualified).length;
      const meetingsScheduled = leads.filter(
        (lead) => lead.meeting_scheduled
      ).length;

      // Calcular rates (porcentajes)
      const contactRate =
        totalLeads > 0 ? (contactedLeads / totalLeads) * 100 : 0;
      const qualificationRate =
        contactedLeads > 0 ? (qualifiedLeads / contactedLeads) * 100 : 0;
      const meetingRate =
        qualifiedLeads > 0 ? (meetingsScheduled / qualifiedLeads) * 100 : 0;

      // Calcular impacto de automatización
      // Asumiendo que cada lead contactado = 1 mensaje automático + tiempo ahorrado
      const messagesAutomated = contactedLeads;
      const timesSaved = contactedLeads * 0.5; // 30 minutos por lead
      const costSavings = timesSaved * 25; // $25/hora ahorrada

      setStats({
        totalLeads,
        contactedLeads,
        qualifiedLeads,
        meetingsScheduled,
        contactRate: Math.round(contactRate * 10) / 10, // 1 decimal
        qualificationRate: Math.round(qualificationRate * 10) / 10,
        meetingRate: Math.round(meetingRate * 10) / 10,
        automationImpact: {
          messagesAutomated,
          timesSaved: Math.round(timesSaved * 10) / 10,
          costSavings: Math.round(costSavings),
        },
      });
    } catch (err: any) {
      if (err?.name === "AbortError") return;
      console.error("Error fetching lead stats:", err);
      setError(err instanceof Error ? err.message : "Unknown error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();

    // Configurar polling
    const intervalId = setInterval(fetchStats, REFRESH_INTERVAL_MS);

    return () => {
      clearInterval(intervalId);
    };
  }, []);

  return {
    ...stats,
    isLoading,
    error,
  };
}

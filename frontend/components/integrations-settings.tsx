"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { useRouter, useSearchParams } from "next/navigation";

import {
  ALL_INTEGRATIONS,
  getIntegrationByKey,
} from "@/lib/integrations-config";
import { OAuthIntegrationCard } from "@/components/oauth-integration-card";
import { api } from "@/lib/api";

interface UserAccount {
  account_id: string;
  account_type: string;
  connection_type: "oauth";
  configuration: any;
  connected: boolean;
  created_at: string;
}

export function IntegrationsSettings() {
  const [accounts, setAccounts] = useState<UserAccount[]>([]);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const searchParams = useSearchParams();

  // Check for OAuth callback success/error
  useEffect(() => {
    const success = searchParams.get("success");
    const error = searchParams.get("error");
    const connected = searchParams.get("connected");

    if (success) {
      const integration = getIntegrationByKey(success);
      toast.success(`${integration?.name || success} conectado exitosamente`);
      // Clean up URL
      router.replace("/integrations");
    }

    if (error) {
      const integration = getIntegrationByKey(error);
      toast.error(`Error conectando ${integration?.name || error}`);
      // Clean up URL
      router.replace("/integrations");
    }

    if (connected) {
      // Refresh accounts after OAuth connection
      loadUserAccounts();
    }
  }, [searchParams, router]);

  // Load existing account configurations
  useEffect(() => {
    loadUserAccounts();
  }, []);

  const loadUserAccounts = async () => {
    try {
      setLoading(true);
      // Usar la API autenticada con la ruta corregida
      const data = await api.get("/api/user/integrations/accounts");
      // El backend ahora retorna un array plano de cuentas
      // Mapear a la estructura esperada por el frontend
      const mappedAccounts = (Array.isArray(data) ? data : []).map(
        (acc: any) => ({
          account_id: `oauth_${acc.service}`,
          account_type: acc.service,
          connection_type: "oauth" as const,
          configuration: { profile: acc.profile_data || {} },
          connected: !!acc.connected,
          created_at: acc.connected_at,
        })
      );
      setAccounts(mappedAccounts);
    } catch (error) {
      console.error("Error loading accounts:", error);
      toast.error("Error cargando configuraciones de cuentas");
    } finally {
      setLoading(false);
    }
  };

  const getAccountForIntegration = (
    integrationKey: string
  ): UserAccount | undefined => {
    return accounts.find(
      (account) =>
        account.account_type === integrationKey ||
        account.account_id === `oauth_${integrationKey}`
    );
  };

  const renderIntegrationsByCategory = (category: string) => {
    const categoryIntegrations = ALL_INTEGRATIONS.filter(
      (integration) => integration.category === category
    );

    if (categoryIntegrations.length === 0) return null;

    const getCategoryIcon = (cat: string) => {
      switch (cat) {
        case "calendar":
          return "📅";
        case "email":
          return "📧";
        case "social":
          return "📱";
        case "crm":
          return "🏢";
        case "automation":
          return "⚙️";
        default:
          return "🔗";
      }
    };

    const getCategoryName = (cat: string) => {
      switch (cat) {
        case "calendar":
          return "Calendario";
        case "email":
          return "Email";
        case "social":
          return "Redes Sociales";
        case "crm":
          return "CRM";
        case "automation":
          return "Automatización";
        default:
          return "Otros";
      }
    };

    return (
      <div key={`category-${category}`} className="space-y-4">
        <h4 className="text-md font-medium">
          {getCategoryIcon(category)} {getCategoryName(category)}
        </h4>
        <div className="grid gap-6 md:grid-cols-2">
          {categoryIntegrations.map((integration) => {
            const account = getAccountForIntegration(integration.key);
            const isConnected = account?.connected || false;

            return (
              <OAuthIntegrationCard
                key={`oauth-${integration.key}`}
                integration={integration}
                isConnected={isConnected}
                connectionData={{
                  connected_at: account?.created_at,
                  profile: account?.configuration?.profile,
                }}
                onConnectionUpdate={loadUserAccounts}
              />
            );
          })}
        </div>
      </div>
    );
  };

  const categories = ["calendar", "crm", "email", "social", "automation"];

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-lg font-semibold">
          Configuración de Integraciones
        </h3>
        <p className="text-sm text-muted-foreground">
          Conecta tus cuentas y servicios para automatizar la gestión de leads y
          comunicaciones usando OAuth 2.0.
        </p>
      </div>

      <div className="space-y-8">
        <div>
          <h4 className="text-md font-medium mb-2">🔐 Conexiones OAuth</h4>
          <p className="text-sm text-muted-foreground mb-6">
            Conecta con un solo clic usando OAuth 2.0. Estas integraciones se
            autentican de forma segura sin necesidad de compartir credenciales.
          </p>

          {categories.map((category) => renderIntegrationsByCategory(category))}
        </div>
      </div>
    </div>
  );
}

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
      toast.success(`${integration?.name || success} connected successfully`);
      // Clean up URL
      router.replace("/integrations");
    }

    if (error) {
      const integration = getIntegrationByKey(error);
      toast.error(`Error connecting ${integration?.name || error}`);
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
      // Use authenticated API with the corrected route
      const data = await api.get("/api/user/integrations/accounts");
      // The backend now returns a flat array of accounts
      // Map to the structure expected by the frontend
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
      toast.error("Error loading account configurations");
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
          return "Calendar";
        case "email":
          return "Email";
        case "social":
          return "Social Media";
        case "crm":
          return "CRM";
        case "automation":
          return "Automation";
        default:
          return "Other";
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
        <h3 className="text-lg font-semibold">Integration Settings</h3>
        <p className="text-sm text-muted-foreground">
          Connect your accounts and services to automate lead management and
          communications using OAuth 2.0.
        </p>
      </div>

      <div className="space-y-8">
        <div>
          <h4 className="text-md font-medium mb-2">🔐 OAuth Connections</h4>
          <p className="text-sm text-muted-foreground mb-6">
            Connect with one click using OAuth 2.0. These integrations
            authenticate securely without the need to share credentials.
          </p>

          {categories.map((category) => renderIntegrationsByCategory(category))}
        </div>
      </div>
    </div>
  );
}

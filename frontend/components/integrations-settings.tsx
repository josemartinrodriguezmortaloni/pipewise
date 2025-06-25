"use client";

import * as React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
  IconPlug,
  IconCheck,
  IconSettings,
  IconCalendar,
  IconBuilding,
  IconDatabase,
  IconMail,
} from "@tabler/icons-react";

interface Integration {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  status: "connected" | "disconnected" | "error";
  category: "calendar" | "crm" | "email";
  features: string[];
  isPremium?: boolean;
}

// Business tool integrations
const businessIntegrations: Integration[] = [
  {
    id: "google_calendar",
    name: "Google Calendar",
    description: "Schedule meetings and manage calendar events seamlessly",
    icon: IconCalendar,
    status: "disconnected",
    category: "calendar",
    features: [
      "Meeting scheduling",
      "Calendar sync",
      "Availability checks",
      "Automated invites",
    ],
  },
  {
    id: "calendly_v2",
    name: "Calendly",
    description: "Professional meeting scheduling and booking system",
    icon: IconCalendar,
    status: "disconnected",
    category: "calendar",
    features: [
      "Automated booking",
      "Custom scheduling",
      "Meeting links",
      "Timezone handling",
    ],
  },
  {
    id: "pipedrive",
    name: "Pipedrive",
    description: "Complete CRM solution for lead and deal management",
    icon: IconDatabase,
    status: "disconnected",
    category: "crm",
    features: [
      "Lead management",
      "Pipeline tracking",
      "Contact sync",
      "Sales reporting",
    ],
  },
  {
    id: "salesforce_rest_api",
    name: "Salesforce",
    description: "Enterprise CRM platform with advanced lead scoring",
    icon: IconBuilding,
    status: "disconnected",
    category: "crm",
    features: [
      "Enterprise CRM",
      "Lead scoring",
      "Account management",
      "Advanced analytics",
    ],
    isPremium: true,
  },
  {
    id: "zoho_crm",
    name: "Zoho CRM",
    description: "Comprehensive CRM solution for growing businesses",
    icon: IconDatabase,
    status: "disconnected",
    category: "crm",
    features: [
      "Contact management",
      "Deal tracking",
      "Lead automation",
      "Sales pipeline",
    ],
  },
  {
    id: "sendgrid",
    name: "SendGrid",
    description: "Professional email automation and delivery platform",
    icon: IconMail,
    status: "disconnected",
    category: "email",
    features: [
      "Email automation",
      "Template management",
      "Delivery tracking",
      "Analytics dashboard",
    ],
  },
];

export function IntegrationsSettings() {
  const [loading, setLoading] = React.useState<Record<string, boolean>>({});
  const [connectedIntegrations, setConnectedIntegrations] = React.useState<
    Set<string>
  >(new Set());

  // Load connected integrations status
  React.useEffect(() => {
    const loadConnectedIntegrations = async () => {
      try {
        const response = await fetch("/api/integrations/");

        if (response.ok) {
          const data = await response.json();
          const connected = new Set<string>();
          data.integrations?.forEach(
            (integration: { id: string; status: string }) => {
              if (integration.status === "connected") {
                connected.add(integration.id);
              }
            }
          );
          setConnectedIntegrations(connected);
        }
      } catch (error) {
        console.error("Error loading integrations:", error);
      }
    };

    loadConnectedIntegrations();
  }, []);

  const handleConnect = async (integration: Integration) => {
    setLoading((prev) => ({ ...prev, [integration.id]: true }));

    try {
      const endpoint = `/api/integrations/mcp/${integration.id}/enable`;

      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          enabled: true,
          integration_type: "business_tool",
        }),
      });

      if (!response.ok) {
        let errorMessage = `Failed to connect ${integration.name}`;
        try {
          const errorData = await response.json();
          if (errorData.detail) {
            errorMessage =
              typeof errorData.detail === "string"
                ? errorData.detail
                : JSON.stringify(errorData.detail);
          }
        } catch {
          errorMessage = `${response.status} ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const result = await response.json();

      if (result.success) {
        setConnectedIntegrations((prev) => new Set([...prev, integration.id]));
        console.log(`${integration.name} connected successfully:`, result);
      } else {
        throw new Error(
          result.message || `Failed to connect ${integration.name}`
        );
      }
    } catch (error) {
      console.error(`Error connecting ${integration.name}:`, error);
      let errorMessage = "Unknown error";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      alert(`Failed to connect ${integration.name}: ${errorMessage}`);
    } finally {
      setLoading((prev) => ({ ...prev, [integration.id]: false }));
    }
  };

  const handleDisconnect = async (integration: Integration) => {
    setLoading((prev) => ({ ...prev, [integration.id]: true }));

    try {
      const endpoint = `/api/integrations/mcp/${integration.id}/disable`;

      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          enabled: false,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to disconnect ${integration.name}`);
      }

      setConnectedIntegrations((prev) => {
        const newSet = new Set(prev);
        newSet.delete(integration.id);
        return newSet;
      });

      console.log(`${integration.name} disconnected successfully`);
    } catch (error) {
      console.error(`Error disconnecting ${integration.name}:`, error);
      alert(`Failed to disconnect ${integration.name}`);
    } finally {
      setLoading((prev) => ({ ...prev, [integration.id]: false }));
    }
  };

  const getCategoryColor = (category: Integration["category"]) => {
    return "border-gray-200 bg-gray-50 text-gray-700";
  };

  const renderIntegrationCard = (integration: Integration) => {
    const isConnected = connectedIntegrations.has(integration.id);
    const isLoading = loading[integration.id];

    return (
      <Card
        key={integration.id}
        className={`border border-gray-200 bg-white shadow-sm transition-shadow duration-200 hover:shadow-md ${
          isConnected ? "ring-1 ring-gray-300 bg-gray-50" : ""
        }`}
      >
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-lg border ${
                  isConnected
                    ? "border-gray-300 bg-gray-100"
                    : "border-gray-200 bg-gray-50"
                }`}
              >
                <integration.icon
                  className={`h-5 w-5 ${
                    isConnected ? "text-gray-700" : "text-gray-500"
                  }`}
                />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <CardTitle className="text-base text-gray-900">
                    {integration.name}
                  </CardTitle>
                  {integration.isPremium && (
                    <Badge className="text-xs border-gray-300 bg-gray-100 text-gray-800">
                      Premium
                    </Badge>
                  )}
                </div>
                <Badge
                  variant="outline"
                  className={`text-xs ${getCategoryColor(
                    integration.category
                  )}`}
                >
                  {integration.category}
                </Badge>
              </div>
            </div>
            {isConnected && <IconCheck className="h-5 w-5 text-gray-600" />}
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-gray-600">{integration.description}</p>

          <div className="space-y-2">
            <div className="text-xs font-medium text-gray-500 uppercase tracking-wide">
              Features
            </div>
            <div className="flex flex-wrap gap-1">
              {integration.features.slice(0, 3).map((feature, idx) => (
                <Badge
                  key={idx}
                  variant="outline"
                  className="text-xs border-gray-200 bg-white text-gray-600"
                >
                  {feature}
                </Badge>
              ))}
              {integration.features.length > 3 && (
                <Badge
                  variant="outline"
                  className="text-xs border-gray-200 bg-white text-gray-600"
                >
                  +{integration.features.length - 3} more
                </Badge>
              )}
            </div>
          </div>

          <div className="pt-2">
            {isConnected ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleDisconnect(integration)}
                disabled={isLoading}
                className="w-full border-gray-200 bg-white text-gray-700 hover:bg-gray-50"
              >
                {isLoading ? "Disconnecting..." : "Disconnect"}
              </Button>
            ) : (
              <Button
                onClick={() => handleConnect(integration)}
                disabled={isLoading}
                className="w-full bg-gray-900 text-white hover:bg-gray-800"
                size="sm"
              >
                {isLoading ? "Connecting..." : "Connect"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  // Calculate metrics for connected integrations
  const connectedCount = businessIntegrations.filter((i) =>
    connectedIntegrations.has(i.id)
  ).length;

  const calendarConnected = businessIntegrations.filter(
    (i) => i.category === "calendar" && connectedIntegrations.has(i.id)
  ).length;

  const crmConnected = businessIntegrations.filter(
    (i) => i.category === "crm" && connectedIntegrations.has(i.id)
  ).length;

  return (
    <div className="space-y-8">
      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="border border-gray-200 bg-white shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <IconPlug className="h-5 w-5 text-gray-600" />
              <span className="text-sm font-medium text-gray-700">
                Connected Tools
              </span>
            </div>
            <div className="mt-2">
              <span className="text-2xl font-semibold text-gray-900">
                {connectedCount}
              </span>
              <span className="text-gray-500 text-sm ml-1">
                / {businessIntegrations.length} available
              </span>
            </div>
          </CardContent>
        </Card>
        <Card className="border border-gray-200 bg-white shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <IconCalendar className="h-5 w-5 text-gray-600" />
              <span className="text-sm font-medium text-gray-700">
                Calendar
              </span>
            </div>
            <div className="mt-2">
              <span className="text-2xl font-semibold text-gray-900">
                {calendarConnected}
              </span>
              <span className="text-gray-500 text-sm ml-1">connected</span>
            </div>
          </CardContent>
        </Card>
        <Card className="border border-gray-200 bg-white shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <IconDatabase className="h-5 w-5 text-gray-600" />
              <span className="text-sm font-medium text-gray-700">CRM</span>
            </div>
            <div className="mt-2">
              <span className="text-2xl font-semibold text-gray-900">
                {crmConnected}
              </span>
              <span className="text-gray-500 text-sm ml-1">connected</span>
            </div>
          </CardContent>
        </Card>
        <Card className="border border-gray-200 bg-white shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <IconCheck className="h-5 w-5 text-gray-600" />
              <span className="text-sm font-medium text-gray-700">Status</span>
            </div>
            <div className="mt-2">
              <span className="text-2xl font-semibold text-gray-900">
                Ready
              </span>
              <span className="text-gray-500 text-sm ml-1">to connect</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Business Tools Section */}
      <div className="space-y-6">
        <Card className="border border-gray-200 bg-white shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-gray-200 bg-gray-50">
                <IconPlug className="h-6 w-6 text-gray-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-lg mb-2 text-gray-900">
                  Business Tool Integrations
                </h3>
                <p className="text-gray-600 mb-4">
                  Connect your essential business tools to streamline your lead
                  qualification and management workflow. Sync data automatically
                  and enhance productivity.
                </p>
                <div className="flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-2">
                    <IconCheck className="h-4 w-4 text-gray-600" />
                    <span className="text-gray-600">Secure connections</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <IconCheck className="h-4 w-4 text-gray-600" />
                    <span className="text-gray-600">Real-time sync</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <IconCheck className="h-4 w-4 text-gray-600" />
                    <span className="text-gray-600">Easy setup</span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {businessIntegrations.map(renderIntegrationCard)}
        </div>
      </div>

      {/* Settings Section */}
      <Card className="border border-gray-200 bg-gray-50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-gray-900">
            <IconSettings className="h-5 w-5" />
            Integration Settings
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-gray-600 leading-relaxed">
            Configure how your business tools sync data and interact with your
            lead qualification system. All connections are secured with
            enterprise-grade encryption.
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label className="text-sm font-medium text-gray-700">
                  Auto-sync data
                </Label>
                <p className="text-xs text-gray-500">
                  Automatically sync lead data from connected tools
                </p>
              </div>
              <Checkbox defaultChecked />
            </div>
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label className="text-sm font-medium text-gray-700">
                  Real-time notifications
                </Label>
                <p className="text-xs text-gray-500">
                  Get notified when data syncs between tools
                </p>
              </div>
              <Checkbox defaultChecked />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

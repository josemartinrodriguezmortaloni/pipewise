"use client";

import * as React from "react";
import {
  IconBrandInstagram,
  IconBrandTwitter,
  IconBrandWhatsapp,
  IconCalendar,
  IconCheck,
  IconMail,
  IconPlug,
  IconSettings,
  IconShield,
  IconDatabase,
  IconBuildingStore,
  IconBrandGoogle,
  IconLoader,
  IconExternalLink,
  IconArrowRight,
  IconRobot,
  IconSparkles,
} from "@tabler/icons-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

interface Integration {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  status: "connected" | "disconnected" | "error";
  category: "calendar" | "social" | "messaging" | "email" | "crm" | "mcp";
  features: string[];
  requiresApi: boolean;
  apiKeyLabel?: string;
  webhookUrl?: string;
  toolsCount?: number;
  isOneClick?: boolean;
  isPopular?: boolean;
  isPremium?: boolean;
}

// Modern integrations with MCP support
const mcpIntegrations: Integration[] = [
  {
    id: "calendly_v2",
    name: "Calendly",
    description:
      "Schedule meetings and manage calendar availability automatically through AI agents",
    icon: IconCalendar,
    status: "disconnected",
    category: "mcp",
    features: [
      "Automated meeting scheduling",
      "Calendar availability checks",
      "Meeting link generation",
      "Timezone handling",
      "Event type management",
      "Booking confirmations",
      "Reschedule requests",
    ],
    requiresApi: false,
    toolsCount: 7,
    isOneClick: true,
    isPopular: true,
    isPremium: false,
  },
  {
    id: "pipedrive",
    name: "Pipedrive",
    description:
      "Complete CRM integration for lead management, deal tracking, and sales pipeline automation",
    icon: IconDatabase,
    status: "disconnected",
    category: "mcp",
    features: [
      "Lead creation and updates",
      "Deal pipeline management",
      "Contact synchronization",
      "Activity tracking",
      "Custom field mapping",
      "Sales reporting",
      "Automation workflows",
    ],
    requiresApi: false,
    toolsCount: 37,
    isOneClick: true,
    isPopular: true,
    isPremium: false,
  },
  {
    id: "salesforce_rest_api",
    name: "Salesforce",
    description:
      "Enterprise CRM integration with advanced lead scoring and opportunity management",
    icon: IconBuildingStore,
    status: "disconnected",
    category: "mcp",
    features: [
      "Enterprise lead management",
      "Opportunity tracking",
      "Account management",
      "Custom objects support",
      "Advanced reporting",
      "Workflow automation",
      "Territory management",
    ],
    requiresApi: false,
    toolsCount: 30,
    isOneClick: true,
    isPopular: false,
    isPremium: true,
  },
  {
    id: "zoho_crm",
    name: "Zoho CRM",
    description:
      "Comprehensive CRM solution for small to medium businesses with AI-powered insights",
    icon: IconDatabase,
    status: "disconnected",
    category: "mcp",
    features: [
      "Lead capture automation",
      "Contact management",
      "Deal tracking",
      "Email campaigns",
      "Sales analytics",
      "Mobile access",
      "Integration workflows",
    ],
    requiresApi: false,
    toolsCount: 11,
    isOneClick: true,
    isPopular: false,
    isPremium: false,
  },
  {
    id: "sendgrid",
    name: "SendGrid",
    description:
      "Professional email automation and delivery with advanced analytics and templates",
    icon: IconMail,
    status: "disconnected",
    category: "mcp",
    features: [
      "Automated email sequences",
      "Template management",
      "Delivery optimization",
      "Analytics & tracking",
      "A/B testing",
      "Bounce handling",
      "Suppression lists",
    ],
    requiresApi: false,
    toolsCount: 20,
    isOneClick: true,
    isPopular: true,
    isPremium: false,
  },
  {
    id: "google_calendar",
    name: "Google Calendar",
    description:
      "Calendar management and meeting coordination with Google Workspace integration",
    icon: IconBrandGoogle,
    status: "disconnected",
    category: "mcp",
    features: [
      "Calendar synchronization",
      "Event creation",
      "Availability checking",
      "Meeting invitations",
      "Recurring events",
      "Timezone support",
      "Mobile notifications",
    ],
    requiresApi: false,
    toolsCount: 10,
    isOneClick: true,
    isPopular: true,
    isPremium: false,
  },
];

// Legacy integrations that require API keys
const legacyIntegrations: Integration[] = [
  {
    id: "whatsapp",
    name: "WhatsApp Business",
    description: "Connect with leads through WhatsApp messaging",
    icon: IconBrandWhatsapp,
    status: "disconnected",
    category: "messaging",
    features: ["Direct messaging", "Media sharing", "Business profiles"],
    requiresApi: true,
    apiKeyLabel: "WhatsApp Business API Token",
    isOneClick: false,
    isPopular: true,
    isPremium: false,
  },
  {
    id: "instagram",
    name: "Instagram",
    description: "Capture leads from Instagram DMs and comments",
    icon: IconBrandInstagram,
    status: "disconnected",
    category: "social",
    features: ["DM automation", "Comment tracking", "Story interactions"],
    requiresApi: true,
    apiKeyLabel: "Instagram Access Token",
    isOneClick: false,
    isPopular: true,
    isPremium: false,
  },
  {
    id: "twitter",
    name: "Twitter/X",
    description: "Engage with prospects on Twitter and X platform",
    icon: IconBrandTwitter,
    status: "disconnected",
    category: "social",
    features: ["Tweet monitoring", "DM automation", "Mention tracking"],
    requiresApi: true,
    apiKeyLabel: "Twitter API Bearer Token",
    isOneClick: false,
    isPopular: false,
    isPremium: false,
  },
];

export function IntegrationsSettings() {
  const [apiKeys, setApiKeys] = React.useState<Record<string, string>>({});
  const [loading, setLoading] = React.useState<Record<string, boolean>>({});
  const [connectedIntegrations, setConnectedIntegrations] = React.useState<
    Set<string>
  >(new Set());
  const [activeTab, setActiveTab] = React.useState("mcp");

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

  const handleApiKeyChange = (integrationId: string, value: string) => {
    setApiKeys((prev) => ({
      ...prev,
      [integrationId]: value,
    }));
  };

  const handleOneClickConnect = async (integration: Integration) => {
    setLoading((prev) => ({ ...prev, [integration.id]: true }));

    try {
      // For MCP integrations, we just need to enable them
      const endpoint = `/api/integrations/mcp/${integration.id}/enable`;

      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          enabled: true,
          integration_type: "mcp",
          tools_count: integration.toolsCount,
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
        // Mark as connected
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

  const handleConnect = async (integration: Integration) => {
    if (integration.isOneClick) {
      return handleOneClickConnect(integration);
    }

    setLoading((prev) => ({ ...prev, [integration.id]: true }));

    try {
      const apiKey = apiKeys[integration.id];
      if (!apiKey) {
        alert("Please enter your API key first");
        setLoading((prev) => ({ ...prev, [integration.id]: false }));
        return;
      }

      // Prepare request based on integration type
      const endpoint = `/api/integrations/${integration.id}/connect`;
      let payload: Record<string, string | boolean> = {};

      if (integration.id === "calendly") {
        payload = {
          name: integration.name,
          enabled: true,
          access_token: apiKey,
          default_event_type: "Sales Call",
          timezone: "UTC",
        };
      } else if (integration.id === "whatsapp") {
        payload = {
          name: "WhatsApp Business",
          enabled: true,
          api_key: apiKey,
        };
      } else {
        // Generic payload for other integrations
        payload = {
          name: integration.name,
          enabled: true,
          api_key: apiKey,
        };
      }

      // Make actual API call to backend
      const response = await fetch(endpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        let errorMessage = `Failed to connect ${integration.name}`;
        try {
          const errorData = await response.json();
          if (errorData.detail) {
            if (Array.isArray(errorData.detail)) {
              errorMessage = errorData.detail
                .map(
                  (err: { loc?: string[]; msg: string }) =>
                    `${err.loc?.join(".")} - ${err.msg}`
                )
                .join(", ");
            } else if (typeof errorData.detail === "string") {
              errorMessage = errorData.detail;
            } else {
              errorMessage = JSON.stringify(errorData.detail);
            }
          }
        } catch {
          errorMessage = `${response.status} ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const result = await response.json();

      if (result.success) {
        // Mark as connected
        setConnectedIntegrations((prev) => new Set([...prev, integration.id]));

        // Clear the API key input for security
        setApiKeys((prev) => ({
          ...prev,
          [integration.id]: "",
        }));

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
      const endpoint = integration.isOneClick
        ? `/api/integrations/mcp/${integration.id}/disable`
        : `/api/integrations/${integration.id}`;

      const method = integration.isOneClick ? "POST" : "DELETE";

      const response = await fetch(endpoint, {
        method,
        headers: {
          "Content-Type": "application/json",
        },
        body: integration.isOneClick
          ? JSON.stringify({ enabled: false })
          : undefined,
      });

      if (!response.ok) {
        let errorMessage = `Failed to disconnect ${integration.name}`;
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
        // Mark as disconnected
        setConnectedIntegrations((prev) => {
          const newSet = new Set(prev);
          newSet.delete(integration.id);
          return newSet;
        });

        console.log(`${integration.name} disconnected successfully`);
      } else {
        throw new Error(
          result.message || `Failed to disconnect ${integration.name}`
        );
      }
    } catch (error) {
      console.error(`Error disconnecting ${integration.name}:`, error);
      let errorMessage = "Unknown error";
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      alert(`Failed to disconnect ${integration.name}: ${errorMessage}`);
    } finally {
      setLoading((prev) => ({ ...prev, [integration.id]: false }));
    }
  };

  const getCategoryColor = (category: Integration["category"]) => {
    switch (category) {
      case "calendar":
        return "text-blue-600";
      case "social":
        return "text-purple-600";
      case "messaging":
        return "text-green-600";
      case "email":
        return "text-orange-600";
      case "crm":
        return "text-red-600";
      case "mcp":
        return "text-indigo-600";
      default:
        return "text-gray-600";
    }
  };

  const renderIntegrationCard = (integration: Integration) => {
    const Icon = integration.icon;
    const isConnected = connectedIntegrations.has(integration.id);
    const isLoading = loading[integration.id];

    return (
      <Card
        key={integration.id}
        className={`relative transition-all hover:shadow-lg ${
          isConnected ? "ring-2 ring-green-500/20 bg-green-50/50" : ""
        }`}
      >
        {integration.isPopular && (
          <div className="absolute -top-2 -right-2 z-10">
            <Badge className="bg-gradient-to-r from-purple-500 to-pink-500 text-white">
              Popular
            </Badge>
          </div>
        )}

        {integration.isPremium && (
          <div className="absolute -top-2 -left-2 z-10">
            <Badge className="bg-gradient-to-r from-yellow-500 to-orange-500 text-white">
              <IconSparkles className="h-3 w-3 mr-1" />
              Premium
            </Badge>
          </div>
        )}

        <CardHeader className="space-y-4">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div
                className={`flex h-12 w-12 items-center justify-center rounded-lg ${getCategoryColor(
                  integration.category
                )} bg-current/10`}
              >
                <Icon
                  className={`h-6 w-6 ${getCategoryColor(
                    integration.category
                  )}`}
                />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <CardTitle className="text-lg">{integration.name}</CardTitle>
                  {integration.isOneClick && (
                    <Badge
                      variant="outline"
                      className="text-xs bg-blue-50 text-blue-700 border-blue-200"
                    >
                      <IconRobot className="h-3 w-3 mr-1" />
                      MCP
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <Badge variant="outline" className="text-xs">
                    {integration.category}
                  </Badge>
                  {integration.toolsCount && (
                    <Badge variant="outline" className="text-xs">
                      {integration.toolsCount} tools
                    </Badge>
                  )}
                </div>
              </div>
            </div>
          </div>
          <CardDescription className="text-sm leading-relaxed">
            {integration.description}
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Features List - Only show when not connected */}
          {!isConnected && (
            <div>
              <Label className="text-sm font-medium">Key Features:</Label>
              <ul className="mt-2 space-y-1">
                {integration.features.slice(0, 4).map((feature, index) => (
                  <li
                    key={index}
                    className="flex items-center gap-2 text-sm text-muted-foreground"
                  >
                    <div className="h-1.5 w-1.5 rounded-full bg-primary" />
                    {feature}
                  </li>
                ))}
                {integration.features.length > 4 && (
                  <li className="text-sm text-muted-foreground">
                    +{integration.features.length - 4} more features
                  </li>
                )}
              </ul>
            </div>
          )}

          {/* API Key Input - Only show for legacy integrations when not connected */}
          {integration.requiresApi &&
            !isConnected &&
            !integration.isOneClick && (
              <div className="space-y-2">
                <Label
                  htmlFor={`api-key-${integration.id}`}
                  className="text-sm"
                >
                  {integration.apiKeyLabel}
                </Label>
                <Input
                  id={`api-key-${integration.id}`}
                  type="password"
                  placeholder="Enter your API key or token"
                  value={apiKeys[integration.id] || ""}
                  onChange={(e) =>
                    handleApiKeyChange(integration.id, e.target.value)
                  }
                />
              </div>
            )}

          {/* Success message when connected */}
          {isConnected && (
            <div className="text-center py-4">
              <div className="inline-flex items-center gap-2 text-green-600 font-medium">
                <IconCheck className="h-5 w-5" />
                Successfully Connected
              </div>
              <p className="text-sm text-muted-foreground mt-1">
                {integration.name} is now integrated with your AI agents
              </p>
            </div>
          )}
        </CardContent>

        <CardFooter className="flex gap-2">
          {isConnected ? (
            <Button
              className="flex-1 bg-green-600 hover:bg-green-700 text-white"
              onClick={() => handleDisconnect(integration)}
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <IconLoader className="h-4 w-4 mr-2 animate-spin" />
                  Disconnecting...
                </>
              ) : (
                <>
                  <IconCheck className="h-4 w-4 mr-2" />
                  Connected
                </>
              )}
            </Button>
          ) : (
            <>
              <Button
                className="flex-1"
                onClick={() => handleConnect(integration)}
                disabled={
                  isLoading ||
                  (integration.requiresApi &&
                    !integration.isOneClick &&
                    !apiKeys[integration.id])
                }
              >
                {isLoading ? (
                  <>
                    <IconLoader className="h-4 w-4 mr-2 animate-spin" />
                    Connecting...
                  </>
                ) : integration.isOneClick ? (
                  <>
                    <IconRobot className="h-4 w-4 mr-2" />
                    Connect Now
                  </>
                ) : (
                  <>
                    <IconPlug className="h-4 w-4 mr-2" />
                    Connect
                  </>
                )}
              </Button>
              {integration.isOneClick && (
                <Button variant="outline" size="sm" asChild>
                  <a
                    href="https://pipedream.com/docs/connect/mcp/openai/"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <IconExternalLink className="h-4 w-4" />
                  </a>
                </Button>
              )}
            </>
          )}
        </CardFooter>
      </Card>
    );
  };

  const connectedMcp = mcpIntegrations.filter((i) =>
    connectedIntegrations.has(i.id)
  ).length;
  const connectedLegacy = legacyIntegrations.filter((i) =>
    connectedIntegrations.has(i.id)
  ).length;
  const totalConnected = connectedMcp + connectedLegacy;

  return (
    <div className="space-y-8">
      {/* Header Section */}
      <div className="flex items-center gap-4">
        <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
          <IconSettings className="h-6 w-6 text-primary" />
        </div>
        <div>
          <h2 className="text-2xl font-semibold tracking-tight">
            Integrations
          </h2>
          <p className="text-muted-foreground">
            Connect your favorite platforms to automate lead management with AI
            agents
          </p>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <IconRobot className="h-5 w-5 text-indigo-600" />
              <span className="text-sm font-medium">MCP Integrations</span>
            </div>
            <div className="mt-2">
              <span className="text-2xl font-bold">{connectedMcp}</span>
              <span className="text-muted-foreground text-sm ml-1">
                / {mcpIntegrations.length} active
              </span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <IconPlug className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm font-medium">Legacy APIs</span>
            </div>
            <div className="mt-2">
              <span className="text-2xl font-bold">{connectedLegacy}</span>
              <span className="text-muted-foreground text-sm ml-1">
                / {legacyIntegrations.length} active
              </span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <IconCheck className="h-5 w-5 text-green-600" />
              <span className="text-sm font-medium">Total Connected</span>
            </div>
            <div className="mt-2">
              <span className="text-2xl font-bold">{totalConnected}</span>
              <span className="text-muted-foreground text-sm ml-1">
                integrations
              </span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <IconShield className="h-5 w-5 text-blue-600" />
              <span className="text-sm font-medium">Security</span>
            </div>
            <div className="mt-2">
              <span className="text-2xl font-bold text-green-600">Secure</span>
              <span className="text-muted-foreground text-sm ml-1">
                encrypted
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      <Separator />

      {/* Integrations Tabs */}
      <Tabs
        value={activeTab}
        onValueChange={setActiveTab}
        className="space-y-6"
      >
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="mcp" className="flex items-center gap-2">
            <IconRobot className="h-4 w-4" />
            MCP Integrations
            <Badge className="ml-2">{mcpIntegrations.length}</Badge>
          </TabsTrigger>
          <TabsTrigger value="legacy" className="flex items-center gap-2">
            <IconPlug className="h-4 w-4" />
            API Integrations
            <Badge variant="outline" className="ml-2">
              {legacyIntegrations.length}
            </Badge>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="mcp" className="space-y-6">
          <Card className="bg-gradient-to-r from-indigo-50 to-purple-50 border-indigo-200">
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-indigo-100">
                  <IconRobot className="h-6 w-6 text-indigo-600" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-lg mb-2">
                    MCP Integrations - One-Click Setup
                  </h3>
                  <p className="text-muted-foreground mb-4">
                    Connect powerful business tools instantly through the Model
                    Context Protocol (MCP). These integrations provide your AI
                    agents with{" "}
                    {mcpIntegrations.reduce(
                      (sum, i) => sum + (i.toolsCount || 0),
                      0
                    )}
                    + tools across 6 major platforms.
                  </p>
                  <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-2">
                      <IconCheck className="h-4 w-4 text-green-600" />
                      <span>No API keys required</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <IconCheck className="h-4 w-4 text-green-600" />
                      <span>Instant setup</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <IconCheck className="h-4 w-4 text-green-600" />
                      <span>AI agent ready</span>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {mcpIntegrations.map(renderIntegrationCard)}
          </div>
        </TabsContent>

        <TabsContent value="legacy" className="space-y-6">
          <Card className="bg-amber-50 border-amber-200">
            <CardContent className="p-6">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-amber-100">
                  <IconPlug className="h-6 w-6 text-amber-600" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-lg mb-2">
                    API Integrations - Manual Setup
                  </h3>
                  <p className="text-muted-foreground mb-4">
                    Connect social media and messaging platforms using your own
                    API keys. These integrations require manual configuration
                    and API credentials.
                  </p>
                  <div className="flex items-center gap-4 text-sm">
                    <div className="flex items-center gap-2">
                      <IconArrowRight className="h-4 w-4 text-amber-600" />
                      <span>Requires API keys</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <IconArrowRight className="h-4 w-4 text-amber-600" />
                      <span>Manual setup</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <IconArrowRight className="h-4 w-4 text-amber-600" />
                      <span>Custom configuration</span>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {legacyIntegrations.map(renderIntegrationCard)}
          </div>
        </TabsContent>
      </Tabs>

      {/* Help Section */}
      <Card className="bg-muted/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <IconShield className="h-5 w-5" />
            Security & Privacy
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground leading-relaxed">
            All integrations use secure authentication methods. MCP integrations
            connect through Pipedream&apos;s secure infrastructure, while API
            integrations store encrypted credentials.
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label className="text-sm font-medium">Auto-sync data</Label>
                <p className="text-xs text-muted-foreground">
                  Automatically sync lead data from connected platforms
                </p>
              </div>
              <Checkbox defaultChecked />
            </div>
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label className="text-sm font-medium">
                  Real-time notifications
                </Label>
                <p className="text-xs text-muted-foreground">
                  Get notified when AI agents use integrations
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

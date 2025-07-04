"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ExternalLink, Check, AlertCircle, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { Integration } from "@/lib/integrations-config";
import { api } from "@/lib/api";

// Backend base URL configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface OAuthIntegrationCardProps {
  integration: Integration;
  isConnected: boolean;
  connectionData?: {
    connected_at?: string;
    profile?: any;
  };
  onConnectionUpdate: () => void;
}

export function OAuthIntegrationCard({
  integration,
  isConnected,
  connectionData,
  onConnectionUpdate,
}: OAuthIntegrationCardProps) {
  const [isLoading, setIsLoading] = useState(false);

  const handleConnect = async () => {
    if (!integration.oauthUrl) {
      toast.error("OAuth not configured for this integration");
      return;
    }

    setIsLoading(true);
    try {
      const redirectUrl = `${window.location.origin}/integrations?connected=${integration.key}`;

      // Get authorization URL from backend
      const response = await api.startOAuthFlow(integration.key, redirectUrl);

      if (response && response.authorization_url) {
        // Redirect user to provider's authorization page
        window.location.href = response.authorization_url;
      } else {
        throw new Error("No valid authorization URL received from server.");
      }
    } catch (error) {
      console.error("Error starting OAuth flow:", error);
      toast.error(
        `Error starting OAuth connection: ${
          error instanceof Error ? error.message : "Unknown error"
        }`
      );
      setIsLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setIsLoading(true);
    try {
      await api.post(`/api/integrations/${integration.key}/oauth/disconnect`);
      toast.success(`Disconnected from ${integration.name}`);
      onConnectionUpdate();
    } catch (error) {
      console.error("Error disconnecting:", error);
      toast.error("Error disconnecting integration");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="relative">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-50 rounded-lg">
              <span className="text-2xl">{integration.icon}</span>
            </div>
            <div>
              <CardTitle className="text-lg">{integration.name}</CardTitle>
              <CardDescription className="text-sm mt-1">
                {integration.description}
              </CardDescription>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Badge
              variant={isConnected ? "default" : "secondary"}
              className="text-xs"
            >
              {isConnected ? "Connected" : "Disconnected"}
            </Badge>
            {integration.docs && (
              <Button variant="ghost" size="sm" asChild className="h-8 w-8 p-0">
                <a
                  href={integration.docs}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="View documentation"
                >
                  <ExternalLink className="h-4 w-4" />
                </a>
              </Button>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="pt-0">
        {isConnected ? (
          <div className="space-y-4">
            {connectionData?.profile && (
              <div className="space-y-2">
                <Separator />
                <div className="text-sm">
                  <div className="font-medium text-gray-700 mb-2">
                    Account information:
                  </div>
                  <div className="space-y-1 text-gray-600">
                    {connectionData.profile.name && (
                      <div>
                        <span className="font-medium">Name:</span>{" "}
                        {connectionData.profile.name}
                      </div>
                    )}
                    {connectionData.profile.email && (
                      <div>
                        <span className="font-medium">Email:</span>{" "}
                        {connectionData.profile.email}
                      </div>
                    )}
                    {connectionData.profile.username && (
                      <div>
                        <span className="font-medium">Username:</span> @
                        {connectionData.profile.username}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {connectionData?.connected_at && (
              <div className="text-xs text-gray-500">
                Connected on:{" "}
                {new Date(connectionData.connected_at).toLocaleDateString(
                  "en-US",
                  {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit",
                  }
                )}
              </div>
            )}

            <div className="flex justify-end space-x-2">
              <Button
                variant="default"
                size="sm"
                disabled
                className="bg-green-600 text-white"
              >
                Connected
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDisconnect}
                disabled={isLoading}
              >
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Disconnect
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <AlertCircle className="h-4 w-4" />
              <span>
                Connect your {integration.name} account with one click
              </span>
            </div>

            <div className="flex justify-end">
              <Button
                onClick={handleConnect}
                disabled={isLoading}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Connect with {integration.name}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

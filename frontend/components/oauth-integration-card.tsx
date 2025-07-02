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
import { IntegrationConfig } from "@/lib/integrations-config";
import { api } from "@/lib/api";

// Configuración de la URL base del backend
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

interface OAuthIntegrationCardProps {
  integration: IntegrationConfig;
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
    if (!integration.oauthStartUrl) {
      toast.error("OAuth no configurado para esta integración");
      return;
    }

    setIsLoading(true);
    try {
      const redirectUrl = `${window.location.origin}/integrations?connected=${integration.key}`;

      // Obtener la URL de autorización desde el backend
      const response = await api.startOAuthFlow(integration.key, redirectUrl);

      if (response && response.authorization_url) {
        // Redirigir al usuario a la página de autorización del proveedor
        window.location.href = response.authorization_url;
      } else {
        throw new Error(
          "No se recibió una URL de autorización válida del servidor."
        );
      }
    } catch (error) {
      console.error("Error starting OAuth flow:", error);
      toast.error(
        `Error al iniciar la conexión OAuth: ${
          error instanceof Error ? error.message : "Error desconocido"
        }`
      );
      setIsLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setIsLoading(true);
    try {
      await api.post(`/api/integrations/${integration.key}/oauth/disconnect`);
      toast.success(`Desconectado de ${integration.name}`);
      onConnectionUpdate();
    } catch (error) {
      console.error("Error disconnecting:", error);
      toast.error("Error al desconectar la integración");
    } finally {
      setIsLoading(false);
    }
  };

  const IconComponent = integration.icon;

  return (
    <Card className="relative">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-blue-50 rounded-lg">
              {IconComponent && (
                <IconComponent className="h-6 w-6 text-blue-600" />
              )}
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
              {isConnected ? "Conectado" : "Desconectado"}
            </Badge>
            {integration.documentationUrl && (
              <Button variant="ghost" size="sm" asChild className="h-8 w-8 p-0">
                <a
                  href={integration.documentationUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="Ver documentación"
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
                    Información de la cuenta:
                  </div>
                  <div className="space-y-1 text-gray-600">
                    {connectionData.profile.name && (
                      <div>
                        <span className="font-medium">Nombre:</span>{" "}
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
                        <span className="font-medium">Usuario:</span> @
                        {connectionData.profile.username}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {connectionData?.connected_at && (
              <div className="text-xs text-gray-500">
                Conectado el:{" "}
                {new Date(connectionData.connected_at).toLocaleDateString(
                  "es-ES",
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
                Conectado
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDisconnect}
                disabled={isLoading}
              >
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Desconectar
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <AlertCircle className="h-4 w-4" />
              <span>Conecta tu cuenta de {integration.name} con un clic</span>
            </div>

            <div className="flex justify-end">
              <Button
                onClick={handleConnect}
                disabled={isLoading}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Conectar con {integration.name}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

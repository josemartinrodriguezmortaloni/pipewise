"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  IconUser,
  IconMail,
  IconCalendar,
  IconBrandInstagram,
  IconBrandTwitter,
  IconSettings,
  IconPlug,
  IconUsers,
  IconCheck,
} from "@tabler/icons-react";

interface UserAccountConfig {
  id: string;
  name: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  fields: {
    name: string;
    type: "text" | "email" | "textarea";
    placeholder: string;
    required: boolean;
    description: string;
  }[];
  category: "calendar" | "crm" | "email" | "social";
  connected: boolean;
}

const userAccountConfigs: UserAccountConfig[] = [
  {
    id: "google_calendar",
    name: "Google Calendar",
    description:
      "Conecta tu calendario de Google para que PipeWise programe reuniones automáticamente.",
    icon: IconCalendar,
    category: "calendar",
    connected: false,
    fields: [
      {
        name: "oauth_token",
        type: "text",
        placeholder: "Token OAuth 2.0",
        required: true,
        description: "Token de acceso OAuth con permisos de calendario.",
      },
      {
        name: "refresh_token",
        type: "text",
        placeholder: "Refresh Token",
        required: true,
        description: "Refresh token para renovar el acceso periódicamente.",
      },
    ],
  },
  {
    id: "calendly_account",
    name: "Calendly",
    description: "Configura tu cuenta de Calendly para programación automática",
    icon: IconCalendar,
    category: "calendar",
    connected: false,
    fields: [
      {
        name: "username",
        type: "text",
        placeholder: "tu-usuario-calendly",
        required: true,
        description: "Tu nombre de usuario en Calendly (sin @)",
      },
      {
        name: "default_event_type",
        type: "text",
        placeholder: "15min-meeting",
        required: false,
        description: "Tipo de evento por defecto para reuniones",
      },
    ],
  },
  {
    id: "twitter_account",
    name: "Twitter/X",
    description: "Configura tu perfil de Twitter para comunicación social",
    icon: IconBrandTwitter,
    category: "social",
    connected: false,
    fields: [
      {
        name: "username",
        type: "text",
        placeholder: "@tu_usuario",
        required: true,
        description: "Tu nombre de usuario en Twitter/X (incluye @)",
      },
      {
        name: "display_name",
        type: "text",
        placeholder: "Tu Nombre en Twitter",
        required: false,
        description: "Nombre que aparece en tu perfil",
      },
    ],
  },
  {
    id: "sendgrid",
    name: "SendGrid",
    description:
      "Envía emails transaccionales y campañas usando la API de SendGrid.",
    icon: IconMail,
    category: "email",
    connected: false,
    fields: [
      {
        name: "api_key",
        type: "text",
        placeholder: "SG.xxxxx",
        required: true,
        description: "Tu API Key de SendGrid con permisos de envío.",
      },
      {
        name: "from_email",
        type: "email",
        placeholder: "ventas@tudominio.com",
        required: true,
        description: "Dirección de remitente por defecto.",
      },
    ],
  },
  {
    id: "pipedrive",
    name: "Pipedrive",
    description: "Sincroniza leads y oportunidades con tu CRM Pipedrive.",
    icon: IconPlug,
    category: "crm",
    connected: false,
    fields: [
      {
        name: "api_token",
        type: "text",
        placeholder: "Tu API Token",
        required: true,
        description: "API token de tu cuenta Pipedrive.",
      },
    ],
  },
  {
    id: "salesforce_rest_api",
    name: "Salesforce",
    description: "Conecta Salesforce REST API para sincronizar datos de CRM.",
    icon: IconPlug,
    category: "crm",
    connected: false,
    fields: [
      {
        name: "client_id",
        type: "text",
        placeholder: "Consumer Key",
        required: true,
        description: "Client ID de tu app en Salesforce.",
      },
      {
        name: "client_secret",
        type: "text",
        placeholder: "Consumer Secret",
        required: true,
        description: "Client secret de tu app en Salesforce.",
      },
      {
        name: "refresh_token",
        type: "text",
        placeholder: "Refresh Token OAuth",
        required: true,
        description: "Refresh token con permisos API.",
      },
    ],
  },
  {
    id: "zoho_crm",
    name: "Zoho CRM",
    description: "Sincroniza contactos y negocios con Zoho CRM.",
    icon: IconPlug,
    category: "crm",
    connected: false,
    fields: [
      {
        name: "client_id",
        type: "text",
        placeholder: "Client ID",
        required: true,
        description: "Client ID de tu app en Zoho.",
      },
      {
        name: "client_secret",
        type: "text",
        placeholder: "Client Secret",
        required: true,
        description: "Client secret de tu app en Zoho.",
      },
      {
        name: "refresh_token",
        type: "text",
        placeholder: "Refresh Token",
        required: true,
        description: "Refresh token OAuth.",
      },
    ],
  },
];

export function IntegrationsSettings() {
  const [userAccounts, setUserAccounts] =
    React.useState<UserAccountConfig[]>(userAccountConfigs);
  const [accountForms, setAccountForms] = React.useState<
    Record<string, Record<string, string>>
  >({});
  const [loading, setLoading] = React.useState<Record<string, boolean>>({});

  // Load saved configurations
  React.useEffect(() => {
    const loadUserConfigurations = async () => {
      try {
        // Load user account configurations
        const accountResponse = await fetch("/api/user/integrations/accounts");
        if (accountResponse.ok) {
          const accountData = await accountResponse.json();
          // Update connected status and form data based on saved configurations
          // Implementation would depend on backend API structure
        }
      } catch (error) {
        console.error("Error loading user configurations:", error);
      }
    };

    loadUserConfigurations();
  }, []);

  const handleFieldChange = (
    accountId: string,
    fieldName: string,
    value: string
  ) => {
    setAccountForms((prev) => ({
      ...prev,
      [accountId]: {
        ...prev[accountId],
        [fieldName]: value,
      },
    }));
  };

  const handleSaveAccount = async (account: UserAccountConfig) => {
    setLoading((prev) => ({ ...prev, [account.id]: true }));

    try {
      const formData = accountForms[account.id] || {};

      // Validate required fields
      const missingFields = account.fields
        .filter((field) => field.required && !formData[field.name])
        .map((field) => field.name);

      if (missingFields.length > 0) {
        alert(
          `Por favor completa los campos requeridos: ${missingFields.join(
            ", "
          )}`
        );
        return;
      }

      const response = await fetch("/api/user/integrations/accounts", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          account_id: account.id,
          account_type: account.category,
          configuration: formData,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to save ${account.name} configuration`);
      }

      // Update UI to show as connected
      setUserAccounts((prev) =>
        prev.map((acc) =>
          acc.id === account.id ? { ...acc, connected: true } : acc
        )
      );

      alert(`${account.name} configurado exitosamente`);
    } catch (error) {
      console.error(`Error saving ${account.name}:`, error);
      alert(
        `Error al configurar ${account.name}: ${
          error instanceof Error ? error.message : "Error desconocido"
        }`
      );
    } finally {
      setLoading((prev) => ({ ...prev, [account.id]: false }));
    }
  };

  const handleDisconnectAccount = async (account: UserAccountConfig) => {
    setLoading((prev) => ({ ...prev, [account.id]: true }));

    try {
      const response = await fetch(
        `/api/user/integrations/accounts/${account.id}`,
        {
          method: "DELETE",
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to disconnect ${account.name}`);
      }

      setUserAccounts((prev) =>
        prev.map((acc) =>
          acc.id === account.id ? { ...acc, connected: false } : acc
        )
      );

      // Clear form data
      setAccountForms((prev) => ({
        ...prev,
        [account.id]: {},
      }));

      alert(`${account.name} desconectado exitosamente`);
    } catch (error) {
      console.error(`Error disconnecting ${account.name}:`, error);
      alert(`Error al desconectar ${account.name}`);
    } finally {
      setLoading((prev) => ({ ...prev, [account.id]: false }));
    }
  };

  const renderAccountCard = (account: UserAccountConfig) => {
    const formData = accountForms[account.id] || {};
    const isLoading = loading[account.id] || false;

    return (
      <Card key={account.id} className="border border-gray-200 bg-white">
        <CardContent className="p-6">
          <div className="flex items-start gap-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-gray-200 bg-gray-50">
              <account.icon className="h-5 w-5 text-gray-600" />
            </div>
            <div className="flex-1">
              <h4 className="font-medium text-gray-900 mb-1">{account.name}</h4>
              <p className="text-sm text-gray-600 mb-4">
                {account.description}
              </p>

              {!account.connected ? (
                <div className="space-y-3">
                  {account.fields.map((field) => (
                    <div key={field.name}>
                      <Label className="text-sm font-medium text-gray-700">
                        {field.name}
                        {field.required && (
                          <span className="text-red-500 ml-1">*</span>
                        )}
                      </Label>
                      {field.type === "textarea" ? (
                        <Textarea
                          placeholder={field.placeholder}
                          value={formData[field.name] || ""}
                          onChange={(e) =>
                            handleFieldChange(
                              account.id,
                              field.name,
                              e.target.value
                            )
                          }
                          className="text-sm"
                          disabled={isLoading}
                        />
                      ) : (
                        <Input
                          type={field.type}
                          placeholder={field.placeholder}
                          value={formData[field.name] || ""}
                          onChange={(e) =>
                            handleFieldChange(
                              account.id,
                              field.name,
                              e.target.value
                            )
                          }
                          className="text-sm"
                          disabled={isLoading}
                        />
                      )}
                      <p className="text-xs text-gray-500 mt-1">
                        {field.description}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-2 bg-green-500 rounded-full"></div>
                    <span className="text-sm text-green-700 font-medium">
                      Conectado
                    </span>
                  </div>
                  {Object.entries(formData).map(([key, value]) => (
                    <div key={key} className="text-sm text-gray-600">
                      <span className="font-medium capitalize">{key}: </span>
                      <span>{value}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="mt-4 pt-4 border-t border-gray-100">
            {!account.connected ? (
              <Button
                onClick={() => handleSaveAccount(account)}
                disabled={isLoading}
                className="bg-blue-600 text-white hover:bg-blue-700"
                size="sm"
              >
                {isLoading ? "Configurando..." : "Configurar"}
              </Button>
            ) : (
              <Button
                onClick={() => handleDisconnectAccount(account)}
                disabled={isLoading}
                variant="outline"
                className="border-red-200 text-red-700 hover:bg-red-50"
                size="sm"
              >
                {isLoading ? "Desconectando..." : "Desconectar"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };

  const connectedCount = userAccounts.filter((acc) => acc.connected).length;
  const socialConnected = userAccounts.filter(
    (acc) => acc.category === "social" && acc.connected
  ).length;
  const calendarConnected = userAccounts.filter(
    (acc) => acc.category === "calendar" && acc.connected
  ).length;

  return (
    <div className="space-y-8">
      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="border border-gray-200 bg-white shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <IconPlug className="h-5 w-5 text-gray-600" />
              <span className="text-sm font-medium text-gray-700">
                Cuentas Configuradas
              </span>
            </div>
            <div className="mt-2">
              <span className="text-2xl font-semibold text-gray-900">
                {connectedCount}
              </span>
              <span className="text-gray-500 text-sm ml-1">
                / {userAccounts.length} disponibles
              </span>
            </div>
          </CardContent>
        </Card>

        <Card className="border border-gray-200 bg-white shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <IconCalendar className="h-5 w-5 text-gray-600" />
              <span className="text-sm font-medium text-gray-700">
                Calendario
              </span>
            </div>
            <div className="mt-2">
              <span className="text-2xl font-semibold text-gray-900">
                {calendarConnected}
              </span>
              <span className="text-gray-500 text-sm ml-1">conectadas</span>
            </div>
          </CardContent>
        </Card>

        <Card className="border border-gray-200 bg-white shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-center gap-2">
              <IconUsers className="h-5 w-5 text-gray-600" />
              <span className="text-sm font-medium text-gray-700">
                Redes Sociales
              </span>
            </div>
            <div className="mt-2">
              <span className="text-2xl font-semibold text-gray-900">
                {socialConnected}
              </span>
              <span className="text-gray-500 text-sm ml-1">conectadas</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* User Account Configuration Section */}
      <div className="space-y-6">
        <Card className="border border-gray-200 bg-white shadow-sm">
          <CardContent className="p-6">
            <div className="flex items-start gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-gray-200 bg-gray-50">
                <IconUser className="h-6 w-6 text-gray-600" />
              </div>
              <div className="flex-1">
                <h3 className="font-semibold text-lg mb-2 text-gray-900">
                  Configuración de Cuentas Personales
                </h3>
                <p className="text-gray-600 mb-4">
                  Configura tus cuentas personales para que PipeWise pueda
                  comunicarse con leads en tu nombre. Solo necesitamos
                  información básica de identificación.
                </p>
                <div className="flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-2">
                    <IconCheck className="h-4 w-4 text-gray-600" />
                    <span className="text-gray-600">Configuración simple</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <IconCheck className="h-4 w-4 text-gray-600" />
                    <span className="text-gray-600">Sin credenciales API</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <IconCheck className="h-4 w-4 text-gray-600" />
                    <span className="text-gray-600">Gestión automática</span>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="grid gap-6 md:grid-cols-1 lg:grid-cols-2">
          {userAccounts.map(renderAccountCard)}
        </div>
      </div>

      {/* Automation Settings */}
      <Card className="border border-gray-200 bg-gray-50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-gray-900">
            <IconSettings className="h-5 w-5" />
            Configuración de Automatización
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-gray-600 leading-relaxed">
            Configura cómo el orchestrator debe manejar las comunicaciones
            automáticas. El orchestrator utilizará el chat para comunicarse
            contigo sobre objetivos y estrategias.
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label className="text-sm font-medium text-gray-700">
                  Comunicación automática
                </Label>
                <p className="text-xs text-gray-500">
                  Permitir que el orchestrator inicie conversaciones
                </p>
              </div>
              <Checkbox defaultChecked />
            </div>
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label className="text-sm font-medium text-gray-700">
                  Respuestas inteligentes
                </Label>
                <p className="text-xs text-gray-500">
                  Responder automáticamente a mensajes entrantes
                </p>
              </div>
              <Checkbox defaultChecked />
            </div>
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label className="text-sm font-medium text-gray-700">
                  Creación automática de leads
                </Label>
                <p className="text-xs text-gray-500">
                  Crear leads automáticamente desde conversaciones
                </p>
              </div>
              <Checkbox defaultChecked />
            </div>
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label className="text-sm font-medium text-gray-700">
                  Notificaciones de actividad
                </Label>
                <p className="text-xs text-gray-500">
                  Recibir notificaciones de comunicaciones importantes
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

// integrations-config.ts - Solo OAuth, sin API keys
import {
  Calendar,
  Building2,
  Cloud,
  Mail,
  Twitter,
  Instagram,
  LucideIcon,
} from "lucide-react";

// Configuración de la URL base del backend
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export interface IntegrationField {
  name: string;
  label: string;
  type: "text" | "email" | "password" | "number";
  required: boolean;
  placeholder?: string;
}

export interface IntegrationConfig {
  key: string;
  name: string;
  description: string;
  category: string;
  icon: any;
  oauthStartUrl?: string;
  documentationUrl?: string;
}

export const ALL_INTEGRATIONS: IntegrationConfig[] = [
  // Calendario
  {
    key: "calendly",
    name: "Calendly",
    description:
      "Automatiza la programación de reuniones con clientes potenciales",
    category: "calendar",
    icon: Calendar,
    oauthStartUrl: `${API_BASE_URL}/api/integrations/calendly/oauth/start`,
    documentationUrl: "https://developer.calendly.com/api-docs",
  },
  {
    key: "google_calendar",
    name: "Google Calendar",
    description: "Sincroniza reuniones y eventos con tu calendario de Google",
    category: "calendar",
    icon: Calendar,
    oauthStartUrl: `${API_BASE_URL}/api/integrations/google_calendar/oauth/start`,
    documentationUrl:
      "https://developers.google.com/calendar/api/guides/overview",
  },

  // CRM
  {
    key: "pipedrive",
    name: "Pipedrive",
    description: "Gestiona ventas y leads automáticamente en tu CRM",
    category: "crm",
    icon: Building2,
    oauthStartUrl: `${API_BASE_URL}/api/integrations/pipedrive/oauth/start`,
    documentationUrl: "https://developers.pipedrive.com/docs/api/v1",
  },
  {
    key: "salesforce_rest_api",
    name: "Salesforce",
    description: "Integración completa con la plataforma Salesforce CRM",
    category: "crm",
    icon: Cloud,
    oauthStartUrl: `${API_BASE_URL}/api/integrations/salesforce_rest_api/oauth/start`,
    documentationUrl: "https://developer.salesforce.com/docs",
  },
  {
    key: "zoho_crm",
    name: "Zoho CRM",
    description: "Conecta y sincroniza contactos y deals con Zoho CRM",
    category: "crm",
    icon: Building2,
    oauthStartUrl: `${API_BASE_URL}/api/integrations/zoho_crm/oauth/start`,
    documentationUrl:
      "https://www.zoho.com/crm/developer/docs/api/overview.html",
  },

  // Email
  {
    key: "sendgrid_email",
    name: "SendGrid",
    description: "Envía emails transaccionales y newsletters a leads",
    category: "email",
    icon: Mail,
    oauthStartUrl: `${API_BASE_URL}/api/integrations/sendgrid_email/oauth/start`,
    documentationUrl: "https://docs.sendgrid.com/api-reference",
  },

  // Social
  {
    key: "twitter_account",
    name: "Twitter / X",
    description: "Conecta tu cuenta de Twitter/X para interactuar con leads",
    category: "social",
    icon: Twitter,
    oauthStartUrl: `${API_BASE_URL}/api/integrations/twitter_account/oauth/start`,
    documentationUrl: "https://developer.twitter.com/en/docs/twitter-api",
  },
  {
    key: "instagram_account",
    name: "Instagram",
    description: "Conecta tu cuenta de Instagram para interactuar con leads",
    category: "social",
    icon: Instagram,
    oauthStartUrl: `${API_BASE_URL}/api/integrations/instagram_account/oauth/start`,
    documentationUrl: "https://developers.facebook.com/docs/instagram-api/",
  },
];

export function getIntegrationByKey(
  key: string
): IntegrationConfig | undefined {
  return ALL_INTEGRATIONS.find((integration) => integration.key === key);
}

export function getIntegrationsByCategory(
  category: string
): IntegrationConfig[] {
  return ALL_INTEGRATIONS.filter(
    (integration) => integration.category === category
  );
}

export function getAvailableCategories(): string[] {
  return Array.from(
    new Set(ALL_INTEGRATIONS.map((integration) => integration.category))
  );
}

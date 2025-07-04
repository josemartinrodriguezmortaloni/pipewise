/**
 * Configuration for OAuth integrations in PipeWise
 * Defines all supported integrations with their metadata and OAuth endpoints
 */

export interface Integration {
  key: string;
  name: string;
  description: string;
  category: "calendar" | "email" | "social" | "crm" | "automation";
  icon: string;
  color: string;
  oauthUrl?: string;
  features: string[];
  status: "active" | "beta" | "coming_soon";
  docs?: string;
}

export const ALL_INTEGRATIONS: Integration[] = [
  // Calendar Integrations
  {
    key: "google_calendar",
    name: "Google Calendar",
    description: "Sincroniza eventos y agenda reuniones automáticamente",
    category: "calendar",
    icon: "🗓️",
    color: "bg-blue-500",
    oauthUrl: "/api/integrations/google_calendar/oauth/start",
    features: [
      "Sincronización de calendario",
      "Creación automática de eventos",
      "Invitaciones por email",
      "Recordatorios personalizados",
    ],
    status: "active",
    docs: "https://developers.google.com/calendar",
  },
  {
    key: "calendly",
    name: "Calendly",
    description: "Integra tu sistema de reservas y automatiza la programación",
    category: "calendar",
    icon: "📅",
    color: "bg-orange-500",
    oauthUrl: "/api/integrations/calendly/oauth/start",
    features: [
      "Programación automática",
      "Webhooks de eventos",
      "Sincronización bidireccional",
      "Gestión de disponibilidad",
    ],
    status: "active",
    docs: "https://developer.calendly.com",
  },

  // CRM Integrations
  {
    key: "pipedrive",
    name: "Pipedrive",
    description: "Sincroniza leads y gestiona tu pipeline de ventas",
    category: "crm",
    icon: "🏢",
    color: "bg-green-500",
    oauthUrl: "/api/integrations/pipedrive/oauth/start",
    features: [
      "Sincronización de leads",
      "Gestión de pipeline",
      "Seguimiento de actividades",
      "Reportes de ventas",
    ],
    status: "beta",
    docs: "https://developers.pipedrive.com",
  },
  {
    key: "zoho_crm",
    name: "Zoho CRM",
    description: "Conecta con Zoho para gestión completa de clientes",
    category: "crm",
    icon: "📊",
    color: "bg-purple-500",
    oauthUrl: "/api/integrations/zoho_crm/oauth/start",
    features: [
      "Gestión de contactos",
      "Automatización de ventas",
      "Seguimiento de leads",
      "Análisis de rendimiento",
    ],
    status: "beta",
    docs: "https://www.zoho.com/crm/developer/",
  },

  // Social Media Integrations
  {
    key: "twitter_account",
    name: "Twitter/X",
    description: "Publica contenido y gestiona interacciones automáticamente",
    category: "social",
    icon: "🐦",
    color: "bg-black",
    oauthUrl: "/api/integrations/twitter_account/oauth/start",
    features: [
      "Publicación automática",
      "Gestión de menciones",
      "Análisis de engagement",
      "Programación de tweets",
    ],
    status: "beta",
    docs: "https://developer.twitter.com",
  },
  {
    key: "instagram_account",
    name: "Instagram",
    description: "Gestiona tu presencia en Instagram y automatiza posts",
    category: "social",
    icon: "📸",
    color: "bg-pink-500",
    oauthUrl: "/api/integrations/instagram_account/oauth/start",
    features: [
      "Publicación de contenido",
      "Gestión de comentarios",
      "Análisis de métricas",
      "Stories automáticas",
    ],
    status: "beta",
    docs: "https://developers.facebook.com/docs/instagram",
  },

  // Email Integrations
  {
    key: "gmail",
    name: "Gmail",
    description: "Automatiza emails y gestiona comunicaciones",
    category: "email",
    icon: "📧",
    color: "bg-red-500",
    oauthUrl: "/api/integrations/gmail/oauth/start",
    features: [
      "Envío automático de emails",
      "Plantillas personalizadas",
      "Seguimiento de aperturas",
      "Gestión de respuestas",
    ],
    status: "active",
    docs: "https://developers.google.com/gmail",
  },

  // Automation Integrations
  {
    key: "zapier",
    name: "Zapier",
    description: "Conecta con miles de aplicaciones usando Zapier",
    category: "automation",
    icon: "⚡",
    color: "bg-yellow-500",
    features: [
      "Automatización avanzada",
      "Conectores múltiples",
      "Flujos personalizados",
      "Triggers inteligentes",
    ],
    status: "coming_soon",
    docs: "https://zapier.com/developer",
  },
];

/**
 * Get integration configuration by key
 */
export function getIntegrationByKey(key: string): Integration | undefined {
  return ALL_INTEGRATIONS.find((integration) => integration.key === key);
}

/**
 * Get integrations by category
 */
export function getIntegrationsByCategory(
  category: Integration["category"]
): Integration[] {
  return ALL_INTEGRATIONS.filter(
    (integration) => integration.category === category
  );
}

/**
 * Get active integrations only
 */
export function getActiveIntegrations(): Integration[] {
  return ALL_INTEGRATIONS.filter(
    (integration) => integration.status === "active"
  );
}

/**
 * Get OAuth URL for integration
 */
export function getOAuthUrl(
  integrationKey: string,
  redirectUrl?: string
): string {
  const integration = getIntegrationByKey(integrationKey);
  if (!integration?.oauthUrl) {
    throw new Error(
      `OAuth URL not configured for integration: ${integrationKey}`
    );
  }

  let url = integration.oauthUrl;
  if (redirectUrl) {
    url += `?redirect_url=${encodeURIComponent(redirectUrl)}`;
  }

  return url;
}

/**
 * Check if integration is available
 */
export function isIntegrationAvailable(integrationKey: string): boolean {
  const integration = getIntegrationByKey(integrationKey);
  return integration?.status === "active" || integration?.status === "beta";
}

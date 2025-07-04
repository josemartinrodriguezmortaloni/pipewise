import { tokenStorage } from "./auth";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

/**
 * Biblioteca API para hacer solicitudes autenticadas
 */
export const api = {
  /**
   * Hacer solicitud GET autenticada
   */
  async get(endpoint: string, params: Record<string, string> = {}) {
    const queryString = new URLSearchParams(params).toString();
    const url = `${API_BASE_URL}${endpoint}${
      queryString ? `?${queryString}` : ""
    }`;

    return this.request("GET", url);
  },

  /**
   * Hacer solicitud POST autenticada
   */
  async post(endpoint: string, data: any = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    return this.request("POST", url, data);
  },

  /**
   * Hacer solicitud PUT autenticada
   */
  async put(endpoint: string, data: any = {}) {
    const url = `${API_BASE_URL}${endpoint}`;

    return this.request("PUT", url, data);
  },

  /**
   * Hacer solicitud DELETE autenticada
   */
  async delete(endpoint: string) {
    const url = `${API_BASE_URL}${endpoint}`;

    return this.request("DELETE", url);
  },

  /**
   * Método base para realizar solicitudes
   */
  async request(method: string, url: string, data?: any) {
    console.log(`🚀 API Request: ${method} ${url}`);
    if (data) {
      console.log("📋 Request data:", data);
    }

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    // Añadir token de autenticación si existe
    const token = tokenStorage.getAccessToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
      console.log(`🔐 Auth token added: ${token.substring(0, 20)}...`);
    } else {
      console.warn("⚠️ No authentication token found");
    }

    const config: RequestInit = {
      method,
      headers,
      credentials: "include",
    };

    if (data) {
      config.body = JSON.stringify(data);
    }

    try {
      console.log(`📡 Making request to: ${url}`);
      const response = await fetch(url, config);

      console.log(
        `📡 Response status: ${response.status} ${response.statusText}`
      );

      // Manejar errores HTTP
      if (!response.ok) {
        // Si el token expiró intentar refresh una sola vez
        if (response.status === 401) {
          try {
            const { refreshToken } = (await import(
              "./auth"
            )) as typeof import("./auth");
            const refreshed = await refreshToken();
            if (refreshed) {
              const newToken = tokenStorage.getAccessToken();
              if (newToken) headers["Authorization"] = `Bearer ${newToken}`;
              const retryResp = await fetch(url, { ...config, headers });
              if (retryResp.ok) {
                if (retryResp.status === 204) return null;
                return await retryResp.json();
              }
            }
            // Si falla el refresh limpiar tokens y redirigir a login
            tokenStorage.clearTokens();
            if (typeof window !== "undefined") window.location.href = "/login";
          } catch (e) {
            console.error("⚠️ Token refresh attempt failed", e);
          }
        }

        const errorData = await response.json().catch(() => ({
          detail: `Error HTTP ${response.status}: ${response.statusText}`,
        }));

        console.error("❌ API Error response:", errorData);
        throw new Error(
          errorData.detail ||
            `Error HTTP ${response.status}: ${response.statusText}`
        );
      }

      // Para respuestas 204 No Content
      if (response.status === 204) {
        console.log("✅ 204 No Content response");
        return null;
      }

      const responseData = await response.json();
      console.log("✅ API Response data:", responseData);
      return responseData;
    } catch (error) {
      console.error("❌ API request failed:", error);
      throw error;
    }
  },

  /**
   * Iniciar flujo OAuth
   */
  async startOAuthFlow(integrationKey: string, redirectUrl?: string) {
    console.log(`🔐 Starting OAuth flow for: ${integrationKey}`);
    console.log(`📋 Redirect URL: ${redirectUrl}`);

    const params: Record<string, string> = {};
    if (redirectUrl) {
      params["redirect_url"] = redirectUrl;
    }

    // Realizar una petición GET que devuelve un JSON con la URL de autorización
    const response = await this.get(
      `/api/integrations/${integrationKey}/oauth/start`,
      params
    );

    console.log("✅ OAuth flow started, received response:", response);
    // Devolver la respuesta completa para que el componente maneje la redirección
    return response;
  },
};

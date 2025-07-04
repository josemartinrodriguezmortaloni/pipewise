export interface User {
  id: string;
  email: string;
  full_name: string;
  company?: string;
  phone?: string;
  role: "user" | "manager" | "admin";
  is_active: boolean;
  email_confirmed: boolean;
  has_2fa: boolean;
  created_at: string;
  last_login?: string;
}

export interface LoginCredentials {
  email: string;
  password: string;
  remember_me?: boolean;
}

export interface RegisterData {
  email: string;
  password: string;
  full_name: string;
  company?: string;
  phone?: string;
  role?: "user" | "manager" | "admin";
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
  requires_2fa?: boolean;
}

export type RegisterResponse = AuthResponse;

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

// Funciones para manejar tokens
export const tokenStorage = {
  getAccessToken: (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
  },

  getRefreshToken: (): string | null => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("refresh_token");
  },

  setTokens: (accessToken: string, refreshToken: string): void => {
    if (typeof window === "undefined") return;
    localStorage.setItem("access_token", accessToken);
    localStorage.setItem("refresh_token", refreshToken);
  },

  clearTokens: (): void => {
    if (typeof window === "undefined") return;
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user_data");
  },
};

// Funciones para manejar datos del usuario
export const userStorage = {
  getUser: (): User | null => {
    if (typeof window === "undefined") return null;
    const userData = localStorage.getItem("user_data");
    if (!userData) return null;
    try {
      return JSON.parse(userData);
    } catch (err) {
      console.error("Failed to parse user_data from localStorage", err);
      return null;
    }
  },

  setUser: (user: User): void => {
    if (typeof window === "undefined") return;
    localStorage.setItem("user_data", JSON.stringify(user));
  },

  clearUser: (): void => {
    if (typeof window === "undefined") return;
    localStorage.removeItem("user_data");
  },
};

// Función para hacer requests autenticados
export async function authenticatedFetch(
  url: string,
  options: RequestInit = {}
) {
  const token = tokenStorage.getAccessToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    const refreshed = await refreshToken();
    if (refreshed) {
      headers.Authorization = `Bearer ${tokenStorage.getAccessToken()}`;
      return fetch(`${API_BASE_URL}${url}`, { ...options, headers });
    } else {
      tokenStorage.clearTokens();
      userStorage.clearUser();
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new Error("Session expired");
    }
  }

  return response;
}

// Función de login
export async function login(
  credentials: LoginCredentials
): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE_URL}/api/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    const raw = await response.text();
    try {
      const errorJson = JSON.parse(raw);
      throw new Error(errorJson.detail || "Login failed");
    } catch {
      throw new Error(raw || "Login failed");
    }
  }

  const data: AuthResponse = await response.json();
  if (!data.requires_2fa) {
    tokenStorage.setTokens(data.access_token, data.refresh_token);
    userStorage.setUser(data.user);
  }
  return data;
}

// Función de login con Google - Implementación completa y mejorada
export async function loginWithGoogle(): Promise<void> {
  try {
    const { supabase } = await import("@/lib/supabase");

    // Configurar las opciones de OAuth
    const { data, error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/dashboard`,
        queryParams: {
          access_type: "offline",
          prompt: "consent",
        },
      },
    });

    if (error) {
      console.error("Google OAuth initiation error:", error);
      throw new Error(error.message || "Failed to initiate Google sign-in");
    }

    console.log("Google OAuth initiated successfully");

    // No necesitamos hacer nada más aquí ya que Supabase redirige automáticamente
    // El resto del flujo se maneja en el onAuthStateChange listener
  } catch (error) {
    console.error("Google login error:", error);
    throw error;
  }
}

// Función de registro
export async function register(
  userData: RegisterData
): Promise<RegisterResponse> {
  const response = await fetch(`${API_BASE_URL}/api/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(userData),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Registration failed");
  }

  const data: RegisterResponse = await response.json();
  if (data.access_token && data.user) {
    tokenStorage.setTokens(data.access_token, data.refresh_token);
    userStorage.setUser(data.user);
  }
  return data;
}

// Función de logout
export async function logout(): Promise<void> {
  try {
    const token = tokenStorage.getAccessToken();
    if (token) {
      await authenticatedFetch("/api/api/auth/logout", { method: "POST" });
    }
  } catch (error) {
    console.error("Logout error:", error);
  } finally {
    tokenStorage.clearTokens();
    userStorage.clearUser();
  }
}

// Función para renovar token
export async function refreshToken(): Promise<boolean> {
  const refresh = tokenStorage.getRefreshToken();
  if (!refresh) return false;

  try {
    const response = await fetch(`${API_BASE_URL}/api/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refresh }),
    });

    if (!response.ok) return false;

    const data = await response.json();
    tokenStorage.setTokens(data.access_token, data.refresh_token);
    return true;
  } catch (error) {
    console.error("Token refresh error:", error);
    return false;
  }
}

// Función para validar token actual
export async function validateToken(): Promise<User | null> {
  try {
    const response = await authenticatedFetch("/api/api/auth/validate");
    if (!response.ok) return null;

    const data = await response.json();
    if (data.valid && data.user) {
      userStorage.setUser(data.user);
      return data.user;
    }
    return null;
  } catch (error) {
    console.error("Token validation error:", error);
    return null;
  }
}

// Función para obtener el perfil del usuario
export async function getUserProfile(): Promise<User | null> {
  try {
    const response = await authenticatedFetch("/api/api/auth/profile");
    if (!response.ok) return null;

    const userData = await response.json();
    userStorage.setUser(userData);
    return userData;
  } catch (error) {
    console.error("Get profile error:", error);
    return null;
  }
}

import { createClient } from "@supabase/supabase-js";

// Hybrid approach: Supabase for Auth (Google OAuth), Backend API for data
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

if (!supabaseUrl) {
  throw new Error("NEXT_PUBLIC_SUPABASE_URL environment variable is required");
}

if (!supabaseAnonKey) {
  throw new Error("SUPABASE_ANON_KEY environment variable is required");
}

// Native Supabase client for authentication
export const supabase = createClient(supabaseUrl, supabaseAnonKey);

class APIClient {
  private baseURL: string;
  private tenantId: string | null = null;

  constructor() {
    this.baseURL = API_BASE_URL;

    // Get tenant ID from subdomain or localStorage
    if (typeof window !== "undefined") {
      const hostname = window.location.hostname;
      const subdomain = hostname.split(".")[0];

      if (subdomain && subdomain !== "localhost" && subdomain !== "www") {
        this.tenantId = subdomain;
      } else {
        // Fallback to localStorage for development
        this.tenantId = localStorage.getItem("tenant_id") || "default";
      }
    }
  }

  private getHeaders(): HeadersInit {
    const headers: HeadersInit = {
      "Content-Type": "application/json",
    };

    if (this.tenantId) {
      headers["X-Tenant-ID"] = this.tenantId;
    }

    // Add auth token if available
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("auth_token");
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }
    }

    return headers;
  }

  async request(endpoint: string, options: RequestInit = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config: RequestInit = {
      ...options,
      headers: {
        ...this.getHeaders(),
        ...options.headers,
      },
    };

    const response = await fetch(url, config);

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // Auth methods
  async signIn(email: string, password: string) {
    return this.request("/api/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  async signUp(
    email: string,
    password: string,
    userData: Record<string, unknown>
  ) {
    return this.request("/api/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, ...userData }),
    });
  }

  async signOut() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("auth_token");
      localStorage.removeItem("user_data");
    }

    return this.request("/api/api/auth/logout", {
      method: "POST",
    });
  }

  async getCurrentUser() {
    return this.request("/api/api/auth/profile");
  }

  setTenantId(tenantId: string) {
    this.tenantId = tenantId;
    if (typeof window !== "undefined") {
      localStorage.setItem("tenant_id", tenantId);
    }
  }

  getTenantId(): string {
    return this.tenantId || "default";
  }
}

// Enhanced API client that syncs with Supabase auth
export const apiClient = new APIClient();

// Sync Supabase session with our backend
export async function syncAuthWithBackend(
  supabaseSession: {
    access_token?: string;
    user?: unknown;
  } | null
) {
  if (!supabaseSession?.access_token) return null;

  try {
    // Send Supabase token to our backend for verification and user sync
    const response = await fetch(`${API_BASE_URL}/api/api/auth/supabase-sync`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${supabaseSession.access_token}`,
        "X-Tenant-ID": apiClient.getTenantId(),
      },
      body: JSON.stringify({
        user: supabaseSession.user,
        provider_token: supabaseSession.access_token,
      }),
    });

    if (response.ok) {
      const backendAuth = await response.json();

      // Store our backend token
      if (typeof window !== "undefined") {
        localStorage.setItem("auth_token", backendAuth.access_token);
        localStorage.setItem("user_data", JSON.stringify(backendAuth.user));
      }

      return backendAuth;
    }
  } catch (error) {
    console.error("Failed to sync auth with backend:", error);
  }

  return null;
}

// Helper function to handle Google OAuth
export async function signInWithGoogle() {
  const { data, error } = await supabase.auth.signInWithOAuth({
    provider: "google",
    options: {
      redirectTo: `${window.location.origin}/auth/callback`,
    },
  });

  return { data, error };
}

// Helper function to handle email/password auth
export async function signInWithPassword(email: string, password: string) {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  });

  if (data.session) {
    // Sync with backend
    await syncAuthWithBackend(data.session);
  }

  return { data, error };
}

// Helper function for sign up
export async function signUpWithPassword(
  email: string,
  password: string,
  options?: Record<string, unknown>
) {
  const { data, error } = await supabase.auth.signUp({
    email,
    password,
    options,
  });

  return { data, error };
}

// Enhanced sign out that clears both Supabase and backend auth
export async function signOut() {
  // Sign out from Supabase
  const { error } = await supabase.auth.signOut();

  // Clear backend auth
  if (typeof window !== "undefined") {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user_data");
  }

  return { error };
}

// Types para TypeScript
export interface User {
  id: string;
  email: string;
  full_name: string;
  company?: string;
  phone?: string;
  has_2fa: boolean;
  created_at: string;
  last_login?: string;
}

export interface AuthSession {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: User;
}

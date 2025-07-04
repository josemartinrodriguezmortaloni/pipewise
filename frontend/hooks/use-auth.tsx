"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import {
  User,
  LoginCredentials,
  RegisterData,
  AuthResponse,
  RegisterResponse,
  login as authLogin,
  register as authRegister,
  logout as authLogout,
  loginWithGoogle as authLoginWithGoogle,
  validateToken,
  tokenStorage,
  userStorage,
} from "@/lib/auth";
import { supabase } from "@/lib/supabase";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginCredentials) => Promise<AuthResponse>;
  register: (userData: RegisterData) => Promise<RegisterResponse>;
  logout: () => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Listen for auth state changes
  useEffect(() => {
    // Immediately try to set the user from existing data
    const storedUser = userStorage.getUser();
    if (storedUser) {
      setUser(storedUser);
    }

    const { data: authListener } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        console.log("Auth event:", event, {
          hasSession: !!session,
          hasUser: !!session?.user,
          provider: session?.user?.app_metadata?.provider,
        });

        if (event === "SIGNED_OUT") {
          setUser(null);
          tokenStorage.clearTokens();
          userStorage.clearUser();
        } else if (
          event === "SIGNED_IN" ||
          event === "TOKEN_REFRESHED" ||
          event === "INITIAL_SESSION"
        ) {
          if (session?.user && session.access_token) {
            try {
              // For OAuth providers (Google), sync with backend
              const isOAuthProvider =
                session.user.app_metadata?.provider !== "email";

              if (isOAuthProvider) {
                console.log("OAuth login detected, syncing with backend...");

                // Sync with backend using the supabase-sync endpoint
                const { syncAuthWithBackend } = await import("@/lib/supabase");
                const backendAuth = await syncAuthWithBackend(session);

                if (backendAuth?.user) {
                  setUser(backendAuth.user);
                  console.log("✅ OAuth user synchronized with backend");
                } else {
                  console.warn(
                    "⚠️ Backend sync failed, using fallback user profile"
                  );
                  // Fallback to basic user profile from Supabase
                  setUser({
                    id: session.user.id,
                    email: session.user.email ?? "",
                    full_name:
                      (session.user.user_metadata?.full_name as string) ||
                      (session.user.user_metadata?.name as string) ||
                      session.user.email?.split("@")[0] ||
                      "Usuario",
                    company: session.user.user_metadata?.company as
                      | string
                      | undefined,
                    phone: session.user.user_metadata?.phone as
                      | string
                      | undefined,
                    role: "user",
                    is_active: true,
                    email_confirmed: true,
                    has_2fa: false,
                    created_at:
                      session.user.created_at ?? new Date().toISOString(),
                    last_login: new Date().toISOString(),
                  } as any);
                }
              } else {
                // For email/password auth, try to validate with backend
                if (session.access_token && session.refresh_token) {
                  tokenStorage.setTokens(
                    session.access_token,
                    session.refresh_token
                  );
                }

                let validatedUser = null;
                try {
                  validatedUser = await validateToken();
                } catch (error) {
                  console.warn("Backend token validation failed:", error);
                }

                if (validatedUser) {
                  setUser(validatedUser);
                } else {
                  // Fallback for email auth
                  setUser({
                    id: session.user.id,
                    email: session.user.email ?? "",
                    full_name:
                      (session.user.user_metadata?.full_name as string) ||
                      session.user.email?.split("@")[0] ||
                      "Usuario",
                    company: session.user.user_metadata?.company as
                      | string
                      | undefined,
                    phone: session.user.user_metadata?.phone as
                      | string
                      | undefined,
                    role: "user",
                    is_active: true,
                    email_confirmed: true,
                    has_2fa: false,
                    created_at:
                      session.user.created_at ?? new Date().toISOString(),
                    last_login: new Date().toISOString(),
                  } as any);
                }
              }
            } catch (error) {
              console.error("Error processing auth session:", error);
              // Even if backend sync fails, we can still set a basic user profile
              setUser({
                id: session.user.id,
                email: session.user.email ?? "",
                full_name:
                  (session.user.user_metadata?.full_name as string) ||
                  (session.user.user_metadata?.name as string) ||
                  session.user.email?.split("@")[0] ||
                  "Usuario",
                company: session.user.user_metadata?.company as
                  | string
                  | undefined,
                phone: session.user.user_metadata?.phone as string | undefined,
                role: "user",
                is_active: true,
                email_confirmed: true,
                has_2fa: false,
                created_at: session.user.created_at ?? new Date().toISOString(),
                last_login: new Date().toISOString(),
              } as any);
            }
          }
        }
        setIsLoading(false);
      }
    );

    // Initial check to hide loader if no session
    supabase.auth.getSession().then(({ data }) => {
      if (!data.session) {
        setIsLoading(false);
      }
    });

    return () => {
      authListener.subscription.unsubscribe();
    };
  }, []);

  const login = async (
    credentials: LoginCredentials
  ): Promise<AuthResponse> => {
    setIsLoading(true);
    try {
      const response = await authLogin(credentials);

      if (!response.requires_2fa) {
        setUser(response.user);
      }

      return response;
    } catch (error) {
      console.error("Login error:", error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (
    userData: RegisterData
  ): Promise<RegisterResponse> => {
    setIsLoading(true);
    try {
      const response = await authRegister(userData);
      if (response.user) {
        setUser(response.user);
      }
      return response;
    } catch (error) {
      console.error("Register error:", error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await authLogout();
      setUser(null);
    } catch (error) {
      console.error("Logout error:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const loginWithGoogle = async () => {
    setIsLoading(true);
    try {
      await authLoginWithGoogle();
      // Redirección manejada por Supabase; el listener onAuthStateChange
      // actualizará isLoading cuando la sesión se confirme.
    } catch (error) {
      console.error("Google login error:", error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const refreshUser = async () => {
    try {
      const validatedUser = await validateToken();
      if (validatedUser) {
        setUser(validatedUser);
      } else {
        setUser(null);
        tokenStorage.clearTokens();
        userStorage.clearUser();
      }
    } catch (error) {
      console.error("Error refreshing user:", error);
      setUser(null);
    }
  };

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    loginWithGoogle,
    refreshUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

// Hook para proteger rutas
import { useRouter } from "next/navigation";

export function useRequireAuth(redirectTo = "/login") {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push(redirectTo);
    }
  }, [isAuthenticated, isLoading, redirectTo, router]);

  return { isAuthenticated, isLoading };
}

// Hook para datos específicos del usuario
export function useUserData() {
  const { user } = useAuth();

  return {
    user,
    isAdmin: user?.role === "admin",
    isManager: user?.role === "manager" || user?.role === "admin",
    isUser: user?.role === "user",
    hasRole: (role: "user" | "manager" | "admin") => user?.role === role,
    userInitials: user
      ? `${user.full_name?.split(" ")[0]?.[0] || ""}${
          user.full_name?.split(" ")[1]?.[0] || ""
        }`.trim() ||
        user.email?.[0]?.toUpperCase() ||
        "U"
      : "",
    displayName: user?.full_name || user?.email || "Usuario",
  };
}

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
        console.log("Auth event:", event);
        if (event === "SIGNED_OUT") {
          setUser(null);
          tokenStorage.clearTokens();
          userStorage.clearUser();
        } else if (event === "SIGNED_IN" || event === "TOKEN_REFRESHED") {
          if (session?.user) {
            // Let's use the user profile from our own DB via validateToken
            const validatedUser = await validateToken();
            setUser(validatedUser);
            if (session.access_token && session.refresh_token) {
              tokenStorage.setTokens(
                session.access_token,
                session.refresh_token
              );
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
      /* no-op: listener will flip loading state */
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

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
  validateToken,
  tokenStorage,
  userStorage,
} from "@/lib/auth";

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (
    credentials: LoginCredentials,
    fromRegistration?: boolean
  ) => Promise<AuthResponse>;
  register: (userData: RegisterData) => Promise<RegisterResponse>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Verificar si hay un usuario autenticado al cargar
  useEffect(() => {
    checkAuthStatus();
  }, []);

  const checkAuthStatus = async () => {
    try {
      // Primero verificar si hay datos en localStorage
      const storedUser = userStorage.getUser();
      const token = tokenStorage.getAccessToken();

      if (storedUser && token) {
        // Validar el token con el servidor
        const validatedUser = await validateToken();
        if (validatedUser) {
          setUser(validatedUser);
        } else {
          // Token inválido, limpiar datos
          tokenStorage.clearTokens();
          userStorage.clearUser();
          setUser(null);
        }
      } else {
        setUser(null);
      }
    } catch (error) {
      console.error("Error checking auth status:", error);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (
    credentials: LoginCredentials,
    fromRegistration = false
  ): Promise<AuthResponse> => {
    setIsLoading(true);
    try {
      // Si viene del registro, el login ya se hizo en el backend.
      // Aquí solo necesitamos obtener los datos y guardarlos.
      // La llamada a authLogin se hace para obtener el token y datos del usuario.
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

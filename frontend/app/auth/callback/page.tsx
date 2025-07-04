"use client";

import { useEffect, Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isAuthenticated, isLoading } = useAuth();
  const [status, setStatus] = useState<"loading" | "error" | "success">(
    "loading"
  );
  const [message, setMessage] = useState("Procesando autenticación...");

  useEffect(() => {
    // Check for OAuth errors first
    const error = searchParams.get("error");
    const errorDescription = searchParams.get("error_description");
    const errorCode = searchParams.get("error_code");

    if (error) {
      console.error("OAuth error:", { error, errorCode, errorDescription });
      setStatus("error");

      let userFriendlyMessage = "Error de autenticación con Google";

      if (
        error === "server_error" &&
        errorDescription?.includes("Unable to exchange external code")
      ) {
        userFriendlyMessage =
          "Error de configuración OAuth. Verifica que las credenciales de Google OAuth estén configuradas correctamente en Supabase.";
        console.error(
          "OAuth Configuration Error: This usually means there's an issue with Google OAuth credentials in Supabase or redirect URL mismatch."
        );
      } else if (errorDescription) {
        userFriendlyMessage = `Error: ${decodeURIComponent(errorDescription)}`;
      }

      setMessage(userFriendlyMessage);

      // Redirect to login after showing error
      setTimeout(() => {
        router.replace("/login");
      }, 5000);
      return;
    }

    // Handle successful authentication flow
    const handleSuccessFlow = () => {
      if (isAuthenticated) {
        console.log("✅ User authenticated, redirecting to dashboard");
        setStatus("success");
        setMessage("¡Autenticación exitosa! Redirigiendo...");
        setTimeout(() => {
          router.replace("/dashboard");
        }, 1500);
      } else if (!isLoading) {
        console.log(
          "❌ User not authenticated after callback, redirecting to login"
        );
        setStatus("error");
        setMessage(
          "No se pudo completar la autenticación. Redirigiendo al login..."
        );
        setTimeout(() => {
          router.replace("/login");
        }, 3000);
      }
    };

    // Give some time for the auth state to update
    const timeout = setTimeout(handleSuccessFlow, 1000);

    return () => clearTimeout(timeout);
  }, [isAuthenticated, isLoading, router, searchParams]);

  const getStatusColor = () => {
    switch (status) {
      case "success":
        return "text-green-600";
      case "error":
        return "text-red-600";
      default:
        return "text-muted-foreground";
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case "success":
        return (
          <div className="rounded-full h-12 w-12 bg-green-100 flex items-center justify-center">
            <svg
              className="h-6 w-6 text-green-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
          </div>
        );
      case "error":
        return (
          <div className="rounded-full h-12 w-12 bg-red-100 flex items-center justify-center">
            <svg
              className="h-6 w-6 text-red-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </div>
        );
      default:
        return (
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        );
    }
  };

  return (
    <div className="flex h-screen w-full items-center justify-center bg-background">
      <div className="flex flex-col items-center gap-6 p-8 max-w-md text-center">
        {getStatusIcon()}

        <div className="space-y-2">
          <h1 className="text-2xl font-semibold">
            {status === "success" && "¡Autenticación Exitosa!"}
            {status === "error" && "Error de Autenticación"}
            {status === "loading" && "Procesando..."}
          </h1>

          <p className={`text-sm ${getStatusColor()}`}>{message}</p>
        </div>

        {status === "error" && (
          <div className="space-y-2">
            <button
              onClick={() => router.push("/login")}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
            >
              Volver al Login
            </button>

            <p className="text-xs text-muted-foreground">
              Si el problema persiste, contacta al administrador
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen w-full items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            <p className="text-muted-foreground">Cargando autenticación...</p>
          </div>
        </div>
      }
    >
      <AuthCallbackContent />
    </Suspense>
  );
}

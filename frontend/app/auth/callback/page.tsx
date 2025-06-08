"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";

export default function AuthCallbackPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    // The `useAuth` hook's onAuthStateChange listener will handle the session.
    // We just need to wait for the authentication state to be resolved.
    if (!isLoading) {
      if (isAuthenticated) {
        router.push("/dashboard");
      } else {
        // If auth fails for some reason, send back to login
        router.push("/login");
      }
    }
  }, [isAuthenticated, isLoading, router]);

  return (
    <div className="flex h-screen w-full items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
        <p className="text-muted-foreground">
          Finalizando autenticación, por favor espera...
        </p>
      </div>
    </div>
  );
}

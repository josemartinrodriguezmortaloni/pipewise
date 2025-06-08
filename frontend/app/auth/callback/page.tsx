"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";

export default function AuthCallbackPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    const base = process.env.NEXT_PUBLIC_APP_URL ?? "";
    if (isAuthenticated) {
      router.replace(`${base}/dashboard`);
    } else if (!isLoading) {
      router.replace(`${base}/login`);
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

"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";

export default function Home() {
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (isLoading) return;
    const base = process.env.NEXT_PUBLIC_APP_URL ?? "";
    if (isAuthenticated) router.replace(`${base}/dashboard`);
    else router.replace(`${base}/login`);
  }, [isAuthenticated, isLoading, router]);

  // Optional fallback UI while deciding
  return (
    <div className="flex h-screen w-full items-center justify-center text-muted-foreground">
      Loading...
    </div>
  );
}

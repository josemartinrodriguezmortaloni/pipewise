import { Suspense } from "react";
import { AppSidebar } from "@/components/app-sidebar";
import { ProtectedRoute } from "@/components/protected-route";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Skeleton } from "@/components/ui/skeleton";

function HeaderSkeleton() {
  return (
    <div className="flex h-12 items-center gap-2 px-4">
      <Skeleton className="h-8 w-8" />
      <Skeleton className="h-6 w-32" />
    </div>
  );
}

export default function ChatLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <SidebarProvider>
        <Suspense fallback={<div className="w-72 bg-muted" />}>
          <AppSidebar />
        </Suspense>

        <SidebarInset className="m-0 flex-1 rounded-none shadow-none">
          <div className="flex flex-1 flex-col">
            <Suspense fallback={<HeaderSkeleton />}>
              <header className="sticky top-0 z-40 flex h-12 shrink-0 items-center gap-2 border-b bg-background px-4">
                <SidebarTrigger />
                <nav
                  aria-label="Chat navigation"
                  className="flex items-center gap-2"
                >
                  <span className="text-sm font-medium text-muted-foreground">
                    Chat
                  </span>
                </nav>
              </header>
            </Suspense>

            <main id="main-content" className="flex-1">
              {children}
            </main>
          </div>
        </SidebarInset>
      </SidebarProvider>
    </ProtectedRoute>
  );
}

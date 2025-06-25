// Settings Layout - Server Component with modern React 19 patterns
import { Suspense } from "react";
import { AppSidebar } from "@/components/app-sidebar";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { ProtectedRoute } from "@/components/protected-route";
import { Skeleton } from "@/components/ui/skeleton";

// Loading components for Suspense boundaries
function SettingsSkeleton() {
  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="flex items-center justify-between mb-6">
        <div>
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-96 mt-2" />
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-64 w-full" />
        ))}
      </div>
    </div>
  );
}

function HeaderSkeleton() {
  return (
    <div className="flex items-center gap-2 h-12 px-4">
      <Skeleton className="h-8 w-8" />
      <Skeleton className="h-6 w-32" />
    </div>
  );
}

// Server Component Layout with nested loading states
export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ProtectedRoute>
      <SidebarProvider>
        {/* Sidebar with loading boundary */}
        <Suspense fallback={<div className="w-72 bg-muted" />}>
          <AppSidebar />
        </Suspense>

        <SidebarInset className="m-0 rounded-none shadow-none">
          <div className="flex flex-1 flex-col">
            {/* Header with Suspense boundary */}
            <Suspense fallback={<HeaderSkeleton />}>
              <header className="sticky top-0 z-40 flex h-12 shrink-0 items-center gap-2 bg-background px-4">
                <SidebarTrigger />
                <nav
                  aria-label="Settings navigation"
                  className="flex items-center gap-2"
                >
                  <span className="text-sm font-medium text-muted-foreground">
                    Settings
                  </span>
                </nav>
              </header>
            </Suspense>

            {/* Main content area without container queries */}
            <div className="flex flex-1 flex-col">
              <main id="main-content" className="flex-1">
                {/* Nested Suspense for settings content */}
                <Suspense fallback={<SettingsSkeleton />}>{children}</Suspense>
              </main>
            </div>
          </div>
        </SidebarInset>
      </SidebarProvider>
    </ProtectedRoute>
  );
}

// Export metadata for this layout
export const metadata = {
  title: "Settings",
  description: "Configure your account, integrations, and agent settings",
};

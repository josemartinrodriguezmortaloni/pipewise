// Leads Layout - Server Component with modern React 19 patterns
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
function LeadsSkeleton() {
  return (
    <div className="flex flex-col gap-4 p-4">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-96 w-full" />
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
export default function LeadsLayout({
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
                  aria-label="Leads navigation"
                  className="flex items-center gap-2"
                >
                  <span className="text-sm font-medium text-muted-foreground">
                    Leads
                  </span>
                </nav>
              </header>
            </Suspense>

            {/* Main content area without container queries */}
            <div className="flex flex-1 flex-col">
              <main id="main-content" className="flex-1">
                {/* Nested Suspense for leads content */}
                <Suspense fallback={<LeadsSkeleton />}>{children}</Suspense>
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
  title: "Leads",
  description: "Lead management and qualification dashboard",
};

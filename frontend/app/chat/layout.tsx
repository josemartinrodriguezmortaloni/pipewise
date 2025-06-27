// Chat Layout - Server Component with sidebar integration
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
function ChatSkeleton() {
  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 space-y-4 p-4">
        <div className="flex items-start gap-3">
          <Skeleton className="h-8 w-8 rounded-full" />
          <Skeleton className="h-16 w-3/4 rounded-lg" />
        </div>
        <div className="flex items-start gap-3 justify-end">
          <Skeleton className="h-12 w-1/2 rounded-lg" />
          <Skeleton className="h-8 w-8 rounded-full" />
        </div>
        <div className="flex items-start gap-3">
          <Skeleton className="h-8 w-8 rounded-full" />
          <Skeleton className="h-20 w-2/3 rounded-lg" />
        </div>
      </div>
      <div className="p-4 border-t">
        <Skeleton className="h-12 w-full rounded-lg" />
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
export default function ChatLayout({
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
          <div className="flex flex-1 flex-col h-screen">
            {/* Header with Suspense boundary */}
            <Suspense fallback={<HeaderSkeleton />}>
              <header className="sticky top-0 z-40 flex h-12 shrink-0 items-center gap-2 bg-background px-4 border-b">
                <SidebarTrigger />
                <nav
                  aria-label="Chat navigation"
                  className="flex items-center gap-2"
                >
                  <span className="text-sm font-medium text-muted-foreground">
                    AI Assistant Chat
                  </span>
                </nav>
              </header>
            </Suspense>

            {/* Main chat area - full height */}
            <div className="flex flex-1 flex-col min-h-0">
              <main id="chat-content" className="flex-1 min-h-0">
                {/* Nested Suspense for chat content */}
                <Suspense fallback={<ChatSkeleton />}>{children}</Suspense>
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
  title: "AI Assistant Chat",
  description:
    "Interactive chat interface with AI agents for lead qualification and management",
};

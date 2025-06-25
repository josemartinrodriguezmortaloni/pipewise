"use client";
import { IntegrationsSettings } from "@/components/integrations-settings";
import {
  SidebarProvider,
  SidebarInset,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/app-sidebar";

export default function IntegrationsPage() {
  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset className="m-0 rounded-none shadow-none">
        <div className="flex flex-1 flex-col">
          <header className="sticky top-0 z-40 flex h-12 shrink-0 items-center gap-2 bg-background px-4">
            <SidebarTrigger />
          </header>
          <div className="flex-1 space-y-4 p-6 pr-6 pb-0">
            <IntegrationsSettings />
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}

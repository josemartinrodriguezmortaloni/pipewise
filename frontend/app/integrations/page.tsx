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
    <SidebarProvider
      style={
        {
          "--sidebar-width": "calc(var(--spacing) * 72)",
          "--header-height": "calc(var(--spacing) * 12)",
        } as React.CSSProperties
      }
    >
      <AppSidebar variant="inset" />
      <SidebarInset>
        <div className="flex flex-1 flex-col">
          <header className="sticky top-0 z-40 flex h-[--header-height] shrink-0 items-center gap-2 bg-background/80 px-4 backdrop-blur lg:px-6">
            <SidebarTrigger />
          </header>
          <div className="flex-1 space-y-4 p-4 md:p-8 pt-6">
            <IntegrationsSettings />
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}

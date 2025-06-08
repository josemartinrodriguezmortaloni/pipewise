"use client";

import { AppSidebar } from "@/components/app-sidebar";
import { DataTable } from "@/components/data-table";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";

export default function LeadsPage() {
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
          <header className="sticky top-0 z-40 flex h-[--header-height] shrink-0 items-center gap-2  bg-background/80 px-4 backdrop-blur lg:px-6">
            <SidebarTrigger />
          </header>
          <div className="@container/main flex flex-1 flex-col gap-2">
            <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
              <DataTable showHeader={true} title="Leads" />
            </div>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}

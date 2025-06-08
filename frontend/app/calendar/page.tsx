"use client";

import { AppSidebar } from "@/components/app-sidebar";
import { CalendarView } from "@/components/calendar-view";
import {
  SidebarInset,
  SidebarProvider,
  SidebarTrigger,
} from "@/components/ui/sidebar";

export default function CalendarPage() {
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
          <div className="@container/main flex flex-1 flex-col gap-2">
            <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
              <div className="px-4 lg:px-6">
                <div className="flex items-center justify-between space-y-2 mb-6">
                  <h2 className="text-3xl font-bold tracking-tight">
                    Calendar
                  </h2>
                  <div className="flex items-center space-x-2">
                    <p className="text-sm text-muted-foreground">
                      Scheduled meetings and events
                    </p>
                  </div>
                </div>
                <CalendarView />
              </div>
            </div>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}

"use client";

import Link from "next/link";
import * as React from "react";
import {
  IconCalendar,
  IconDashboard,
  IconHelp,
  IconListDetails,
  IconSearch,
  IconSettings,
  IconCircle,
  IconMail,
} from "@tabler/icons-react";

import { NavMain } from "@/components/nav-main";
import { NavSecondary } from "@/components/nav-secondary";
import { NavUser } from "@/components/nav-user";
import { useAuth, useUserData } from "@/hooks/use-auth";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

const data = {
  user: {
    name: "shadcn",
    email: "m@example.com",
    avatar: "/avatars/shadcn.jpg",
  },
  navMain: [
    {
      title: "Dashboard",
      url: "/dashboard",
      icon: IconDashboard,
    },
    {
      title: "Leads",
      url: "/leads",
      icon: IconListDetails,
    },
    {
      title: "Contacted",
      url: "/contacted",
      icon: IconMail,
    },
    {
      title: "Calendar",
      url: "/calendar",
      icon: IconCalendar,
    },
  ],
  navSecondary: [
    {
      title: "Settings",
      url: "/settings",
      icon: IconSettings,
    },
    {
      title: "Get Help",
      url: "#",
      icon: IconHelp,
    },
    {
      title: "Search",
      url: "#",
      icon: IconSearch,
    },
  ],
};

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const { user } = useUserData();
  const { logout } = useAuth();

  if (!user) {
    return (
      <Sidebar
        collapsible="offcanvas"
        className="border-r border-gray-200 bg-white"
        {...props}
      >
        <SidebarHeader className="border-b border-gray-100 bg-white">
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                asChild
                className="data-[slot=sidebar-menu-button]:!p-4 hover:bg-gray-50"
              >
                <Link href="/" className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full border border-gray-200 bg-white">
                    <IconCircle className="h-4 w-4 text-gray-900" />
                  </div>
                  <span className="text-lg font-medium text-gray-900">
                    PipeWise
                  </span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarHeader>
        <SidebarContent className="px-2 py-4 bg-white">
          <NavMain items={data.navMain} />
        </SidebarContent>
      </Sidebar>
    );
  }

  return (
    <Sidebar
      collapsible="offcanvas"
      className="border-r border-gray-200 bg-white"
      {...props}
    >
      <SidebarHeader className="border-b border-gray-100 bg-white">
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              asChild
              className="data-[slot=sidebar-menu-button]:!p-4 hover:bg-gray-50"
            >
              <Link href="/" className="flex items-center gap-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full border border-gray-200 bg-white">
                  <IconCircle className="h-4 w-4 text-gray-900" />
                </div>
                <span className="text-lg font-medium text-gray-900">
                  PipeWise
                </span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent className="px-2 py-4 bg-white">
        <NavMain items={data.navMain} />
        <NavSecondary items={data.navSecondary} className="mt-auto" />
      </SidebarContent>
      <SidebarFooter className="border-t border-gray-100 bg-white">
        <NavUser
          user={{
            name: user.full_name,
            email: user.email,
            avatar: `https://avatar.vercel.sh/${user.email}`,
          }}
          onLogout={logout}
        />
      </SidebarFooter>
    </Sidebar>
  );
}

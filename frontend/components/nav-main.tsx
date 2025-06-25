"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "@tabler/icons-react";

// import { Button } from "@/components/ui/button";
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

export function NavMain({
  items,
}: {
  items: {
    title: string;
    url: string;
    icon?: Icon;
  }[];
}) {
  const pathname = usePathname();

  return (
    <SidebarGroup>
      <SidebarGroupContent className="px-0">
        <SidebarMenu className="space-y-1">
          {items.map((item) => {
            const isActive = pathname === item.url;
            return (
              <SidebarMenuItem key={item.title}>
                <SidebarMenuButton asChild tooltip={item.title}>
                  <Link
                    href={item.url}
                    className={`
                      flex items-center gap-3 px-3 py-2 text-sm font-medium transition-colors duration-150
                      ${
                        isActive
                          ? "text-gray-900 bg-gray-100"
                          : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
                      }
                      rounded-none border-none shadow-none
                    `}
                  >
                    {item.icon && (
                      <item.icon
                        className={`h-4 w-4 ${
                          isActive ? "text-gray-900" : "text-gray-500"
                        }`}
                      />
                    )}
                    <span className="font-normal">{item.title}</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            );
          })}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}

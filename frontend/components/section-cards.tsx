"use client";

import * as React from "react";
import {
  IconTrendingDown,
  IconTrendingUp,
  IconUsers,
  IconCheck,
  IconCalendar,
  IconTarget,
} from "@tabler/icons-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useLeadStats } from "@/hooks/use-lead-stats";

export function SectionCards() {
  const {
    totalLeads,
    contactedLeads,
    qualifiedLeads,
    meetingsScheduled,
    contactRate,
    qualificationRate,
    meetingRate,
    isLoading,
    error,
  } = useLeadStats();

  // Helper function to determine trend
  const getTrendIcon = (rate: number) => {
    return rate >= 50 ? IconTrendingUp : IconTrendingDown;
  };

  if (error) {
    return (
      <div className="grid grid-cols-1 gap-3 px-6 md:grid-cols-2 lg:grid-cols-4">
        <Card className="col-span-full">
          <CardHeader>
            <CardTitle className="text-sm font-medium">
              Error Loading Statistics
            </CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-3 px-6 md:grid-cols-2 lg:grid-cols-4">
      {/* Total Leads Generated */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">
            Total Leads Generated
          </CardTitle>
          <IconUsers className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {isLoading ? "..." : totalLeads.toLocaleString()}
          </div>
          <p className="text-xs text-muted-foreground">
            AI-powered lead generation
          </p>
        </CardContent>
      </Card>

      {/* Leads Contacted */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Leads Contacted</CardTitle>
          <IconCheck className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {isLoading ? "..." : contactedLeads.toLocaleString()}
          </div>
          <p className="text-xs text-muted-foreground">
            {contactRate >= 50 ? "Strong engagement" : "Improving reach"}
          </p>
        </CardContent>
      </Card>

      {/* Qualified Leads */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Qualified Leads</CardTitle>
          <IconTarget className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {isLoading ? "..." : qualifiedLeads.toLocaleString()}
          </div>
          <p className="text-xs text-muted-foreground">
            AI qualification accuracy
          </p>
        </CardContent>
      </Card>

      {/* Meetings Scheduled */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">
            Meetings Scheduled
          </CardTitle>
          <IconCalendar className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {isLoading ? "..." : meetingsScheduled.toLocaleString()}
          </div>
          <p className="text-xs text-muted-foreground">
            Ready for conversations
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

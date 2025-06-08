"use client";

import * as React from "react";
import {
  IconTrendingDown,
  IconTrendingUp,
  IconRobot,
  IconCheck,
  IconCalendar,
} from "@tabler/icons-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardAction,
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

  const getTrendVariant = (rate: number) => {
    return rate >= 50 ? "default" : "secondary";
  };

  if (error) {
    return (
      <div className="*:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card dark:*:data-[slot=card]:bg-card grid grid-cols-1 gap-4 px-4 *:data-[slot=card]:bg-gradient-to-t *:data-[slot=card]:shadow-xs lg:px-6 @xl/main:grid-cols-2 @5xl/main:grid-cols-4">
        <Card className="@container/card col-span-full">
          <CardHeader>
            <CardDescription>Error Loading Statistics</CardDescription>
            <CardTitle className="text-destructive">{error}</CardTitle>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="*:data-[slot=card]:from-primary/5 *:data-[slot=card]:to-card dark:*:data-[slot=card]:bg-card grid grid-cols-1 gap-4 px-4 *:data-[slot=card]:bg-gradient-to-t *:data-[slot=card]:shadow-xs lg:px-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {/* Total Leads Generated */}
      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Total Leads Generated</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {isLoading ? "..." : totalLeads.toLocaleString()}
          </CardTitle>
          <CardAction>
            <Badge variant="outline">
              <IconRobot />
              Automated
            </Badge>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            AI-powered lead generation <IconRobot className="size-4" />
          </div>
          <div className="text-muted-foreground">
            Leads captured by automation
          </div>
        </CardFooter>
      </Card>

      {/* Leads Contacted */}
      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Leads Contacted</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {isLoading ? "..." : contactedLeads.toLocaleString()}
          </CardTitle>
          <CardAction>
            <Badge variant={getTrendVariant(contactRate)}>
              {React.createElement(getTrendIcon(contactRate))}
              {contactRate}%
            </Badge>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            {contactRate >= 50 ? "Strong engagement rate" : "Improving reach"}
            {React.createElement(getTrendIcon(contactRate), {
              className: "size-4",
            })}
          </div>
          <div className="text-muted-foreground">
            Automated outreach messages sent
          </div>
        </CardFooter>
      </Card>

      {/* Qualified Leads */}
      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Qualified Leads</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {isLoading ? "..." : qualifiedLeads.toLocaleString()}
          </CardTitle>
          <CardAction>
            <Badge variant={getTrendVariant(qualificationRate)}>
              <IconCheck />
              {qualificationRate}%
            </Badge>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            AI qualification accuracy <IconCheck className="size-4" />
          </div>
          <div className="text-muted-foreground">
            Leads passed initial screening
          </div>
        </CardFooter>
      </Card>

      {/* Meetings Scheduled */}
      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Meetings Scheduled</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {isLoading ? "..." : meetingsScheduled.toLocaleString()}
          </CardTitle>
          <CardAction>
            <Badge variant={getTrendVariant(meetingRate)}>
              <IconCalendar />
              {meetingRate}%
            </Badge>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            Automated scheduling success <IconCalendar className="size-4" />
          </div>
          <div className="text-muted-foreground">
            Ready for sales conversations
          </div>
        </CardFooter>
      </Card>

      {/* Contact Success Rate */}
      <Card className="@container/card">
        <CardHeader>
          <CardDescription>Success Rate</CardDescription>
          <CardTitle className="text-2xl font-semibold tabular-nums @[250px]/card:text-3xl">
            {isLoading ? "..." : `${contactRate}%`}
          </CardTitle>
          <CardAction>
            <Badge variant={getTrendVariant(contactRate)}>
              {React.createElement(getTrendIcon(contactRate))}
              {contactRate >= 50 ? "Excellent" : "Growing"}
            </Badge>
          </CardAction>
        </CardHeader>
        <CardFooter className="flex-col items-start gap-1.5 text-sm">
          <div className="line-clamp-1 flex gap-2 font-medium">
            Overall automation performance
            {React.createElement(getTrendIcon(contactRate), {
              className: "size-4",
            })}
          </div>
          <div className="text-muted-foreground">
            Lead engagement effectiveness
          </div>
        </CardFooter>
      </Card>
    </div>
  );
}

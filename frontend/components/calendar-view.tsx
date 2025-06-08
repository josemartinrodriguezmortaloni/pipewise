"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ChevronLeft, ChevronRight, Calendar } from "lucide-react";
import { useApi } from "@/hooks/use-api";

interface Meeting {
  id: string;
  title: string;
  start: string;
  end: string;
  participants: string[];
  url?: string;
  platform: string;
}

interface CalendarDay {
  date: Date;
  meetings: Meeting[];
  isCurrentMonth: boolean;
  isToday: boolean;
}

export function CalendarView() {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [meetings, setMeetings] = useState<Meeting[]>([]);

  const onMeetingsSuccess = useCallback((data: { meetings: Meeting[] }) => {
    setMeetings(data.meetings || []);
  }, []);

  const {
    loading,
    error,
    execute: fetchMeetings,
  } = useApi<{ meetings: Meeting[] }>(
    "/calendar/meetings",
    {},
    {
      onSuccess: onMeetingsSuccess,
      onError: () => setMeetings([]),
    }
  );

  // Generate calendar days for the current month
  const generateCalendarDays = (): CalendarDay[] => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    // First day of the month
    const firstDay = new Date(year, month, 1);
    // Last day of the month
    const lastDay = new Date(year, month + 1, 0);

    // First day of the calendar (might be from previous month)
    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());

    // Last day of the calendar (might be from next month)
    const endDate = new Date(lastDay);
    endDate.setDate(endDate.getDate() + (6 - lastDay.getDay()));

    const days: CalendarDay[] = [];
    const currentDateTime = new Date();
    currentDateTime.setHours(0, 0, 0, 0);

    for (
      let date = new Date(startDate);
      date <= endDate;
      date.setDate(date.getDate() + 1)
    ) {
      const dayMeetings = meetings.filter((meeting) => {
        const meetingDate = new Date(meeting.start);
        return (
          meetingDate.getDate() === date.getDate() &&
          meetingDate.getMonth() === date.getMonth() &&
          meetingDate.getFullYear() === date.getFullYear()
        );
      });

      const isCurrentMonth = date.getMonth() === month;
      const isToday = date.getTime() === currentDateTime.getTime();

      days.push({
        date: new Date(date),
        meetings: dayMeetings,
        isCurrentMonth,
        isToday,
      });
    }

    return days;
  };

  // Fetch meetings when month changes
  useEffect(() => {
    const startOfMonth = new Date(
      currentDate.getFullYear(),
      currentDate.getMonth(),
      1
    );
    const endOfMonth = new Date(
      currentDate.getFullYear(),
      currentDate.getMonth() + 1,
      0
    );

    const startDate = startOfMonth.toISOString().split("T")[0];
    const endDate = endOfMonth.toISOString().split("T")[0];

    fetchMeetings(
      `/calendar/meetings?start_date=${startDate}&end_date=${endDate}`
    );
  }, [currentDate, fetchMeetings]);

  // Navigate to previous month
  const previousMonth = () => {
    setCurrentDate(
      new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1)
    );
  };

  // Navigate to next month
  const nextMonth = () => {
    setCurrentDate(
      new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1)
    );
  };

  // Navigate to today
  const goToToday = () => {
    setCurrentDate(new Date());
  };

  const calendarDays = generateCalendarDays();
  const monthNames = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
  ];

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Calendar</CardTitle>
          <CardDescription>Loading meetings...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Calendar</CardTitle>
          <CardDescription>
            <span className="text-red-500">{error.message}</span>
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Calendar Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-2xl">
                {monthNames[currentDate.getMonth()]} {currentDate.getFullYear()}
              </CardTitle>
              <CardDescription>
                {meetings.length} meeting{meetings.length !== 1 ? "s" : ""}{" "}
                scheduled this month
              </CardDescription>
            </div>
            <div className="flex items-center space-x-2">
              <Button variant="outline" size="sm" onClick={goToToday}>
                Today
              </Button>
              <Button variant="outline" size="sm" onClick={previousMonth}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <Button variant="outline" size="sm" onClick={nextMonth}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Calendar Grid */}
      <Card>
        <CardContent className="p-0">
          {/* Day Headers */}
          <div className="grid grid-cols-7 border-b">
            {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
              <div
                key={day}
                className="p-4 text-center font-medium text-sm text-muted-foreground border-r last:border-r-0"
              >
                {day}
              </div>
            ))}
          </div>

          {/* Calendar Days */}
          {!loading && meetings.length === 0 ? (
            <div className="flex h-[600px] items-center justify-center">
              <div className="text-center">
                <Calendar className="mx-auto h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-medium">No Meetings Found</h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  There are no meetings scheduled for this month.
                </p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-7 h-[600px]">
              {calendarDays.map(
                ({ date, meetings, isCurrentMonth, isToday }) => (
                  <div
                    key={date.toString()}
                    className={`p-2 border-r border-b ${
                      !isCurrentMonth ? "bg-muted/50" : ""
                    } ${isToday ? "bg-primary/10" : ""}`}
                  >
                    <span
                      className={`text-sm ${
                        !isCurrentMonth ? "text-muted-foreground" : ""
                      }`}
                    >
                      {date.getDate()}
                    </span>
                    <div className="mt-1 space-y-1">
                      {meetings.map((meeting) => (
                        <Badge
                          key={meeting.id}
                          variant="secondary"
                          className="w-full text-left font-normal"
                        >
                          {meeting.title}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

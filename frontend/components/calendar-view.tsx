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
      onError: () => {
        setMeetings([]);
      },
    }
  );

  // Generate calendar days for the current month
  const generateCalendarDays = (): CalendarDay[] => {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();

    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);

    const startDate = new Date(firstDay);
    startDate.setDate(startDate.getDate() - firstDay.getDay());

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

  const previousMonth = () => {
    setCurrentDate(
      new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1)
    );
  };

  const nextMonth = () => {
    setCurrentDate(
      new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1)
    );
  };

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

  return (
    <Card className="calendar-container">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Calendar</CardTitle>
            <CardDescription>
              {loading
                ? "Loading meetings..."
                : error
                ? "Error loading meetings - Calendar view available"
                : "Scheduled meetings and events"}
            </CardDescription>
          </div>
          <div className="flex items-center space-x-2">
            <span className="text-lg font-semibold">
              {monthNames[currentDate.getMonth()]} {currentDate.getFullYear()}
            </span>
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
      <CardContent>
        {/* Day Headers */}
        <div className="grid grid-cols-7 gap-0 mb-2">
          {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
            <div
              key={day}
              className="text-center text-sm font-medium text-muted-foreground py-2"
            >
              {day}
            </div>
          ))}
        </div>

        {/* Calendar Grid */}
        <div className="grid grid-cols-7 gap-0 border-t">
          {calendarDays.map((day, index) => (
            <div
              key={index}
              className={`min-h-[100px] p-2 border-r border-b border-gray-100 ${
                !day.isCurrentMonth
                  ? "bg-muted/30 text-muted-foreground"
                  : day.isToday
                  ? "bg-primary/10"
                  : "bg-background"
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span
                  className={`text-sm ${
                    day.isToday
                      ? "bg-primary text-primary-foreground rounded-full w-6 h-6 flex items-center justify-center font-medium"
                      : "font-medium"
                  }`}
                >
                  {day.date.getDate()}
                </span>
              </div>

              {/* Meetings for this day */}
              <div className="space-y-1">
                {day.meetings.slice(0, 2).map((meeting) => (
                  <Badge
                    key={meeting.id}
                    variant="secondary"
                    className="text-xs truncate block w-full"
                  >
                    {new Date(meeting.start).toLocaleTimeString("es-ES", {
                      hour: "2-digit",
                      minute: "2-digit",
                    })}{" "}
                    {meeting.title}
                  </Badge>
                ))}
                {day.meetings.length > 2 && (
                  <Badge variant="outline" className="text-xs">
                    +{day.meetings.length - 2} more
                  </Badge>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

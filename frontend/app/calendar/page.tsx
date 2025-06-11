import { CalendarView } from "@/components/calendar-view";

export default function CalendarPage() {
  return (
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
  );
}

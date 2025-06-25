import { ChartAreaInteractive } from "@/components/chart-area-interactive";
import { DataTable } from "@/components/data-table";
import { SectionCards } from "@/components/section-cards";

export default function Page() {
  return (
    <div className="p-6 pr-6 pb-0 space-y-6">
      <SectionCards />
      <ChartAreaInteractive />
      <DataTable showHeader={true} title="Recent Leads" />
    </div>
  );
}

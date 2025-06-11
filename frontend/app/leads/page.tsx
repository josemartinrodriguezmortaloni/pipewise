import { DataTable } from "@/components/data-table";

export default function LeadsPage() {
  return (
    <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
      <DataTable showHeader={true} title="Leads" />
    </div>
  );
}

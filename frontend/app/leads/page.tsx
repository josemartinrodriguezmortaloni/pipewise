import { DataTable } from "@/components/data-table";

export default function LeadsPage() {
  return (
    <div className="p-6 pr-6 pb-0">
      <DataTable showHeader={true} title="Leads" />
    </div>
  );
}

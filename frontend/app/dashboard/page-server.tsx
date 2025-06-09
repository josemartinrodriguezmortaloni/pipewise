// Modern Dashboard Page - React 19 Server Component with async data fetching
import { Suspense } from "react";
import { SectionCards } from "@/components/section-cards";
import { ChartAreaInteractive } from "@/components/chart-area-interactive";
import { DataTable } from "@/components/data-table";
import { Skeleton } from "@/components/ui/skeleton";

// Server-side data fetching functions (for future implementation)
// These demonstrate React 19 Server Component patterns for async data fetching

/* 
async function getDashboardStats() {
  // In a real app, this would fetch from your API
  await new Promise(resolve => setTimeout(resolve, 100));
  
  return {
    totalLeads: 1234,
    conversionRate: 23.5,
    activeDeals: 89,
    revenue: 156000,
  };
}

async function getRecentLeads() {
  // Simulate API call with actual backend integration
  await new Promise(resolve => setTimeout(resolve, 150));
  
  return [
    {
      id: "1",
      name: "John Doe", 
      email: "john@example.com",
      company: "Tech Corp",
      status: "qualified",
      created_at: new Date().toISOString(),
    },
  ];
}

async function getAnalyticsData() {
  // Simulate analytics data fetching
  await new Promise(resolve => setTimeout(resolve, 200));
  
  return {
    chartData: [
      { month: "Jan", leads: 65, conversions: 15 },
      { month: "Feb", leads: 78, conversions: 18 },
      { month: "Mar", leads: 92, conversions: 22 },
    ],
  };
}
*/

// Loading components for granular Suspense boundaries
function StatsCardsSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 px-4 lg:px-6">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="h-32 w-full rounded-lg" />
      ))}
    </div>
  );
}

function ChartSkeleton() {
  return (
    <div className="px-4 lg:px-6">
      <Skeleton className="h-64 w-full rounded-lg" />
    </div>
  );
}

function TableSkeleton() {
  return (
    <div className="px-4 lg:px-6">
      <Skeleton className="h-96 w-full rounded-lg" />
    </div>
  );
}

// Server Component wrapper for stats
async function DashboardStats() {
  // Note: SectionCards uses hooks for data, so it remains a client component
  // In a real implementation, you'd create a new ServerSectionCards component
  // that accepts server-fetched data as props
  
  return (
    <div className="px-4 lg:px-6">
      <SectionCards />
    </div>
  );
}

// Server Component for analytics
async function DashboardAnalytics() {
  // Note: ChartAreaInteractive is a client component with hooks
  // In a real implementation, you'd create a ServerChart component
  
  return (
    <div className="px-4 lg:px-6">
      <ChartAreaInteractive />
    </div>
  );
}

// Server Component for leads table
async function DashboardLeads() {
  // Note: DataTable is a client component
  // In a real implementation, you'd create a ServerDataTable component
  
  return (
    <div className="px-4 lg:px-6">
      <DataTable 
        showHeader={true} 
        title="Recent Leads"
      />
    </div>
  );
}

// Main Dashboard Page - Server Component
export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6">
      {/* Stats Cards with independent loading */}
      <Suspense fallback={<StatsCardsSkeleton />}>
        <DashboardStats />
      </Suspense>
      
      {/* Analytics Chart with independent loading */}
      <Suspense fallback={<ChartSkeleton />}>
        <DashboardAnalytics />
      </Suspense>
      
      {/* Recent Leads Table with independent loading */}
      <Suspense fallback={<TableSkeleton />}>
        <DashboardLeads />
      </Suspense>
    </div>
  );
}

// Static metadata for SEO
export const metadata = {
  title: "Dashboard Overview",
  description: "Real-time dashboard with lead analytics, conversion metrics, and recent activity",
};

// Enable static generation where possible
export const revalidate = 60; // Revalidate every 60 seconds
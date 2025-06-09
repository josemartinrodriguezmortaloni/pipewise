// Modern Loading Component - React 19 with advanced loading states
import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardLoading() {
  return (
    <div className="flex flex-col gap-4 py-4 md:gap-6 md:py-6 animate-pulse">
      {/* Header loading */}
      <div className="px-4 lg:px-6">
        <Skeleton className="h-8 w-48 mb-2" />
        <Skeleton className="h-4 w-96" />
      </div>
      
      {/* Stats cards loading */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 px-4 lg:px-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="p-6 rounded-lg border bg-card">
            <div className="flex items-center justify-between space-y-0 pb-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-4 rounded" />
            </div>
            <div className="space-y-2">
              <Skeleton className="h-8 w-16" />
              <Skeleton className="h-3 w-32" />
            </div>
          </div>
        ))}
      </div>
      
      {/* Chart loading */}
      <div className="px-4 lg:px-6">
        <div className="rounded-lg border bg-card p-6">
          <div className="mb-4">
            <Skeleton className="h-6 w-32 mb-2" />
            <Skeleton className="h-4 w-64" />
          </div>
          <div className="h-64 flex items-end space-x-2">
            {Array.from({ length: 12 }).map((_, i) => (
              <Skeleton 
                key={i} 
                className="flex-1 rounded-t"
                style={{ 
                  height: `${Math.random() * 200 + 50}px`,
                  animationDelay: `${i * 100}ms`
                }}
              />
            ))}
          </div>
        </div>
      </div>
      
      {/* Table loading */}
      <div className="px-4 lg:px-6">
        <div className="rounded-lg border bg-card">
          <div className="p-6 border-b">
            <Skeleton className="h-6 w-32 mb-2" />
            <Skeleton className="h-4 w-48" />
          </div>
          <div className="p-6">
            {/* Table header */}
            <div className="grid grid-cols-4 gap-4 mb-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-4 w-full" />
              ))}
            </div>
            
            {/* Table rows */}
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="grid grid-cols-4 gap-4 py-3 border-b last:border-0">
                {Array.from({ length: 4 }).map((_, j) => (
                  <Skeleton 
                    key={j} 
                    className="h-4 w-full"
                    style={{ animationDelay: `${(i * 4 + j) * 50}ms` }}
                  />
                ))}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// Preload key components for faster loading
export const dynamic = 'force-dynamic';
export const fetchCache = 'force-no-store';
import { Skeleton } from "@/components/ui/skeleton";

/** Analytics page loading skeleton */
export default function AnalyticsLoading() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* KPI row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="rounded-xl border bg-white p-5 shadow-sm space-y-3">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-8 w-28" />
            <div className="flex items-center gap-2">
              <Skeleton className="h-4 w-4 rounded-full" />
              <Skeleton className="h-3 w-16" />
            </div>
          </div>
        ))}
      </div>
      {/* Revenue chart */}
      <div className="rounded-xl border bg-white p-6 shadow-sm">
        <div className="flex justify-between mb-4">
          <Skeleton className="h-5 w-48" />
          <Skeleton className="h-8 w-32 rounded-lg" />
        </div>
        <Skeleton className="h-72 w-full rounded-lg" />
      </div>
      {/* Two column charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="rounded-xl border bg-white p-6 shadow-sm">
          <Skeleton className="h-5 w-36 mb-4" />
          <Skeleton className="h-56 w-full rounded-lg" />
        </div>
        <div className="rounded-xl border bg-white p-6 shadow-sm">
          <Skeleton className="h-5 w-36 mb-4" />
          <Skeleton className="h-56 w-full rounded-lg" />
        </div>
      </div>
    </div>
  );
}

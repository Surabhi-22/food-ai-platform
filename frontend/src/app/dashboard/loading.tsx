import { Skeleton } from "@/components/ui/skeleton";

/** Dashboard overview loading skeleton */
export default function DashboardLoading() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* KPI cards row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="rounded-xl border bg-white p-5 shadow-sm space-y-3">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-8 w-32" />
            <Skeleton className="h-3 w-20" />
          </div>
        ))}
      </div>
      {/* Chart placeholder */}
      <div className="rounded-xl border bg-white p-6 shadow-sm">
        <Skeleton className="h-5 w-40 mb-4" />
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
      {/* Table placeholder */}
      <div className="rounded-xl border bg-white p-6 shadow-sm space-y-3">
        <Skeleton className="h-5 w-48" />
        {[...Array(5)].map((_, i) => (
          <Skeleton key={i} className="h-10 w-full" />
        ))}
      </div>
    </div>
  );
}

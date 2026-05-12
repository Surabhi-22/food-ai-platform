import { Skeleton } from "@/components/ui/skeleton";

/** Forecasts page loading skeleton */
export default function ForecastsLoading() {
  return (
    <div className="space-y-6 animate-pulse">
      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="rounded-xl border bg-white p-5 shadow-sm space-y-3">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-7 w-24" />
            <Skeleton className="h-3 w-28" />
          </div>
        ))}
      </div>
      {/* Chart */}
      <div className="rounded-xl border bg-white p-6 shadow-sm">
        <Skeleton className="h-5 w-52 mb-4" />
        <Skeleton className="h-80 w-full rounded-lg" />
      </div>
      {/* Forecast table */}
      <div className="rounded-xl border bg-white p-6 shadow-sm space-y-3">
        <Skeleton className="h-5 w-44" />
        <Skeleton className="h-8 w-full" />
        {[...Array(6)].map((_, i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    </div>
  );
}

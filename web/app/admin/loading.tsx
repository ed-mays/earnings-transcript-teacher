/** Skeleton shown while admin analytics data loads. */
export default function AdminLoading() {
  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-12">
      {/* Title skeleton */}
      <div className="mb-8 h-9 w-64 animate-pulse rounded bg-muted" />

      {/* Stat card row skeleton */}
      <div className="mb-8 grid gap-6 sm:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-border bg-card p-5">
            <div className="mb-3 h-3 w-24 animate-pulse rounded bg-muted" />
            <div className="space-y-2">
              {Array.from({ length: 4 }).map((_, j) => (
                <div key={j} className="h-4 w-full animate-pulse rounded bg-muted" />
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Table-like skeleton */}
      <div className="rounded-lg border border-border bg-card p-5">
        <div className="mb-3 h-3 w-32 animate-pulse rounded bg-muted" />
        <div className="space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="flex items-center gap-4">
              <div className="h-4 w-24 animate-pulse rounded bg-muted" />
              <div className="h-4 flex-1 animate-pulse rounded bg-muted" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

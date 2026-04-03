/** Skeleton shown while admin health data loads. */
export default function AdminHealthLoading() {
  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-12">
      {/* Title skeleton */}
      <div className="mb-8 h-9 w-72 animate-pulse rounded bg-muted" />

      {/* 3-column status card skeleton */}
      <div className="grid gap-6 sm:grid-cols-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="rounded-lg border border-border bg-card p-5">
            <div className="mb-3 h-3 w-28 animate-pulse rounded bg-muted" />
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, j) => (
                <div key={j} className="flex items-center gap-3">
                  <div className="h-3 w-3 animate-pulse rounded-full bg-muted" />
                  <div className="h-4 w-40 animate-pulse rounded bg-muted" />
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

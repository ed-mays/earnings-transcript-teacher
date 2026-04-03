/** Shown automatically by Next.js while the transcript page fetches data. */
export default function TranscriptPageLoading() {
  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-8">
      {/* Header skeleton */}
      <div className="mb-6 flex items-baseline gap-3">
        <div className="h-9 w-24 animate-pulse rounded bg-muted" />
        <div className="h-6 w-40 animate-pulse rounded bg-muted" />
      </div>

      {/* Two-column layout skeleton */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_360px]">
        {/* Left: transcript skeleton */}
        <div className="space-y-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="space-y-1">
              <div className="h-3 w-24 animate-pulse rounded bg-muted" />
              <div className="h-4 w-full animate-pulse rounded bg-muted" />
              <div className="h-4 w-5/6 animate-pulse rounded bg-muted" />
            </div>
          ))}
        </div>

        {/* Right: metadata skeleton */}
        <div className="space-y-3">
          <div className="h-8 w-full animate-pulse rounded bg-muted" />
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-5 w-3/4 animate-pulse rounded bg-muted" />
          ))}
        </div>
      </div>
    </div>
  );
}

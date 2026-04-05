/** Shown automatically by Next.js while the home page server component loads. */
export default function HomePageLoading() {
  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-12">
      {/* Heading skeleton */}
      <div className="mb-2 h-9 w-64 animate-pulse rounded bg-muted" />
      <div className="mb-8 h-5 w-80 animate-pulse rounded bg-muted" />

      {/* Call card grid skeleton */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="animate-pulse rounded-xl border p-6 shadow-sm bg-card">
            <div className="flex items-start justify-between gap-4">
              <div className="h-7 w-16 rounded bg-muted" />
              <div className="h-4 w-24 rounded bg-muted" />
            </div>
            <div className="mt-2 h-4 w-40 rounded bg-muted" />
            <div className="mt-3 h-5 w-20 rounded-full bg-muted" />
          </div>
        ))}
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { CallCard, type CallSummary } from "./CallCard";

/** Skeleton placeholder shown while call list is loading. */
function CallCardSkeleton() {
  return (
    <div className="animate-pulse rounded-xl border p-6 shadow-sm bg-card">
      <div className="flex items-start justify-between gap-4">
        <div className="h-7 w-16 rounded bg-muted" />
        <div className="h-4 w-24 rounded bg-muted" />
      </div>
      <div className="mt-2 h-4 w-40 rounded bg-muted" />
      <div className="mt-3 h-5 w-20 rounded-full bg-muted" />
    </div>
  );
}

/** Fetches the call list from the API and renders it as a grid of cards. */
export function CallList() {
  const [calls, setCalls] = useState<CallSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<CallSummary[]>("/api/calls")
      .then(setCalls)
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load calls.");
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <CallCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">
        {error}
      </div>
    );
  }

  if (calls.length === 0) {
    return (
      <div className="rounded-xl border border-dashed px-8 py-16 text-center bg-card">
        <p className="text-lg font-medium text-foreground">No transcripts yet</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Ingest an earnings call to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {calls.map((call) => (
        <CallCard key={call.ticker} call={call} />
      ))}
    </div>
  );
}

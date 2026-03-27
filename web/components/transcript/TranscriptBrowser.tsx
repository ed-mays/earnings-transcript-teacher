"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type {
  CallDetail,
  SearchResponse,
  SearchResult,
  SpanItem,
  SpansResponse,
} from "./types";

type Section = "all" | "prepared" | "qa";

interface TranscriptBrowserProps {
  ticker: string;
  call: CallDetail;
}

/** Returns a debounced version of a value, updating only after `delay` ms of silence. */
function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);

  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);

  return debounced;
}

/** Left-pane transcript browser with section/speaker filtering, pagination, and semantic search. */
export function TranscriptBrowser({ ticker, call }: TranscriptBrowserProps) {
  const [section, setSection] = useState<Section>("all");
  const [speaker, setSpeaker] = useState<string>("");
  const [page, setPage] = useState(1);

  const [spans, setSpans] = useState<SpanItem[]>([]);
  const [total, setTotal] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchQuery, setSearchQuery] = useState("");
  const debouncedQuery = useDebounce(searchQuery, 400);
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Reset to page 1 when filters change
  useEffect(() => {
    setPage(1);
  }, [section, speaker]);

  // Fetch spans whenever filters or page change (and not in search mode)
  useEffect(() => {
    if (debouncedQuery.trim()) return; // search mode — skip span fetch

    setLoading(true);
    setError(null);

    const params = new URLSearchParams({
      section,
      page: String(page),
      page_size: "50",
    });
    if (speaker) params.set("speaker", speaker);

    api
      .get<SpansResponse>(`/api/calls/${ticker}/spans?${params}`)
      .then((data) => {
        setSpans(data.spans);
        setTotal(data.total);
        setPageSize(data.page_size);
      })
      .catch((err: unknown) => {
        setError(err instanceof Error ? err.message : "Failed to load transcript.");
      })
      .finally(() => setLoading(false));
  }, [ticker, section, speaker, page, debouncedQuery]);

  // Semantic search
  useEffect(() => {
    const q = debouncedQuery.trim();
    if (!q) {
      setSearchResults(null);
      setSearchError(null);
      return;
    }

    setSearching(true);
    setSearchError(null);

    api
      .get<SearchResponse>(`/api/calls/${ticker}/search?q=${encodeURIComponent(q)}`)
      .then((data) => setSearchResults(data.results))
      .catch((err: unknown) => {
        setSearchError(err instanceof Error ? err.message : "Search failed.");
        setSearchResults(null);
      })
      .finally(() => setSearching(false));
  }, [ticker, debouncedQuery]);

  const totalPages = Math.ceil(total / pageSize);
  const inSearchMode = Boolean(debouncedQuery.trim());

  const speakerNames = call.speakers.map((s) => s.name);

  return (
    <div className="flex flex-col gap-4">
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Section filter */}
        <div className="flex rounded-lg border border-zinc-200 bg-white text-sm overflow-hidden">
          {(["all", "prepared", "qa"] as Section[]).map((s) => (
            <button
              key={s}
              onClick={() => { setSection(s); setSearchQuery(""); }}
              className={`px-3 py-1.5 capitalize transition-colors ${
                section === s && !inSearchMode
                  ? "bg-zinc-900 text-white"
                  : "text-zinc-600 hover:bg-zinc-50"
              }`}
            >
              {s === "qa" ? "Q&A" : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>

        {/* Speaker filter */}
        {speakerNames.length > 0 && (
          <select
            value={speaker}
            onChange={(e) => { setSpeaker(e.target.value); setSearchQuery(""); }}
            className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-sm text-zinc-700 focus:outline-none focus:ring-2 focus:ring-zinc-400"
          >
            <option value="">All speakers</option>
            {speakerNames.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        )}

        {/* Semantic search */}
        <div className="relative flex-1 min-w-[200px]">
          <input
            type="search"
            placeholder="Semantic search…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-sm text-zinc-700 placeholder:text-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-400"
          />
          {searching && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-zinc-400">
              Searching…
            </span>
          )}
        </div>
      </div>

      {/* Content area */}
      {inSearchMode ? (
        <SearchResultsView results={searchResults} error={searchError} query={debouncedQuery} />
      ) : (
        <>
          <SpanListView spans={spans} loading={loading} error={error} />
          {totalPages > 1 && !loading && !error && (
            <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
          )}
        </>
      )}
    </div>
  );
}

// --- Sub-views ---

function SpanListView({
  spans,
  loading,
  error,
}: {
  spans: SpanItem[];
  loading: boolean;
  error: string | null;
}) {
  if (loading) return <SpanSkeleton />;

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
    );
  }

  if (spans.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-zinc-200 px-6 py-10 text-center text-sm text-zinc-400">
        No turns match the current filters.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {spans.map((span) => (
        <SpanBlock key={span.sequence_order} span={span} />
      ))}
    </div>
  );
}

function SpanBlock({ span }: { span: SpanItem }) {
  const isAnalyst = span.section === "qa" && span.speaker.toLowerCase().includes("analyst");
  return (
    <div
      className={`rounded-lg border p-4 ${
        isAnalyst
          ? "border-blue-100 bg-blue-50"
          : "border-zinc-200 bg-white"
      }`}
    >
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">
        {span.speaker}
        <span className="ml-2 font-normal normal-case text-zinc-400">
          · {span.section === "qa" ? "Q&A" : "Prepared"}
        </span>
      </p>
      <p className="text-sm leading-relaxed text-zinc-800">{span.text}</p>
    </div>
  );
}

function SearchResultsView({
  results,
  error,
  query,
}: {
  results: SearchResult[] | null;
  error: string | null;
  query: string;
}) {
  if (error) {
    return (
      <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
    );
  }

  if (!results) return null;

  if (results.length === 0) {
    return (
      <p className="text-sm text-zinc-400">
        No results found for <em>{query}</em>.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-zinc-400">
        {results.length} result{results.length !== 1 ? "s" : ""} for <em>{query}</em>
      </p>
      {results.map((r, i) => (
        <div key={i} className="rounded-lg border border-amber-100 bg-amber-50 p-4">
          <div className="mb-1 flex items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-zinc-500">
              {r.speaker}
              <span className="ml-2 font-normal normal-case text-zinc-400">
                · {r.section === "qa" ? "Q&A" : "Prepared"}
              </span>
            </p>
            <span className="text-xs text-zinc-400">
              {Math.round(r.similarity * 100)}% match
            </span>
          </div>
          <p className="text-sm leading-relaxed text-zinc-800">{r.text}</p>
        </div>
      ))}
    </div>
  );
}

function Pagination({
  page,
  totalPages,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  onPageChange: (p: number) => void;
}) {
  return (
    <div className="flex items-center justify-center gap-2">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-sm text-zinc-600 disabled:opacity-40 hover:bg-zinc-50"
      >
        Prev
      </button>
      <span className="text-sm text-zinc-500">
        {page} / {totalPages}
      </span>
      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-sm text-zinc-600 disabled:opacity-40 hover:bg-zinc-50"
      >
        Next
      </button>
    </div>
  );
}

function SpanSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="animate-pulse rounded-lg border border-zinc-200 bg-white p-4">
          <div className="mb-2 h-3 w-32 rounded bg-zinc-100" />
          <div className="space-y-1.5">
            <div className="h-4 rounded bg-zinc-100" />
            <div className="h-4 w-4/5 rounded bg-zinc-100" />
            <div className="h-4 w-3/5 rounded bg-zinc-100" />
          </div>
        </div>
      ))}
    </div>
  );
}

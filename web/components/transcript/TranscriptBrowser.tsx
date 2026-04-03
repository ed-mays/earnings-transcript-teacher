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
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

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

  const topRef = useRef<HTMLDivElement>(null);

  // Scroll to top when entering search mode
  useEffect(() => {
    if (inSearchMode) {
      topRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [inSearchMode]);

  // Scroll to top when page changes
  useEffect(() => {
    topRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [page]);

  return (
    <div ref={topRef} className="flex flex-col gap-4">
      {/* Section heading */}
      <div className="flex items-baseline justify-between">
        <h2 className="text-sm font-semibold text-foreground">Transcript</h2>
        {!inSearchMode && speakerNames.length > 0 && (
          <span className="text-xs text-muted-foreground">
            {speakerNames.length} speaker{speakerNames.length !== 1 ? "s" : ""}
          </span>
        )}
      </div>
      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Section filter — shadcn Tabs as segmented control */}
        <Tabs
          value={section}
          onValueChange={(v) => { setSection(v as Section); setSearchQuery(""); }}
          className="w-auto"
        >
          <TabsList>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="prepared">Prepared</TabsTrigger>
            <TabsTrigger value="qa">Q&amp;A</TabsTrigger>
          </TabsList>
        </Tabs>

        {/* Speaker filter */}
        {speakerNames.length > 0 && (
          <select
            value={speaker}
            onChange={(e) => { setSpeaker(e.target.value); setSearchQuery(""); }}
            className="h-8 rounded-lg border border-input bg-transparent px-3 py-1 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
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
          <Input
            type="search"
            placeholder="Search by meaning across all sections…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-8"
          />
          {searching && (
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
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
      <div className="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>
    );
  }

  if (spans.length === 0) {
    return (
      <p className="rounded-lg border border-dashed px-6 py-10 text-center text-sm text-muted-foreground">
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
          ? "border-info/20 bg-info/10"
          : "bg-card"
      }`}
    >
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {span.speaker}
        <span className="ml-2 font-normal normal-case text-muted-foreground/70">
          · {span.section === "qa" ? "Q&A" : "Prepared"}
        </span>
      </p>
      <p className="text-sm leading-relaxed text-foreground">{span.text}</p>
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
      <div className="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</div>
    );
  }

  if (!results) return null;

  if (results.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No results found for <em>{query}</em>.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground">
        {results.length} result{results.length !== 1 ? "s" : ""} for <em>{query}</em>
      </p>
      {results.map((r, i) => (
        <div key={i} className="rounded-lg border border-warning/20 bg-warning/10 p-4">
          <div className="mb-1 flex items-center justify-between gap-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              {r.speaker}
              <span className="ml-2 font-normal normal-case text-muted-foreground/70">
                · {r.section === "qa" ? "Q&A" : "Prepared"}
              </span>
            </p>
            <span className="text-xs text-muted-foreground">
              {Math.round(r.similarity * 100)}% match
            </span>
          </div>
          <p className="text-sm leading-relaxed text-foreground">{r.text}</p>
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
      <Button
        variant="outline"
        size="sm"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
      >
        Prev
      </Button>
      <span className="text-sm text-muted-foreground">
        {page} / {totalPages}
      </span>
      <Button
        variant="outline"
        size="sm"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
      >
        Next
      </Button>
    </div>
  );
}

function SpanSkeleton() {
  return (
    <div className="space-y-4">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="animate-pulse rounded-lg border bg-card p-4">
          <div className="mb-2 h-3 w-32 rounded bg-muted" />
          <div className="space-y-1.5">
            <div className="h-4 rounded bg-muted" />
            <div className="h-4 w-4/5 rounded bg-muted" />
            <div className="h-4 w-3/5 rounded bg-muted" />
          </div>
        </div>
      ))}
    </div>
  );
}

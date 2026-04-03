"use client";

/** Card for a single news item with a streaming "Why does this matter?" explainer. */

import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { streamNewsContext } from "@/lib/signals";
import type { NewsItem } from "./types";

interface NewsCardProps {
  item: NewsItem;
  ticker: string;
}

export function NewsCard({ item, ticker }: NewsCardProps) {
  const [context, setContext] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  async function handleContextClick() {
    if (context) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);
    let accumulated = "";

    await streamNewsContext(
      ticker,
      {
        headline: item.headline,
        summary: item.summary,
        source: item.source,
        date: item.date,
      },
      {
        onToken(token) {
          accumulated += token;
          setContext(accumulated);
        },
        onDone() {
          setLoading(false);
        },
        onError(message) {
          if (controller.signal.aborted) return;
          setError(message);
          setLoading(false);
        },
      },
      controller.signal
    );
  }

  return (
    <div className="rounded-lg border bg-card px-4 py-3 space-y-2">
      <div className="space-y-1">
        <a
          href={item.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-sm font-medium text-foreground hover:underline leading-snug block"
        >
          {item.headline}
        </a>
        <p className="text-xs text-muted-foreground">
          {item.source} · {item.date}
        </p>
      </div>

      {context ? (
        <div className="rounded-md bg-muted/50 border px-3 py-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">
            Why this matters for this call
          </p>
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => (
                <p className="text-sm text-foreground/80 mb-1 last:mb-0">{children}</p>
              ),
            }}
          >
            {context}
          </ReactMarkdown>
        </div>
      ) : error ? (
        <p className="text-xs text-destructive">{error}</p>
      ) : (
        <button
          onClick={handleContextClick}
          disabled={loading}
          className="w-full rounded-md border bg-muted/30 px-3 py-1.5 text-xs font-medium text-muted-foreground hover:bg-muted/60 transition-colors disabled:opacity-50"
        >
          {loading ? "Analysing…" : "Why does this matter for this call?"}
        </button>
      )}
    </div>
  );
}

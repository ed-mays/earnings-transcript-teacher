"use client";

/** Card for a single news item with a streaming "Why does this matter?" explainer. */

import { useRef, useState } from "react";
import { streamNewsContext } from "@/lib/signals";
import type { NewsItem } from "./types";
import { SignalsSection } from "./SignalsSection";
import { Card } from "@/components/ui/card";

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
    <Card className="px-4 py-3 gap-2">
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

      <SignalsSection
        signals={context}
        loading={loading}
        error={error}
        onFetch={handleContextClick}
        label="Why does this matter for this call?"
        variant="muted"
        topMargin=""
      />
    </Card>
  );
}

"use client";

/** Renders a topic cluster as a card with a label, narrative summary, and signals button. */

import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { streamThemeSignals } from "@/lib/signals";
import { Card } from "@/components/ui/card";

interface ThemeCardProps {
  /** The theme label (topic name). */
  label: string;
  /** One-sentence narrative summary for this theme. */
  summary: string;
  /** Ticker symbol, required for the signals endpoint. */
  ticker: string;
}

export function ThemeCard({ label, summary, ticker }: ThemeCardProps) {
  const [signals, setSignals] = useState<string | null>(null);
  const [loadingSignals, setLoadingSignals] = useState(false);
  const [signalsError, setSignalsError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  async function handleSignalsClick() {
    if (signals) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoadingSignals(true);
    setSignalsError(null);
    let accumulated = "";

    await streamThemeSignals(
      ticker,
      { label, summary },
      {
        onToken(token) {
          accumulated += token;
          setSignals(accumulated);
        },
        onDone() {
          setLoadingSignals(false);
        },
        onError(message) {
          if (controller.signal.aborted) return;
          setSignalsError(message);
          setLoadingSignals(false);
        },
      },
      controller.signal
    );
  }

  return (
    <Card className="p-4 gap-2">
      <p className="text-sm font-semibold text-foreground">{label}</p>
      {summary && (
        <p className="text-sm text-muted-foreground leading-snug">{summary}</p>
      )}

      {/* Signals section */}
      {signals ? (
        <div className="mt-1 rounded-md bg-warning/10 border border-warning/30 px-3 py-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-warning-foreground mb-1">
            📈 What this signals for investors
          </p>
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => <p className="text-sm text-warning-foreground mb-1 last:mb-0">{children}</p>,
              ul: ({ children }) => <ul className="list-disc list-inside text-sm text-warning-foreground space-y-2 mb-1">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside text-sm text-warning-foreground space-y-2 mb-1">{children}</ol>,
              li: ({ children }) => <li className="text-sm text-warning-foreground border-l-2 border-warning/40 pl-2">{children}</li>,
              strong: ({ children }) => <strong className="font-semibold text-warning-foreground">{children}</strong>,
            }}
          >
            {signals}
          </ReactMarkdown>
        </div>
      ) : signalsError ? (
        <p className="mt-1 text-xs text-destructive">{signalsError}</p>
      ) : (
        <button
          onClick={handleSignalsClick}
          disabled={loadingSignals}
          className="mt-1 w-full rounded-md border border-warning/30 bg-warning/10 px-3 py-1.5 text-xs font-medium text-warning-foreground hover:bg-warning/20 transition-colors disabled:opacity-50"
        >
          {loadingSignals ? "Analysing…" : "📈 What this signals for investors"}
        </button>
      )}
    </Card>
  );
}

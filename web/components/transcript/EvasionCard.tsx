"use client";

/** Reveal-card for a single evasion item. Curiosity-first pattern. */

import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { streamSignals } from "@/lib/signals";
import type { EvasionItem } from "./types";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";

interface EvasionCardProps {
  item: EvasionItem;
  ticker: string;
}

/** Maps defensiveness score (1–10) to severity badge content and colour classes. */
function severityBadge(score: number): { emoji: string; label: string; classes: string } {
  if (score >= 8) return { emoji: "🔴", label: "High", classes: "text-red-700 bg-red-50 dark:bg-red-900/30 dark:text-red-400" };
  if (score >= 5) return { emoji: "🟡", label: "Medium", classes: "text-amber-700 bg-amber-50 dark:bg-amber-900/30 dark:text-amber-400" };
  return { emoji: "🟢", label: "Low", classes: "text-green-700 bg-green-50 dark:bg-green-900/30 dark:text-green-400" };
}

export function EvasionCard({ item, ticker }: EvasionCardProps) {
  const [revealed, setRevealed] = useState(false);
  const [signals, setSignals] = useState<string | null>(null);
  const [loadingSignals, setLoadingSignals] = useState(false);
  const [signalsError, setSignalsError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const badge = severityBadge(item.defensiveness_score);

  async function handleSignalsClick() {
    if (signals) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoadingSignals(true);
    setSignalsError(null);
    let accumulated = "";

    await streamSignals(
      ticker,
      {
        analyst_concern: item.analyst_concern,
        defensiveness_score: item.defensiveness_score,
        evasion_explanation: item.evasion_explanation,
      },
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
    <Collapsible
      open={revealed}
      onOpenChange={setRevealed}
      className="rounded-lg border overflow-hidden bg-card"
    >
      {/* Always-visible header: analyst concern + severity + topic */}
      <CollapsibleTrigger className="w-full text-left px-4 py-3 flex items-start gap-3 hover:bg-muted transition-colors">
        <span
          className={`shrink-0 mt-0.5 rounded-full px-2 py-0.5 text-xs font-semibold ${badge.classes}`}
        >
          {badge.emoji} {badge.label}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground">{item.analyst_concern}</p>
          {item.question_topic && (
            <p className="mt-0.5 text-xs text-muted-foreground">{item.question_topic}</p>
          )}
        </div>
        <span className="shrink-0 text-xs text-muted-foreground mt-0.5">
          {revealed ? "▲" : "▼"}
        </span>
      </CollapsibleTrigger>

      {/* Revealed: full analysis + signals button */}
      <CollapsibleContent className="px-4 pb-4 pt-1 border-t">
        <p className="text-sm text-foreground/80">{item.evasion_explanation}</p>

        {/* Signals section */}
        {signals ? (
          <div className="mt-3 rounded-md bg-amber-50 border border-amber-200 px-3 py-2 dark:bg-amber-900/20 dark:border-amber-800">
            <p className="text-xs font-semibold uppercase tracking-wide text-amber-700 mb-1 dark:text-amber-400">
              📈 What this signals for investors
            </p>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => <p className="text-sm text-amber-800 mb-1 last:mb-0 dark:text-amber-300">{children}</p>,
                ul: ({ children }) => <ul className="list-disc list-inside text-sm text-amber-800 space-y-0.5 mb-1 dark:text-amber-300">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal list-inside text-sm text-amber-800 space-y-0.5 mb-1 dark:text-amber-300">{children}</ol>,
                li: ({ children }) => <li className="text-sm text-amber-800 dark:text-amber-300">{children}</li>,
                strong: ({ children }) => <strong className="font-semibold text-amber-900 dark:text-amber-200">{children}</strong>,
              }}
            >
              {signals}
            </ReactMarkdown>
          </div>
        ) : signalsError ? (
          <p className="mt-3 text-xs text-red-500">{signalsError}</p>
        ) : (
          <button
            onClick={handleSignalsClick}
            disabled={loadingSignals}
            className="mt-3 w-full rounded-md border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 hover:bg-amber-100 transition-colors disabled:opacity-50 dark:border-amber-700 dark:bg-amber-900/20 dark:text-amber-400 dark:hover:bg-amber-900/30"
          >
            {loadingSignals ? "Analysing…" : "📈 What this signals for investors"}
          </button>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}

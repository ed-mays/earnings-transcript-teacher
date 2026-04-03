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
  CollapsibleChevron,
} from "@/components/ui/collapsible";
import { getEvasionStyle, evasionScoreToLevel } from "@/lib/signal-colors";

interface EvasionCardProps {
  item: EvasionItem;
  ticker: string;
}


export function EvasionCard({ item, ticker }: EvasionCardProps) {
  const [revealed, setRevealed] = useState(false);
  const [signals, setSignals] = useState<string | null>(null);
  const [loadingSignals, setLoadingSignals] = useState(false);
  const [signalsError, setSignalsError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const badge = getEvasionStyle(evasionScoreToLevel(item.defensiveness_score));

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
          className={`shrink-0 mt-0.5 rounded-full px-2 py-0.5 text-xs font-semibold ${badge.bg} ${badge.text}`}
        >
          {badge.emoji} {badge.label}
        </span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground">{item.analyst_concern}</p>
          {item.question_topic && (
            <p className="mt-0.5 text-xs text-muted-foreground">{item.question_topic}</p>
          )}
        </div>
        <CollapsibleChevron open={revealed} className="mt-0.5" />
      </CollapsibleTrigger>

      {/* Revealed: full analysis + signals button */}
      <CollapsibleContent className="px-4 pb-4 pt-1 border-t">
        <p className="text-sm text-foreground/80">{item.evasion_explanation}</p>

        {/* Signals section */}
        {signals ? (
          <div className="mt-3 rounded-md bg-warning/10 border border-warning/30 px-3 py-2">
            <p className="text-xs font-semibold uppercase tracking-wide text-warning-foreground mb-1">
              📈 What this signals for investors
            </p>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => <p className="text-sm text-warning-foreground mb-1 last:mb-0">{children}</p>,
                ul: ({ children }) => <ul className="list-disc list-inside text-sm text-warning-foreground space-y-0.5 mb-1">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal list-inside text-sm text-warning-foreground space-y-0.5 mb-1">{children}</ol>,
                li: ({ children }) => <li className="text-sm text-warning-foreground">{children}</li>,
                strong: ({ children }) => <strong className="font-semibold text-warning-foreground">{children}</strong>,
              }}
            >
              {signals}
            </ReactMarkdown>
          </div>
        ) : signalsError ? (
          <p className="mt-3 text-xs text-destructive">{signalsError}</p>
        ) : (
          <button
            onClick={handleSignalsClick}
            disabled={loadingSignals}
            className="mt-3 w-full rounded-md border border-warning/30 bg-warning/10 px-3 py-1.5 text-xs font-medium text-warning-foreground hover:bg-warning/20 transition-colors disabled:opacity-50"
          >
            {loadingSignals ? "Analysing…" : "📈 What this signals for investors"}
          </button>
        )}
      </CollapsibleContent>
    </Collapsible>
  );
}

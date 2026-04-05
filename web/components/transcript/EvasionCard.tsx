"use client";

/** Reveal-card for a single evasion item. Curiosity-first pattern. */

import { useRef, useState } from "react";
import { streamSignals } from "@/lib/signals";
import type { EvasionItem } from "./types";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
  CollapsibleChevron,
} from "@/components/ui/collapsible";
import { getEvasionStyle, evasionScoreToLevel } from "@/lib/signal-colors";
import { SignalsSection } from "./SignalsSection";

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
      {/* Always-visible header: severity badge → analyst concern → topic */}
      <CollapsibleTrigger className="w-full text-left px-4 py-3 flex items-start gap-3 hover:bg-muted transition-colors">
        <div className="flex-1 min-w-0 space-y-1">
          <span
            className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${badge.bg} ${badge.text}`}
          >
            {badge.emoji} {badge.label}
          </span>
          <p className="text-sm font-medium text-foreground">{item.analyst_concern}</p>
          {item.question_topic && (
            <p className="text-xs text-muted-foreground">{item.question_topic}</p>
          )}
        </div>
        <CollapsibleChevron open={revealed} className="mt-0.5" />
      </CollapsibleTrigger>

      {/* Revealed: full analysis + signals button */}
      <CollapsibleContent className="px-4 pb-4 pt-1 border-t">
        <p className="text-sm text-foreground/80">{item.evasion_explanation}</p>

        <SignalsSection
          signals={signals}
          loading={loadingSignals}
          error={signalsError}
          onFetch={handleSignalsClick}
          topMargin="mt-3"
        />
      </CollapsibleContent>
    </Collapsible>
  );
}

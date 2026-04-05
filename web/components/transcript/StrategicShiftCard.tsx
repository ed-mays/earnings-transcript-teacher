/** Renders a strategic shift item showing prior vs current position. */

"use client";

import { useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { streamShiftSignals } from "@/lib/signals";
import type { StrategicShift } from "./types";
import { Card } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
  CollapsibleChevron,
} from "@/components/ui/collapsible";

interface StrategicShiftCardProps {
  shift: StrategicShift;
  ticker: string;
}

export function StrategicShiftCard({ shift, ticker }: StrategicShiftCardProps) {
  const [investorExpanded, setInvestorExpanded] = useState(false);
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

    await streamShiftSignals(
      ticker,
      {
        prior_position: shift.prior_position,
        current_position: shift.current_position,
        investor_significance: shift.investor_significance,
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
    <Card className="p-4 gap-3">
      <div className="flex flex-col gap-2">
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Before
          </p>
          <p className="text-sm text-foreground">{shift.prior_position}</p>
        </div>
        <div className="flex items-center gap-2 text-muted-foreground">
          <div className="h-px flex-1 bg-border" />
          <span className="text-xs">→</span>
          <div className="h-px flex-1 bg-border" />
        </div>
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Now
          </p>
          <p className="text-sm text-foreground">{shift.current_position}</p>
        </div>
      </div>
      <Collapsible
        open={investorExpanded}
        onOpenChange={setInvestorExpanded}
        className="border-t pt-3"
      >
        <CollapsibleTrigger className="flex w-full items-center gap-2 text-left hover:opacity-80 transition-opacity">
          <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground flex-1">
            Investor significance
          </span>
          <CollapsibleChevron open={investorExpanded} />
        </CollapsibleTrigger>
        <CollapsibleContent className="pt-2">
          <p className="text-sm text-foreground/80">{shift.investor_significance}</p>
        </CollapsibleContent>
      </Collapsible>

      {/* Signals section — on-demand "go deeper" action */}
      {signals ? (
        <div className="rounded-md bg-warning/10 border border-warning/30 px-3 py-2">
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
        <p className="text-xs text-destructive">{signalsError}</p>
      ) : (
        <button
          onClick={handleSignalsClick}
          disabled={loadingSignals}
          className="w-full rounded-md border border-warning/30 bg-warning/10 px-3 py-1.5 text-xs font-medium text-warning-foreground hover:bg-warning/20 transition-colors disabled:opacity-50"
        >
          {loadingSignals ? "Analysing…" : "📈 What this signals for investors"}
        </button>
      )}
    </Card>
  );
}

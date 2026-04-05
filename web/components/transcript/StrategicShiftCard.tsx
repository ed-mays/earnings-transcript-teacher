/** Renders a strategic shift item showing prior vs current position. */

"use client";

import { useRef, useState } from "react";
import { streamShiftSignals } from "@/lib/signals";
import type { StrategicShift } from "./types";
import { Card } from "@/components/ui/card";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
  CollapsibleChevron,
} from "@/components/ui/collapsible";
import { SignalsSection } from "./SignalsSection";

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

      <SignalsSection
        signals={signals}
        loading={loadingSignals}
        error={signalsError}
        onFetch={handleSignalsClick}
        topMargin=""
      />
    </Card>
  );
}

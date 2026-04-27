"use client";

import { MessageCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  defensivenessBand,
  evasionTypeLabel,
  JUDGMENT_LABELS,
  type Judgment,
  type QAForensicsExchange,
} from "./types";

interface QARevealPanelProps {
  exchange: QAForensicsExchange;
  judgment: Judgment;
  onDiscuss: () => void;
  onNext: () => void;
  isLast: boolean;
}

/** Reveal step: shows the system's verdict, comparison to the user's judgment,
 *  and the two paths forward (deepen via Feynman or move to next exchange). */
export function QARevealPanel({
  exchange,
  judgment,
  onDiscuss,
  onNext,
  isLast,
}: QARevealPanelProps) {
  const band = defensivenessBand(exchange.defensiveness_score);
  const typeLabel = evasionTypeLabel(exchange.evasion_type);
  const userChoiceLabel = judgment.choice ? JUDGMENT_LABELS[judgment.choice] : null;

  return (
    <div className="space-y-4 rounded-xl border border-amber-500/40 bg-amber-50/40 px-5 py-5 dark:bg-amber-500/5">
      <div className="flex flex-wrap items-center gap-2">
        <span className="rounded-md bg-amber-500/15 px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-amber-900 dark:text-amber-200">
          {band.label}
        </span>
        <span className="text-xs text-muted-foreground">
          Defensiveness {exchange.defensiveness_score}/10
        </span>
        {exchange.evasion_type ? (
          <span className="rounded-md border border-border bg-background px-2 py-0.5 text-xs font-medium text-foreground">
            {typeLabel}
          </span>
        ) : null}
      </div>

      <p className="text-xs text-muted-foreground">{band.description}.</p>

      <section aria-label="System analysis">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          What the system flagged
        </p>
        <p className="mt-1 text-sm text-foreground">{exchange.evasion_explanation}</p>
      </section>

      {userChoiceLabel ? (
        <section aria-label="Your judgment">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Your judgment
          </p>
          <p className="mt-1 text-sm text-foreground">
            <span className="font-medium">{userChoiceLabel}.</span>{" "}
            {judgment.text}
          </p>
        </section>
      ) : null}

      <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
        <Button variant="outline" onClick={onDiscuss}>
          <MessageCircle className="mr-1 h-4 w-4" aria-hidden />
          Discuss further with Feynman
        </Button>
        <Button onClick={onNext}>
          {isLast ? "Finish →" : "Next exchange →"}
        </Button>
      </div>
    </div>
  );
}

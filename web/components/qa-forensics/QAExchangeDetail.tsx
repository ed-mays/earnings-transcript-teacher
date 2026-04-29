"use client";

import { useState } from "react";
import { ChevronLeft } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { QAForensicsExchange } from "@/components/transcript/types";
import { QAExchangeCard } from "./QAExchangeCard";
import { QAChipSet } from "./QAChipSet";
import { generateChips, type Chip } from "./chips";
import { defensivenessBand, evasionTypeLabel } from "./types";

interface QAExchangeDetailProps {
  exchange: QAForensicsExchange;
  onBack: () => void;
  onStartChat: (firstMessage: string) => void;
}

/** Per-exchange detail view. Shows stakes/Q/A, an inline (no-gating) system
 *  verdict strip, suggestion chips, and a freetext input. Picking a chip OR
 *  submitting the freetext starts a fresh chat session in the parent. */
export function QAExchangeDetail({
  exchange,
  onBack,
  onStartChat,
}: QAExchangeDetailProps) {
  const [draft, setDraft] = useState("");
  const chips = generateChips(exchange);
  const band = defensivenessBand(exchange.defensiveness_score);
  const typeLabel = exchange.evasion_type
    ? evasionTypeLabel(exchange.evasion_type)
    : null;

  function handleChipPick(chip: Chip) {
    onStartChat(chip.text);
  }

  function handleFreetextSubmit() {
    const trimmed = draft.trim();
    if (!trimmed) return;
    onStartChat(trimmed);
    setDraft("");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleFreetextSubmit();
    }
  }

  return (
    <div className="mx-auto w-full max-w-3xl space-y-5 px-4 py-6">
      <Button variant="ghost" size="sm" onClick={onBack} className="-ml-2">
        <ChevronLeft className="mr-1 h-4 w-4" aria-hidden />
        Back to exchanges
      </Button>

      <QAExchangeCard exchange={exchange} />

      <section
        aria-label="System verdict"
        className="space-y-1.5 rounded-xl border border-amber-500/40 bg-amber-50/40 px-4 py-3 dark:bg-amber-500/5"
      >
        <div className="flex flex-wrap items-center gap-2">
          <Badge className="rounded-md bg-amber-500/15 text-amber-900 dark:text-amber-200">
            {band.label} · {exchange.defensiveness_score}/10
          </Badge>
          {typeLabel ? (
            <Badge variant="outline" className="rounded-md">
              {typeLabel}
            </Badge>
          ) : null}
        </div>
        <p className="text-sm text-foreground">{exchange.evasion_explanation}</p>
      </section>

      <section aria-label="Discuss" className="space-y-3">
        <p className="text-sm font-semibold text-foreground">
          How would you like to start?
        </p>
        <QAChipSet chips={chips} onPick={handleChipPick} />

        <div className="space-y-1.5 pt-2">
          <label
            htmlFor="forensics-freetext"
            className="text-xs font-semibold uppercase tracking-wide text-muted-foreground"
          >
            Or, in your own words
          </label>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
            <Textarea
              id="forensics-freetext"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="What did you notice? What would you ask the executive?"
              rows={2}
              className="flex-1"
            />
            <Button
              onClick={handleFreetextSubmit}
              disabled={!draft.trim()}
              className="sm:mb-0.5"
            >
              Send
            </Button>
          </div>
        </div>
      </section>
    </div>
  );
}

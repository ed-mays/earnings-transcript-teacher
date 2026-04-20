"use client";

import { useState } from "react";
import { MessageCircle } from "lucide-react";
import {
  Collapsible,
  CollapsibleChevron,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { evasionScoreToLevel, getEvasionStyle } from "@/lib/signal-colors";
import { cn } from "@/lib/utils";
import type { QAEvasionItem } from "@/components/transcript/types";
import type { ChatContext } from "./types";

interface EvasionCardProps {
  item: QAEvasionItem;
  onChatClick: (context: ChatContext) => void;
}

/** Amber-bordered collapsible card summarizing a Q&A evasion moment. */
export function EvasionCard({ item, onChatClick }: EvasionCardProps) {
  const [open, setOpen] = useState(false);
  const level = evasionScoreToLevel(item.defensiveness_score);
  const style = getEvasionStyle(level);

  function handleChatClick() {
    onChatClick({
      type: "evasion",
      text: item.answer_text ?? item.evasion_explanation,
      metadata: item.analyst_concern,
    });
  }

  return (
    <Collapsible
      open={open}
      onOpenChange={setOpen}
      className="my-3 overflow-hidden rounded-lg border border-amber-500/40 bg-amber-50/40 dark:bg-amber-500/5"
    >
      <div className="flex w-full items-start gap-3 px-4 py-3">
        <CollapsibleTrigger className="flex flex-1 items-start gap-3 rounded text-left hover:bg-amber-500/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500">
          <div className="flex-1 space-y-1">
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span
                className={cn(
                  "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold uppercase tracking-wide",
                  style.bg,
                  style.text,
                )}
              >
                <span aria-hidden>{style.emoji}</span>
                Evasion · {style.label}
              </span>
              <span className="text-muted-foreground">
                defensiveness {item.defensiveness_score}/10
              </span>
              {item.analyst_name ? (
                <span className="text-muted-foreground">· {item.analyst_name}</span>
              ) : null}
              {item.question_topic ? (
                <span className="text-muted-foreground">· {item.question_topic}</span>
              ) : null}
            </div>
            <p className="text-sm font-medium text-foreground">{item.analyst_concern}</p>
          </div>
          <CollapsibleChevron open={open} className="mt-1 text-amber-700" />
        </CollapsibleTrigger>
        <button
          type="button"
          aria-label="Discuss this evasion"
          onClick={handleChatClick}
          className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full text-amber-700 hover:bg-amber-500/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
        >
          <MessageCircle className="h-4 w-4" aria-hidden />
        </button>
      </div>
      <CollapsibleContent className="border-t border-amber-500/30 px-4 py-3 space-y-3 text-sm">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            What the executive avoided
          </p>
          <p>{item.evasion_explanation}</p>
        </div>
        {item.question_text ? (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Question
            </p>
            <p className="text-muted-foreground">{item.question_text}</p>
          </div>
        ) : null}
        {item.answer_text ? (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Answer
            </p>
            <p className="text-muted-foreground">{item.answer_text}</p>
          </div>
        ) : null}
      </CollapsibleContent>
    </Collapsible>
  );
}

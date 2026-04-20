"use client";

import { MessageCircle } from "lucide-react";
import { highlightTerms } from "@/lib/highlight";
import type {
  SpanItem,
  TermDefinition,
} from "@/components/transcript/types";
import { TermTooltip } from "./TermTooltip";
import type { AnnotationLayers, ChatContext } from "./types";

interface AnnotatedSpanBlockProps {
  span: SpanItem;
  layers: AnnotationLayers;
  termRegex: RegExp | null;
  termMap: ReadonlyMap<string, TermDefinition>;
  /** When set, renders a chat icon next to this span (e.g., the span is flagged for evasion). */
  evasionContext?: ChatContext;
  onChatClick: (context: ChatContext) => void;
}

/** Renders a transcript span with optional term highlights and an evasion chat icon. */
export function AnnotatedSpanBlock({
  span,
  layers,
  termRegex,
  termMap,
  evasionContext,
  onChatClick,
}: AnnotatedSpanBlockProps) {
  const content = layers.terms
    ? highlightTerms(span.text, termRegex, termMap, (matched, definition, key) => (
        <TermTooltip key={key} term={matched} definition={definition} />
      ))
    : [span.text];

  const showEvasionIcon = layers.evasion && evasionContext;

  return (
    <div className="px-4 py-3">
      <div className="mb-1 flex items-baseline justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {span.speaker}
        </p>
        {showEvasionIcon ? (
          <button
            type="button"
            aria-label="Discuss this passage"
            onClick={() => onChatClick(evasionContext)}
            className="flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full text-amber-600 hover:bg-amber-500/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
          >
            <MessageCircle className="h-4 w-4" aria-hidden />
          </button>
        ) : null}
      </div>
      <p className="text-sm leading-relaxed text-foreground">{content}</p>
    </div>
  );
}

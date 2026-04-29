"use client";

import { highlightTerms } from "@/lib/highlight";
import type {
  SpanItem,
  TermDefinition,
} from "@/components/transcript/types";
import { TermTooltip } from "./TermTooltip";
import type { AnnotationLayers } from "./types";

interface AnnotatedSpanBlockProps {
  span: SpanItem;
  layers: AnnotationLayers;
  termRegex: RegExp | null;
  termMap: ReadonlyMap<string, TermDefinition>;
}

/** Renders a transcript span with optional term highlights. */
export function AnnotatedSpanBlock({
  span,
  layers,
  termRegex,
  termMap,
}: AnnotatedSpanBlockProps) {
  const content = layers.terms
    ? highlightTerms(span.text, termRegex, termMap, (matched, definition, key) => (
        <TermTooltip key={key} term={matched} definition={definition} />
      ))
    : [span.text];

  return (
    <div className="px-4 py-3">
      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        {span.speaker}
      </p>
      <p className="text-sm leading-relaxed text-foreground">{content}</p>
    </div>
  );
}

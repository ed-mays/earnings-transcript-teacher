"use client";

import type { TermDefinition } from "@/components/transcript/types";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

interface TermTooltipProps {
  term: string;
  definition: TermDefinition;
}

/** Inline term with a dotted green underline. Click/focus reveals definition in a popover. */
export function TermTooltip({ term, definition }: TermTooltipProps) {
  return (
    <Popover>
      <PopoverTrigger
        data-slot="term-trigger"
        className="cursor-help border-b border-dashed border-green-500/70 text-foreground hover:text-green-700 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500"
        aria-label={`Definition of ${term}`}
      >
        {term}
      </PopoverTrigger>
      <PopoverContent
        role="tooltip"
        className="max-w-xs space-y-2 text-sm"
        sideOffset={4}
      >
        <p className="font-semibold">{definition.term}</p>
        <p className="text-muted-foreground">{definition.definition}</p>
        {definition.explanation ? (
          <p className="text-xs text-muted-foreground">{definition.explanation}</p>
        ) : null}
      </PopoverContent>
    </Popover>
  );
}

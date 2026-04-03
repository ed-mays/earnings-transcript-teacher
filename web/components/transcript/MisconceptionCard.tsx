"use client";

/** Reveal-card for a single misconception item. Judgment-first pattern. */

import { useState } from "react";
import type { MisconceptionItem } from "./types";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
  CollapsibleChevron,
} from "@/components/ui/collapsible";

interface MisconceptionCardProps {
  item: MisconceptionItem;
  /** When true, overrides local state and forces the card open. */
  forceExpanded?: boolean;
}

export function MisconceptionCard({ item, forceExpanded = false }: MisconceptionCardProps) {
  const [revealed, setRevealed] = useState(false);
  const isOpen = forceExpanded || revealed;

  return (
    <Collapsible
      open={isOpen}
      onOpenChange={setRevealed}
      className="rounded-lg border border-warning/30 bg-warning/10 overflow-hidden"
    >
      {/* Always-visible: the misinterpretation (the "gotcha") */}
      <CollapsibleTrigger className="w-full text-left px-4 py-3 flex items-start justify-between gap-3 hover:bg-warning/20 transition-colors">
        <p className="text-sm font-medium text-warning-foreground">{item.misinterpretation}</p>
        <CollapsibleChevron open={isOpen} className="mt-0.5 text-warning-foreground" />
      </CollapsibleTrigger>

      {/* Revealed: the correction */}
      <CollapsibleContent className="px-4 pb-3 border-t border-warning/30 pt-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-warning-foreground/70 mb-1">
          Correction
        </p>
        <p className="text-sm text-warning-foreground">{item.correction}</p>
      </CollapsibleContent>
    </Collapsible>
  );
}

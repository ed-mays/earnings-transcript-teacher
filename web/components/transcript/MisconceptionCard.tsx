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
      className="rounded-lg border border-amber-200 bg-amber-50 overflow-hidden dark:border-amber-800 dark:bg-amber-900/20"
    >
      {/* Always-visible: the misinterpretation (the "gotcha") */}
      <CollapsibleTrigger className="w-full text-left px-4 py-3 flex items-start justify-between gap-3 hover:bg-amber-100 transition-colors dark:hover:bg-amber-900/30">
        <p className="text-sm font-medium text-amber-900 dark:text-amber-200">{item.misinterpretation}</p>
        <CollapsibleChevron open={isOpen} className="mt-0.5 text-amber-600 dark:text-amber-400" />
      </CollapsibleTrigger>

      {/* Revealed: the correction */}
      <CollapsibleContent className="px-4 pb-3 border-t border-amber-200 pt-2 dark:border-amber-800">
        <p className="text-xs font-semibold uppercase tracking-wide text-amber-600 mb-1 dark:text-amber-400">
          Correction
        </p>
        <p className="text-sm text-amber-800 dark:text-amber-300">{item.correction}</p>
      </CollapsibleContent>
    </Collapsible>
  );
}

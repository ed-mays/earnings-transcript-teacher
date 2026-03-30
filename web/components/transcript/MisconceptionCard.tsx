"use client";

/** Reveal-card for a single misconception item. Judgment-first pattern. */

import { useState } from "react";
import type { MisconceptionItem } from "./types";

interface MisconceptionCardProps {
  item: MisconceptionItem;
  /** When true, overrides local state and forces the card open. */
  forceExpanded?: boolean;
}

export function MisconceptionCard({ item, forceExpanded = false }: MisconceptionCardProps) {
  const [revealed, setRevealed] = useState(false);
  const isOpen = forceExpanded || revealed;

  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 overflow-hidden">
      {/* Always-visible: the misinterpretation (the "gotcha") */}
      <button
        onClick={() => setRevealed((prev) => !prev)}
        className="w-full text-left px-4 py-3 flex items-start justify-between gap-3 hover:bg-amber-100 transition-colors"
      >
        <p className="text-sm font-medium text-amber-900">{item.misinterpretation}</p>
        <span className="shrink-0 text-xs text-amber-600 font-semibold mt-0.5">
          {isOpen ? "Hide" : "Reveal"}
        </span>
      </button>

      {/* Revealed: the correction */}
      {isOpen && (
        <div className="px-4 pb-3 border-t border-amber-200 pt-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-600 mb-1">
            Correction
          </p>
          <p className="text-sm text-amber-800">{item.correction}</p>
        </div>
      )}
    </div>
  );
}

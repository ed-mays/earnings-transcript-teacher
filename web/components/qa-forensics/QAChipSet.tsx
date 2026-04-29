"use client";

import type { Chip } from "./chips";

interface QAChipSetProps {
  chips: Chip[];
  onPick: (chip: Chip) => void;
  disabled?: boolean;
}

/** Clickable suggestion chips. Each click delivers the chip to the parent
 *  which seeds the chat panel and auto-sends. Visual style intentionally
 *  light — these are launchers, not selections. */
export function QAChipSet({ chips, onPick, disabled }: QAChipSetProps) {
  if (!chips.length) return null;
  return (
    <div className="flex flex-wrap gap-2">
      {chips.map((chip) => (
        <button
          key={chip.id}
          type="button"
          onClick={() => onPick(chip)}
          disabled={disabled}
          className="inline-flex items-center rounded-md border border-border bg-background px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
        >
          {chip.text}
        </button>
      ))}
    </div>
  );
}

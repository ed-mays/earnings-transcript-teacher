/** Renders an evasion analysis item as a card. */

import type { EvasionItem } from "./types";

interface EvasionCardProps {
  item: EvasionItem;
}

/** Maps defensiveness score (1–10) to a colour class. */
function scoreColour(score: number): string {
  if (score >= 8) return "text-red-700 bg-red-50";
  if (score >= 5) return "text-amber-700 bg-amber-50";
  return "text-green-700 bg-green-50";
}

export function EvasionCard({ item }: EvasionCardProps) {
  return (
    <div className="rounded-lg border border-zinc-200 bg-white p-4">
      <div className="flex items-start justify-between gap-3">
        <p className="text-sm font-medium text-zinc-800">{item.analyst_concern}</p>
        <span
          className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-semibold ${scoreColour(item.defensiveness_score)}`}
        >
          {item.defensiveness_score}/10
        </span>
      </div>
      <p className="mt-2 text-sm text-zinc-500">{item.evasion_explanation}</p>
    </div>
  );
}

/** Pure helper that turns an exchange into a set of suggestion chips for
 *  the Q&A Forensics detail view. The chips become the user's first chat
 *  message — auto-sent when clicked. */

import type { QAForensicsExchange } from "@/components/transcript/types";

export interface Chip {
  id: string;
  text: string;
}

const GENERIC_CHIPS: readonly Chip[] = [
  { id: "why-pivot", text: "Why might they have pivoted this way?" },
  { id: "honest-answer", text: "What would an honest answer look like?" },
  { id: "investor-confidence", text: "How does this affect investor confidence?" },
];

const TYPE_SPECIFIC_CHIPS: Record<string, Chip> = {
  deflect_to_forward_looking: {
    id: "forward-risk",
    text: "What's the risk of these forward-looking commitments?",
  },
  reframe: {
    id: "reframe-why",
    text: "Why did they want to redefine the question?",
  },
  verbose_non_answer: {
    id: "wordiness",
    text: "What does the wordiness signal?",
  },
  redirect_to_different_metric: {
    id: "metric-substitution",
    text: "Why might the metric they avoided be unflattering?",
  },
  partial_answer: {
    id: "untouched",
    text: "What did they leave untouched?",
  },
  run_out_clock: {
    id: "investor-day",
    text: "What might they reveal at the upcoming investor day?",
  },
};

/** Returns 3 generic chips plus 1 type-specific chip when evasion_type is
 *  set to a known category (and isn't 'none'). Order: generic first, then
 *  the type-specific one as the last/most-targeted choice. */
export function generateChips(exchange: QAForensicsExchange): Chip[] {
  const type = exchange.evasion_type;
  const specific =
    type && type !== "none" ? TYPE_SPECIFIC_CHIPS[type] ?? null : null;
  return specific ? [...GENERIC_CHIPS, specific] : [...GENERIC_CHIPS];
}

/** Local types and helpers for the Q&A Forensics learning mode. */

import type { QAForensicsExchange } from "@/components/transcript/types";

export const EVASION_TYPE_LABELS: Record<string, string> = {
  deflect_to_forward_looking: "Deflect to forward-looking",
  reframe: "Reframe the question",
  verbose_non_answer: "Verbose non-answer",
  redirect_to_different_metric: "Redirect to a different metric",
  partial_answer: "Partial answer",
  run_out_clock: "Run out the clock",
  none: "Direct answer",
};

export function evasionTypeLabel(type: string | null | undefined): string {
  if (!type) return "Uncategorized";
  return EVASION_TYPE_LABELS[type] ?? type;
}

export function defensivenessBand(score: number): {
  label: string;
  description: string;
} {
  if (score >= 8) return { label: "Heavy evasion", description: "Strong dodge — the answer barely engages the question" };
  if (score >= 6) return { label: "Notable evasion", description: "The answer steers away from what was asked" };
  return { label: "Mild evasion", description: "Some pivoting, but partly responsive" };
}

export type { QAForensicsExchange };

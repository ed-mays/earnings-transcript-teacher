/** Pure helper that turns an exchange into a set of suggestion chips for the
 *  Q&A Forensics detail view. Each chip becomes the user's first chat
 *  message — auto-sent when clicked.
 *
 *  Preference order:
 *    1. LLM-generated `suggested_probes` from ingestion (Tier 2 prompt) —
 *       genuinely exchange-specific, references real content.
 *    2. Templated fallback that interpolates analyst name and question topic
 *       — used for older calls that haven't been re-ingested with the new
 *       Tier 2 schema. Still better than purely generic boilerplate. */

import type { QAForensicsExchange } from "@/components/transcript/types";

export interface Chip {
  id: string;
  text: string;
}

/** Builds chips for one exchange. Returns 3-5 chips. */
export function generateChips(exchange: QAForensicsExchange): Chip[] {
  const probes = exchange.suggested_probes;
  if (probes && probes.length > 0) {
    return probes.map((text, i) => ({ id: `probe-${i}`, text }));
  }
  return templatedFallback(exchange);
}

function templatedFallback(exchange: QAForensicsExchange): Chip[] {
  const analyst = exchange.analyst_name?.trim();
  const topic = exchange.question_topic?.trim();

  const chips: Chip[] = [];

  if (analyst && topic) {
    chips.push({
      id: "analyst-concern",
      text: `Why is ${analyst} worried about ${topic}?`,
    });
  } else if (topic) {
    chips.push({
      id: "topic-concern",
      text: `Why might an analyst be worried about ${topic}?`,
    });
  }

  chips.push({
    id: "why-ask",
    text: topic
      ? `Why might an analyst ask about ${topic}?`
      : "Why might an analyst ask this question?",
  });

  chips.push({
    id: "honest-answer",
    text: topic
      ? `What would a clearer answer about ${topic} have to acknowledge?`
      : "What would a clearer answer have to acknowledge?",
  });

  chips.push({
    id: "investor-signal",
    text: "What does this answer signal to investors?",
  });

  return chips;
}

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
  // Mirror the LLM probe style: CTA verb + hedged framing + distinct angles.
  // Each chip targets a different angle from the prompt's taxonomy so we
  // don't ship duplicates even in the fallback path.
  const analyst = exchange.analyst_name?.trim();
  const executive = exchange.executive_name?.trim();
  const topic = exchange.question_topic?.trim();
  const topicClause = topic ? `about ${topic}` : "in this exchange";

  const chips: Chip[] = [];

  // Angle #1 — executive's motivation
  if (executive) {
    chips.push({
      id: "exec-motivation",
      text: `Explore why ${executive} might have answered ${topicClause} the way they did.`,
    });
  } else {
    chips.push({
      id: "exec-motivation",
      text: `Explore why the executive might have answered ${topicClause} the way they did.`,
    });
  }

  // Angle #2 — counterfactual
  chips.push({
    id: "counterfactual",
    text: topic
      ? `Examine what a clearer answer about ${topic} would have had to acknowledge.`
      : "Examine what a clearer answer would have had to acknowledge.",
  });

  // Angle #3 — investor signal
  chips.push({
    id: "investor-signal",
    text: "Dig into what the form of this answer might be signaling to investors.",
  });

  // Angle #4 — analyst's underlying worry
  if (analyst && topic) {
    chips.push({
      id: "analyst-worry",
      text: `Unpack why ${analyst} might have been pressing on ${topic} right now.`,
    });
  } else if (topic) {
    chips.push({
      id: "analyst-worry",
      text: `Unpack why an analyst might have been pressing on ${topic} right now.`,
    });
  } else {
    chips.push({
      id: "analyst-worry",
      text: "Unpack what the analyst might have really been trying to surface.",
    });
  }

  return chips;
}

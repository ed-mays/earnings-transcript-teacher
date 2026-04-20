import type { ReactNode } from "react";

export interface TermDefinition {
  term: string;
  definition: string;
  explanation: string;
  category: "industry" | "financial";
}

export interface SpanItem {
  speaker: string;
  section: string;
  text: string;
  sequence_order: number;
}

function escapeRegex(source: string): string {
  return source.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function buildTermRegex(terms: readonly string[]): RegExp | null {
  if (terms.length === 0) return null;
  const sorted = [...terms].sort((a, b) => b.length - a.length);
  const alternation = sorted.map(escapeRegex).join("|");
  return new RegExp(`\\b(${alternation})\\b`, "gi");
}

export function normalizeForMatch(text: string): string {
  return text.toLowerCase().replace(/\s+/g, " ").trim();
}

export type TermNodeRenderer = (
  matchedTerm: string,
  definition: TermDefinition,
  key: string,
) => ReactNode;

export function highlightTerms(
  text: string,
  termRegex: RegExp | null,
  termMap: ReadonlyMap<string, TermDefinition>,
  renderTerm: TermNodeRenderer,
): ReactNode[] {
  if (!termRegex || termMap.size === 0 || text.length === 0) {
    return [text];
  }

  const nodes: ReactNode[] = [];
  let lastIndex = 0;
  let matchIndex = 0;

  const regex = new RegExp(termRegex.source, termRegex.flags);

  let match: RegExpExecArray | null;
  while ((match = regex.exec(text)) !== null) {
    const start = match.index;
    const end = start + match[0].length;

    if (start > lastIndex) {
      nodes.push(text.slice(lastIndex, start));
    }

    const definition = termMap.get(match[0].toLowerCase());
    if (definition) {
      nodes.push(renderTerm(match[0], definition, `term-${matchIndex}`));
    } else {
      nodes.push(match[0]);
    }

    lastIndex = end;
    matchIndex += 1;

    if (match[0].length === 0) {
      regex.lastIndex += 1;
    }
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes.length > 0 ? nodes : [text];
}

export function findEvasionSpanIndex(
  answerText: string,
  spans: readonly SpanItem[],
): number | null {
  const normalized = normalizeForMatch(answerText);
  if (normalized.length === 0) return null;
  const needle = normalized.slice(0, 80);

  for (let i = 0; i < spans.length; i += 1) {
    if (normalizeForMatch(spans[i].text).includes(needle)) {
      return i;
    }
  }
  return null;
}


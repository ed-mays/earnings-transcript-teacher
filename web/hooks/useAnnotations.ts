"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { buildTermRegex } from "@/lib/highlight";
import type {
  LearnAnnotationsResponse,
  TermDefinition,
} from "@/components/transcript/types";

export interface UseAnnotationsResult {
  annotations: LearnAnnotationsResponse | null;
  termMap: Map<string, TermDefinition>;
  termRegex: RegExp | null;
  loading: boolean;
  error: string | null;
}

// Common lowercase financial words that are ambiguous in prose — they appear
// constantly in sentences without referring to the financial concept.
// Everything else (acronyms like EBITDA/ARR, multi-word phrases, industry
// terms) passes through.
const AMBIGUOUS_SINGLE_WORDS = new Set([
  "call",
  "margin",
  "note",
  "yield",
  "cash",
  "debt",
  "equity",
  "bond",
  "share",
  "unit",
]);

function filterTerms(terms: readonly TermDefinition[]): TermDefinition[] {
  return terms.filter((t) => {
    if (t.category === "industry") return true;
    if (t.term.includes(" ")) return true;
    return !AMBIGUOUS_SINGLE_WORDS.has(t.term.toLowerCase());
  });
}

export function useAnnotations(ticker: string): UseAnnotationsResult {
  const [annotations, setAnnotations] = useState<LearnAnnotationsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    api
      .get<LearnAnnotationsResponse>(`/api/calls/${ticker}/learn-annotations`)
      .then((data) => {
        if (cancelled) return;
        setAnnotations(data);
        setLoading(false);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setAnnotations(null);
        setError(err instanceof Error ? err.message : "Failed to load annotations");
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [ticker]);

  const filteredTerms = useMemo(
    () => (annotations ? filterTerms(annotations.terms) : []),
    [annotations],
  );

  const termMap = useMemo(() => {
    const map = new Map<string, TermDefinition>();
    for (const term of filteredTerms) {
      map.set(term.term.toLowerCase(), term);
    }
    return map;
  }, [filteredTerms]);

  const termRegex = useMemo(
    () => buildTermRegex(filteredTerms.map((t) => t.term)),
    [filteredTerms],
  );

  return { annotations, termMap, termRegex, loading, error };
}

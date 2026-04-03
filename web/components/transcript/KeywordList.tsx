/** Renders a ranked list of keyword chips with glossary definitions on click. */

"use client";

import { useState, useRef } from "react";
import { Popover, PopoverTrigger, PopoverContent } from "@/components/ui/popover";
import { lookupTerm } from "@/lib/glossary";
import { streamDefine } from "@/lib/define";

interface KeywordListProps {
  keywords: string[];
  ticker?: string;
}

interface KeywordDefContentProps {
  term: string;
  ticker?: string;
}

function KeywordDefContent({ term, ticker }: KeywordDefContentProps) {
  const staticDef = lookupTerm(term);
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [definition, setDefinition] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  function handleDefine() {
    if (!ticker) return;
    const controller = new AbortController();
    abortRef.current = controller;
    setStatus("loading");
    setDefinition("");
    streamDefine(
      ticker,
      term,
      {
        onToken: (t) => setDefinition((prev) => prev + t),
        onDone: () => setStatus("done"),
        onError: () => setStatus("error"),
      },
      controller.signal
    );
  }

  if (staticDef) {
    return <p className="text-xs text-foreground leading-snug">{staticDef}</p>;
  }

  if (status === "idle") {
    return (
      <div>
        <p className="text-xs text-muted-foreground mb-2">Not in the static glossary.</p>
        {ticker && (
          <button
            onClick={handleDefine}
            className="text-xs text-foreground underline underline-offset-2 hover:no-underline"
          >
            Define with AI
          </button>
        )}
      </div>
    );
  }

  if (status === "loading" || status === "done") {
    return (
      <p className="text-xs text-foreground leading-snug">
        {definition || <span className="text-muted-foreground italic">Defining…</span>}
      </p>
    );
  }

  return <p className="text-xs text-destructive">Failed to fetch definition.</p>;
}

export function KeywordList({ keywords, ticker }: KeywordListProps) {
  if (keywords.length === 0) {
    return <p className="text-sm text-muted-foreground">No keywords extracted.</p>;
  }

  return (
    <div className="flex flex-wrap gap-2">
      {keywords.map((kw, i) => (
        <Popover key={i}>
          <PopoverTrigger className="inline-flex items-center rounded-full bg-secondary px-3 py-1 text-xs font-medium text-secondary-foreground transition-colors hover:bg-secondary/80 cursor-pointer">
            {kw}
          </PopoverTrigger>
          <PopoverContent className="w-64">
            <p className="text-xs font-semibold mb-1.5 text-foreground">{kw}</p>
            <KeywordDefContent term={kw} ticker={ticker} />
          </PopoverContent>
        </Popover>
      ))}
    </div>
  );
}

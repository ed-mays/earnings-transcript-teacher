"use client";

import { getSentimentStyle } from "@/lib/signal-colors";
import { cn } from "@/lib/utils";
import type { SynthesisInfo } from "@/components/transcript/types";

interface SentimentBarProps {
  synthesis: SynthesisInfo | null;
}

interface Badge {
  label: string;
  value: string | null;
}

/** Sticky sub-bar with overall / executive / analyst sentiment badges. */
export function SentimentBar({ synthesis }: SentimentBarProps) {
  if (!synthesis) return null;

  const badges: Badge[] = [
    { label: "Overall", value: synthesis.overall_sentiment },
    { label: "Executive", value: synthesis.executive_tone },
    { label: "Analyst", value: synthesis.analyst_sentiment },
  ];

  const visible = badges.filter((b): b is { label: string; value: string } => !!b.value);
  if (visible.length === 0) return null;

  return (
    <div className="sticky top-[56px] z-[9] flex flex-wrap gap-2 border-b bg-background/90 px-4 py-2 text-xs backdrop-blur">
      {visible.map(({ label, value }) => {
        const style = getSentimentStyle(value);
        return (
          <span
            key={label}
            className={cn(
              "inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium",
              style.bg,
              style.text,
            )}
          >
            <span className="text-muted-foreground">{label}:</span>
            <span>{value}</span>
          </span>
        );
      })}
    </div>
  );
}

"use client";

import { Badge } from "@/components/ui/badge";
import { getEvasionStyle, getSentimentStyle } from "@/lib/signal-colors";
import type { SignalStrip } from "@/components/transcript/types";

interface QASignalBadgesProps {
  signals: SignalStrip;
}

/** Call-level signal badges for the Q&A Forensics index header. Surfaces the
 *  same dimensions the Analyst Framework's MetadataPanel does (evasion level,
 *  executive tone, analyst sentiment, overall sentiment) so users see the
 *  whole-call context before drilling into individual exchanges. */
export function QASignalBadges({ signals }: QASignalBadgesProps) {
  const items: { label: string; value: string | null; style?: { bg: string; text: string } }[] = [];

  if (signals.evasion_level) {
    items.push({
      label: "Evasion Index",
      value: signals.evasion_level,
      style: getEvasionStyle(signals.evasion_level),
    });
  }
  if (signals.executive_sentiment) {
    items.push({
      label: "Executive tone",
      value: signals.executive_sentiment,
      style: getSentimentStyle(signals.executive_sentiment),
    });
  }
  if (signals.analyst_sentiment) {
    items.push({
      label: "Analyst sentiment",
      value: signals.analyst_sentiment,
      style: getSentimentStyle(signals.analyst_sentiment),
    });
  }
  if (signals.overall_sentiment) {
    items.push({
      label: "Overall sentiment",
      value: signals.overall_sentiment,
      style: getSentimentStyle(signals.overall_sentiment),
    });
  }

  if (items.length === 0) return null;

  return (
    <div
      aria-label="Call-level signals"
      className="mt-3 flex flex-wrap items-center gap-2"
    >
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-1.5">
          <span className="text-xs text-muted-foreground">{item.label}:</span>
          <Badge
            className={`rounded-md whitespace-normal h-auto w-auto shrink ${item.style?.bg ?? ""} ${item.style?.text ?? ""}`}
          >
            {item.value}
          </Badge>
        </div>
      ))}
    </div>
  );
}

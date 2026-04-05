"use client";

/** Pre-reading brief panel shown at the top of the call page. */

import { useState } from "react";
import type { CallBrief, TakeawayItem, MisconceptionItem, SignalStrip } from "./types";
import { MisconceptionCard } from "./MisconceptionCard";
import { Card, CardContent } from "@/components/ui/card";
import { getEvasionStyle, getSentimentStyle } from "@/lib/signal-colors";

interface CallBriefPanelProps {
  brief: CallBrief;
  takeaways: TakeawayItem[];
  misconceptions: MisconceptionItem[];
  signal_strip: SignalStrip | null;
}


interface SignalBadgeProps {
  label: string;
  value: string | null;
}

function SignalBadge({ label, value }: SignalBadgeProps) {
  if (!value) return null;
  const s = getSentimentStyle(value);
  return (
    <span className={`rounded-md px-2.5 py-1 text-xs font-medium ${s.bg} ${s.text}`}>
      {label}: {value}
    </span>
  );
}

interface EvasionBadgeProps {
  level: string | null;
}

function EvasionBadge({ level }: EvasionBadgeProps) {
  if (!level) return null;
  const s = getEvasionStyle(level);
  return (
    <span className={`rounded-md px-2.5 py-1 text-xs font-medium ${s.bg} ${s.text}`}>
      Evasion: {level}
    </span>
  );
}

export function CallBriefPanel({ brief, takeaways, misconceptions, signal_strip }: CallBriefPanelProps) {
  const [allExpanded, setAllExpanded] = useState(false);

  return (
    <Card className="mb-6 gap-0">
      <CardContent className="p-5 space-y-5">
        {/* Context line */}
        <p className="text-sm font-medium text-foreground/80 leading-relaxed italic">
          {brief.context_line}
        </p>

        {/* Bigger Picture bullets */}
        {brief.bigger_picture.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              Bigger Picture
            </p>
            <ul className="space-y-1">
              {brief.bigger_picture.map((bullet, i) => (
                <li key={i} className="text-sm text-foreground/80 flex gap-2">
                  <span className="text-muted-foreground/50 select-none">•</span>
                  {bullet}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Key takeaways */}
        {takeaways.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              Key Takeaways
            </p>
            <ol className="space-y-2 list-decimal list-inside">
              {takeaways.map((t, i) => (
                <li key={i} className="text-sm">
                  <span className="font-medium text-foreground">{t.takeaway}</span>
                  {t.why_it_matters && (
                    <span className="text-muted-foreground"> — {t.why_it_matters}</span>
                  )}
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Interpretation questions */}
        {brief.interpretation_questions.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
              Hold These in Mind
            </p>
            <ol className="space-y-1.5 list-decimal list-inside">
              {brief.interpretation_questions.map((q, i) => (
                <li key={i} className="text-sm text-foreground/80">{q}</li>
              ))}
            </ol>
          </div>
        )}

        {/* Signal strip */}
        {signal_strip && (
          <div className="flex flex-wrap gap-2 border-t pt-4">
            <SignalBadge label="Exec tone" value={signal_strip.executive_sentiment} />
            <SignalBadge label="Analyst mood" value={signal_strip.analyst_sentiment} />
            <EvasionBadge level={signal_strip.evasion_level} />
            {signal_strip.strategic_shift_flagged && (
              <span className="rounded-md px-2.5 py-1 text-xs font-medium bg-info/10 text-info-foreground">
                Strategic shift flagged
              </span>
            )}
          </div>
        )}

        {/* Misconception reveal-cards */}
        {misconceptions.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Common Misreadings
              </p>
              {misconceptions.length >= 2 && (
                <button
                  onClick={() => setAllExpanded((prev) => !prev)}
                  className="text-xs text-muted-foreground hover:text-foreground underline-offset-2 hover:underline"
                >
                  {allExpanded ? "Collapse all" : "Expand all"}
                </button>
              )}
            </div>
            <div className="space-y-2">
              {misconceptions.map((m, i) => (
                <MisconceptionCard key={i} item={m} forceExpanded={allExpanded} />
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

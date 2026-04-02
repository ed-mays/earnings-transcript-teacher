"use client";

import { useState } from "react";
import Link from "next/link";
import type { CallDetail } from "./types";
import { KeywordList } from "./KeywordList";
import { ThemeCard } from "./ThemeCard";
import { EvasionCard } from "./EvasionCard";
import { StrategicShiftCard } from "./StrategicShiftCard";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/EmptyState";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "@/components/ui/collapsible";

interface AnalystStepConfig {
  id: string;
  label: string;
  question: string;
  defaultExpanded: boolean;
}

const ANALYST_STEPS: AnalystStepConfig[] = [
  {
    id: "orient",
    label: "Orient",
    question: "What is this call about, and what was expected?",
    defaultExpanded: true,
  },
  {
    id: "read-the-room",
    label: "Read the Room",
    question: "How did management sound?",
    defaultExpanded: false,
  },
  {
    id: "understand-the-narrative",
    label: "Understand the Narrative",
    question: "What story did management tell?",
    defaultExpanded: false,
  },
  {
    id: "notice-what-was-avoided",
    label: "Notice What Was Avoided",
    question: "What wasn't said?",
    defaultExpanded: false,
  },
  {
    id: "track-what-changed",
    label: "Track What Changed",
    question: "What's different from last quarter?",
    defaultExpanded: false,
  },
  {
    id: "situate-in-context",
    label: "Situate in Context",
    question: "How does this fit the bigger picture?",
    defaultExpanded: false,
  },
];

interface MetadataPanelProps {
  call: CallDetail;
}

/** Sidebar panel with analyst step framework: 6 collapsible sections teaching a mental model. */
export function MetadataPanel({ call }: MetadataPanelProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>(
    Object.fromEntries(ANALYST_STEPS.map((s) => [s.id, s.defaultExpanded]))
  );

  return (
    <Card className="p-0 gap-0 overflow-hidden">
      <div className="px-4 py-3 border-b">
        <p className="text-sm font-semibold text-foreground">Analyst Framework</p>
        <p className="text-xs text-muted-foreground mt-0.5">Use these questions to guide your reading</p>
      </div>
      {ANALYST_STEPS.map((step, i) => (
        <Collapsible
          key={step.id}
          open={expanded[step.id]}
          onOpenChange={(open) => setExpanded((prev) => ({ ...prev, [step.id]: open }))}
          className={i > 0 ? "border-t" : ""}
        >
          {/* Step header */}
          <CollapsibleTrigger className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-muted transition-colors">
            <span className="mt-0.5 shrink-0 text-xs font-semibold text-muted-foreground tabular-nums w-4">
              {i + 1}
            </span>
            <div className="flex-1 min-w-0">
              <span className="text-sm font-semibold text-foreground">{step.label}</span>
              <p className="text-xs text-muted-foreground mt-0.5 leading-snug">{step.question}</p>
            </div>
            <span className="mt-0.5 shrink-0 text-muted-foreground text-xs">
              {expanded[step.id] ? "▲" : "▼"}
            </span>
          </CollapsibleTrigger>

          {/* Step body */}
          <CollapsibleContent className="px-4 pb-4 pt-1">
            <StepContent step={step} call={call} />
            <Link
              href={`/calls/${call.ticker}/learn?topic=${encodeURIComponent(step.question)}`}
              className="mt-4 block text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
            >
              Explore with Feynman →
            </Link>
          </CollapsibleContent>
        </Collapsible>
      ))}

      {/* Language layer — always visible */}
      {call.keywords.length > 0 && (
        <div className="border-t px-4 py-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Language &amp; Keywords
          </p>
          <KeywordList keywords={call.keywords} />
        </div>
      )}
    </Card>
  );
}

interface StepContentProps {
  step: AnalystStepConfig;
  call: CallDetail;
}

function StepContent({ step, call }: StepContentProps) {
  switch (step.id) {
    case "orient":
      return <OrientStep call={call} />;
    case "read-the-room":
      return <ReadTheRoomStep call={call} />;
    case "understand-the-narrative":
      return <UnderstandTheNarrativeStep call={call} />;
    case "notice-what-was-avoided":
      return <NoticeWhatWasAvoidedStep call={call} />;
    case "track-what-changed":
      return <TrackWhatChangedStep call={call} />;
    case "situate-in-context":
      return <SituateInContextStep />;
    default:
      return null;
  }
}

function OrientStep({ call }: { call: CallDetail }) {
  const sentiment = call.synthesis?.overall_sentiment;

  if (!sentiment) {
    return <EmptyState title="No orientation data available." />;
  }

  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        Overall sentiment
      </dt>
      <dd className="mt-1 text-sm text-foreground">{sentiment}</dd>
    </div>
  );
}

function ReadTheRoomStep({ call }: { call: CallDetail }) {
  const { synthesis, speakers } = call;
  const hasSentiment = synthesis?.executive_tone || synthesis?.analyst_sentiment;

  return (
    <div className="space-y-4">
      {hasSentiment && (
        <dl className="grid grid-cols-2 gap-3">
          {synthesis?.executive_tone && (
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Executive tone
              </dt>
              <dd className="mt-1 text-sm text-foreground">{synthesis.executive_tone}</dd>
            </div>
          )}
          {synthesis?.analyst_sentiment && (
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                Analyst sentiment
              </dt>
              <dd className="mt-1 text-sm text-foreground">{synthesis.analyst_sentiment}</dd>
            </div>
          )}
        </dl>
      )}

      {speakers.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Speakers
          </p>
          <ul className="space-y-1.5">
            {speakers.map((s, i) => (
              <li key={i} className="text-sm">
                <span className="font-medium text-foreground">{s.name}</span>
                {s.title && <span className="text-muted-foreground">, {s.title}</span>}
                {s.firm && <span className="text-muted-foreground/70"> · {s.firm}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {!hasSentiment && speakers.length === 0 && (
        <EmptyState title="No room dynamics data available." />
      )}
    </div>
  );
}

function UnderstandTheNarrativeStep({ call }: { call: CallDetail }) {
  const source = call.topics.length > 0 ? call.topics : call.themes.map((t) => [t]);

  if (source.length === 0) {
    return <EmptyState title="No themes extracted." />;
  }

  return (
    <div className="space-y-3">
      {source.map((terms, i) => (
        <ThemeCard key={i} label={terms[0] ?? `Topic ${i + 1}`} terms={terms} />
      ))}
    </div>
  );
}

/** Map evasion_level string to badge styling. */
function evasionLevelBadge(level: string): { emoji: string; classes: string } {
  if (level === "high") return { emoji: "🔴", classes: "text-red-700 bg-red-50" };
  if (level === "medium") return { emoji: "🟡", classes: "text-amber-700 bg-amber-50" };
  return { emoji: "🟢", classes: "text-green-700 bg-green-50" };
}

function NoticeWhatWasAvoidedStep({ call }: { call: CallDetail }) {
  if (call.evasion_analyses.length === 0) {
    return <EmptyState title="No evasion patterns detected." />;
  }

  const evasionLevel = call.signal_strip?.evasion_level ?? null;
  const qaItems = call.evasion_analyses.filter((item) => item.analyst_name !== null);
  const prepItems = call.evasion_analyses.filter((item) => item.analyst_name === null);

  return (
    <div className="space-y-4">
      {/* Overall evasion index */}
      {evasionLevel && (() => {
        const badge = evasionLevelBadge(evasionLevel);
        return (
          <div className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${badge.classes}`}>
            {badge.emoji} Evasion index: {evasionLevel}
          </div>
        );
      })()}

      {/* Q&A evasion */}
      {qaItems.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Q&amp;A evasion
          </p>
          <div className="space-y-2">
            {qaItems.map((item, i) => (
              <EvasionCard key={i} item={item} ticker={call.ticker} />
            ))}
          </div>
        </div>
      )}

      {/* Prepared remarks evasion */}
      {prepItems.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Prepared remarks
          </p>
          <div className="space-y-2">
            {prepItems.map((item, i) => (
              <EvasionCard key={i} item={item} ticker={call.ticker} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TrackWhatChangedStep({ call }: { call: CallDetail }) {
  if (call.strategic_shifts.length === 0) {
    return <EmptyState title="No strategic shifts identified." />;
  }

  return (
    <div className="space-y-3">
      {call.strategic_shifts.map((shift, i) => (
        <StrategicShiftCard key={i} shift={shift} />
      ))}
    </div>
  );
}

function SituateInContextStep() {
  return <EmptyState title="Context data coming soon." />;
}

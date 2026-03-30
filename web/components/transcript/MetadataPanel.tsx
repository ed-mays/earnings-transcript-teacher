"use client";

import { useState } from "react";
import Link from "next/link";
import type { CallDetail } from "./types";
import { KeywordList } from "./KeywordList";
import { ThemeCard } from "./ThemeCard";
import { EvasionCard } from "./EvasionCard";
import { StrategicShiftCard } from "./StrategicShiftCard";

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

  function toggle(id: string) {
    setExpanded((prev) => ({ ...prev, [id]: !prev[id] }));
  }

  return (
    <div className="flex flex-col rounded-xl border border-zinc-200 bg-zinc-50">
      {ANALYST_STEPS.map((step, i) => (
        <div key={step.id} className={i > 0 ? "border-t border-zinc-200" : ""}>
          {/* Step header */}
          <button
            onClick={() => toggle(step.id)}
            className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-zinc-100 transition-colors"
          >
            <span className="mt-0.5 shrink-0 text-xs font-semibold text-zinc-400 tabular-nums w-4">
              {i + 1}
            </span>
            <div className="flex-1 min-w-0">
              <span className="text-sm font-semibold text-zinc-900">{step.label}</span>
              <p className="text-xs text-zinc-500 mt-0.5 leading-snug">{step.question}</p>
            </div>
            <span className="mt-0.5 shrink-0 text-zinc-400 text-xs">
              {expanded[step.id] ? "▲" : "▼"}
            </span>
          </button>

          {/* Step body */}
          {expanded[step.id] && (
            <div className="px-4 pb-4 pt-1">
              <StepContent step={step} call={call} />
              <Link
                href={`/calls/${call.ticker}/learn?topic=${encodeURIComponent(step.question)}`}
                className="mt-4 block text-xs text-zinc-500 underline-offset-2 hover:text-zinc-700 hover:underline"
              >
                Explore with Feynman →
              </Link>
            </div>
          )}
        </div>
      ))}

      {/* Language layer — always visible */}
      {call.keywords.length > 0 && (
        <div className="border-t border-zinc-200 px-4 py-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-400">
            Language &amp; Keywords
          </p>
          <KeywordList keywords={call.keywords} />
        </div>
      )}
    </div>
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
    return <p className="text-sm text-zinc-400">No orientation data available.</p>;
  }

  return (
    <div>
      <dt className="text-xs font-semibold uppercase tracking-wide text-zinc-400">
        Overall sentiment
      </dt>
      <dd className="mt-1 text-sm text-zinc-700">{sentiment}</dd>
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
              <dt className="text-xs font-semibold uppercase tracking-wide text-zinc-400">
                Executive tone
              </dt>
              <dd className="mt-1 text-sm text-zinc-700">{synthesis.executive_tone}</dd>
            </div>
          )}
          {synthesis?.analyst_sentiment && (
            <div>
              <dt className="text-xs font-semibold uppercase tracking-wide text-zinc-400">
                Analyst sentiment
              </dt>
              <dd className="mt-1 text-sm text-zinc-700">{synthesis.analyst_sentiment}</dd>
            </div>
          )}
        </dl>
      )}

      {speakers.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-400">
            Speakers
          </p>
          <ul className="space-y-1.5">
            {speakers.map((s, i) => (
              <li key={i} className="text-sm">
                <span className="font-medium text-zinc-800">{s.name}</span>
                {s.title && <span className="text-zinc-500">, {s.title}</span>}
                {s.firm && <span className="text-zinc-400"> · {s.firm}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {!hasSentiment && speakers.length === 0 && (
        <p className="text-sm text-zinc-400">No room dynamics data available.</p>
      )}
    </div>
  );
}

function UnderstandTheNarrativeStep({ call }: { call: CallDetail }) {
  const source = call.topics.length > 0 ? call.topics : call.themes.map((t) => [t]);

  if (source.length === 0) {
    return <p className="text-sm text-zinc-400">No themes extracted.</p>;
  }

  return (
    <div className="space-y-3">
      {source.map((terms, i) => (
        <ThemeCard key={i} label={terms[0] ?? `Topic ${i + 1}`} terms={terms} />
      ))}
    </div>
  );
}

function NoticeWhatWasAvoidedStep({ call }: { call: CallDetail }) {
  if (call.evasion_analyses.length === 0) {
    return <p className="text-sm text-zinc-400">No evasion patterns detected.</p>;
  }

  return (
    <div className="space-y-3">
      {call.evasion_analyses.map((item, i) => (
        <EvasionCard key={i} item={item} />
      ))}
    </div>
  );
}

function TrackWhatChangedStep({ call }: { call: CallDetail }) {
  if (call.strategic_shifts.length === 0) {
    return <p className="text-sm text-zinc-400">No strategic shifts identified.</p>;
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
  return <p className="text-sm text-zinc-400">Context data coming soon.</p>;
}

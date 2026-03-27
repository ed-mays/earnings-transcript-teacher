"use client";

import { useState } from "react";
import type { CallDetail } from "./types";
import { KeywordList } from "./KeywordList";
import { ThemeCard } from "./ThemeCard";
import { EvasionCard } from "./EvasionCard";
import { StrategicShiftCard } from "./StrategicShiftCard";

type Tab = "summary" | "keywords" | "themes" | "evasion" | "shifts";

const TABS: { id: Tab; label: string }[] = [
  { id: "summary", label: "Summary" },
  { id: "keywords", label: "Keywords" },
  { id: "themes", label: "Themes" },
  { id: "evasion", label: "Evasion" },
  { id: "shifts", label: "Shifts" },
];

interface MetadataPanelProps {
  call: CallDetail;
}

/** Sidebar panel with tabbed metadata: summary, keywords, themes, evasion, strategic shifts. */
export function MetadataPanel({ call }: MetadataPanelProps) {
  const [activeTab, setActiveTab] = useState<Tab>("summary");

  return (
    <div className="flex flex-col rounded-xl border border-zinc-200 bg-zinc-50">
      {/* Tab bar */}
      <div className="flex border-b border-zinc-200 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`shrink-0 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "border-b-2 border-zinc-900 text-zinc-900"
                : "text-zinc-500 hover:text-zinc-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === "summary" && <SummaryTab call={call} />}
        {activeTab === "keywords" && <KeywordList keywords={call.keywords} />}
        {activeTab === "themes" && <ThemesTab topics={call.topics} themes={call.themes} />}
        {activeTab === "evasion" && <EvasionTab items={call.evasion_analyses} />}
        {activeTab === "shifts" && <ShiftsTab shifts={call.strategic_shifts} />}
      </div>
    </div>
  );
}

function SummaryTab({ call }: { call: CallDetail }) {
  const { synthesis } = call;

  if (!synthesis) {
    return <p className="text-sm text-zinc-400">No summary available.</p>;
  }

  const rows = [
    { label: "Overall sentiment", value: synthesis.overall_sentiment },
    { label: "Executive tone", value: synthesis.executive_tone },
    { label: "Analyst sentiment", value: synthesis.analyst_sentiment },
  ];

  return (
    <dl className="space-y-4">
      {rows.map(({ label, value }) =>
        value ? (
          <div key={label}>
            <dt className="text-xs font-semibold uppercase tracking-wide text-zinc-400">
              {label}
            </dt>
            <dd className="mt-1 text-sm text-zinc-700">{value}</dd>
          </div>
        ) : null
      )}
    </dl>
  );
}

function ThemesTab({ topics, themes }: { topics: string[][]; themes: string[] }) {
  // topics is a list of term lists; themes is the same flat but labelled differently
  // Use topics if available (richer), fall back to themes
  const source = topics.length > 0 ? topics : themes.map((t) => [t]);

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

function EvasionTab({ items }: { items: CallDetail["evasion_analyses"] }) {
  if (items.length === 0) {
    return <p className="text-sm text-zinc-400">No evasion patterns detected.</p>;
  }

  return (
    <div className="space-y-3">
      {items.map((item, i) => (
        <EvasionCard key={i} item={item} />
      ))}
    </div>
  );
}

function ShiftsTab({ shifts }: { shifts: CallDetail["strategic_shifts"] }) {
  if (shifts.length === 0) {
    return <p className="text-sm text-zinc-400">No strategic shifts identified.</p>;
  }

  return (
    <div className="space-y-3">
      {shifts.map((shift, i) => (
        <StrategicShiftCard key={i} shift={shift} />
      ))}
    </div>
  );
}

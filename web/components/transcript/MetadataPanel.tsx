"use client";

import { useState, Fragment, useEffect } from "react";
import Link from "next/link";
import { Loader2 } from "lucide-react";
import type {
  CallDetail,
  TopicsResponse,
  EvasionResponse,
  StrategicShiftsResponse,
  CompetitorsResponse,
  NewsResponse,
} from "./types";
import { KeywordList } from "./KeywordList";
import { ThemeCard } from "./ThemeCard";
import { EvasionCard } from "./EvasionCard";
import { StrategicShiftCard } from "./StrategicShiftCard";
import { NewsCard } from "./NewsCard";
import { CompetitorList } from "./CompetitorList";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/EmptyState";
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
  CollapsibleChevron,
} from "@/components/ui/collapsible";
import { getEvasionStyle } from "@/lib/signal-colors";
import { api } from "@/lib/api";
import { useLazySection } from "@/hooks/useLazySection";

interface AnalystStepConfig {
  id: string;
  label: string;
  question: string;
}

const ANALYST_STEPS: AnalystStepConfig[] = [
  {
    id: "orient",
    label: "Orient",
    question: "What is this call about, and what was expected?",
  },
  {
    id: "read-the-room",
    label: "Read the Room",
    question: "How did management sound?",
  },
  {
    id: "understand-the-narrative",
    label: "Understand the Narrative",
    question: "What story did management tell?",
  },
  {
    id: "notice-what-was-avoided",
    label: "Notice What Was Avoided",
    question: "What wasn't said?",
  },
  {
    id: "track-what-changed",
    label: "Track What Changed",
    question: "What's different from last quarter?",
  },
  {
    id: "situate-in-context",
    label: "Situate in Context",
    question: "How does this fit the bigger picture?",
  },
];

interface MetadataPanelProps {
  call: CallDetail;
}

/** Sidebar panel with analyst step framework: 6 collapsible sections teaching a mental model. */
export function MetadataPanel({ call }: MetadataPanelProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>(
    Object.fromEntries(
      [...ANALYST_STEPS.map((s) => [s.id, false]), ["participants", false], ["keywords", false]]
    )
  );

  function handleOpenChange(id: string, open: boolean) {
    setExpanded((prev) => ({ ...prev, [id]: open }));
    api
      .post<{ ok: boolean }>(`/api/calls/${call.ticker}/track`, { section: id, open })
      .catch(() => {});
  }

  return (
    <Card className="p-0 gap-0 overflow-hidden">
      <div className="px-4 py-3 border-b">
        <p className="text-sm font-semibold text-foreground">Analyst Framework</p>
        <p className="text-xs text-muted-foreground mt-0.5">Use these questions to guide your reading</p>
      </div>
      {ANALYST_STEPS.map((step, i) => (
        <Fragment key={step.id}>
          <Collapsible
            open={expanded[step.id]}
            onOpenChange={(open) => handleOpenChange(step.id, open)}
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
              <CollapsibleChevron open={expanded[step.id]} className="mt-0.5" />
            </CollapsibleTrigger>

            {/* Step body */}
            <CollapsibleContent className="px-4 pb-4 pt-1">
              <StepContent step={step} call={call} isOpen={expanded[step.id]} />
              <Link
                href={`/calls/${call.ticker}/learn?topic=${encodeURIComponent(step.question)}`}
                className="mt-4 block text-xs text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
              >
                Explore with Feynman →
              </Link>
            </CollapsibleContent>
          </Collapsible>

          {step.id === "orient" && call.speakers.length > 0 && (
            <Collapsible
              open={expanded.participants}
              onOpenChange={(open) => handleOpenChange("participants", open)}
              className="border-t"
            >
              <CollapsibleTrigger className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-muted transition-colors">
                <div className="flex-1 min-w-0">
                  <span className="text-sm font-semibold text-foreground">Participants</span>
                  <p className="text-xs text-muted-foreground mt-0.5 leading-snug">Who was on the call?</p>
                </div>
                <CollapsibleChevron open={expanded.participants} className="mt-0.5" />
              </CollapsibleTrigger>
              <CollapsibleContent className="px-4 pb-4 pt-1">
                <ul className="space-y-1.5">
                  {call.speakers.map((s, idx) => (
                    <li key={idx} className="text-sm">
                      <span className="font-medium text-foreground">{s.name}</span>
                      {s.title && <span className="text-muted-foreground">, {s.title}</span>}
                      {s.firm && <span className="text-muted-foreground/70"> · {s.firm}</span>}
                    </li>
                  ))}
                </ul>
              </CollapsibleContent>
            </Collapsible>
          )}
        </Fragment>
      ))}

      {call.keywords.length > 0 && (
        <Collapsible
          open={expanded.keywords}
          onOpenChange={(open) => handleOpenChange("keywords", open)}
          className="border-t"
        >
          <CollapsibleTrigger className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-muted transition-colors">
            <div className="flex-1 min-w-0">
              <span className="text-sm font-semibold text-foreground">Language &amp; Keywords</span>
              <p className="text-xs text-muted-foreground mt-0.5 leading-snug">Key terms used in this call</p>
            </div>
            <CollapsibleChevron open={expanded.keywords} className="mt-0.5" />
          </CollapsibleTrigger>
          <CollapsibleContent className="px-4 pb-4 pt-1">
            <KeywordList keywords={call.keywords} ticker={call.ticker} />
          </CollapsibleContent>
        </Collapsible>
      )}
    </Card>
  );
}

interface StepContentProps {
  step: AnalystStepConfig;
  call: CallDetail;
  isOpen: boolean;
}

function StepContent({ step, call, isOpen }: StepContentProps) {
  switch (step.id) {
    case "orient":
      return <OrientStep call={call} />;
    case "read-the-room":
      return <ReadTheRoomStep call={call} />;
    case "understand-the-narrative":
      return <UnderstandTheNarrativeStep ticker={call.ticker} isOpen={isOpen} />;
    case "notice-what-was-avoided":
      return <NoticeWhatWasAvoidedStep ticker={call.ticker} isOpen={isOpen} signal_strip={call.signal_strip} />;
    case "track-what-changed":
      return <TrackWhatChangedStep ticker={call.ticker} isOpen={isOpen} />;
    case "situate-in-context":
      return <SituateInContextStep ticker={call.ticker} isOpen={isOpen} />;
    default:
      return null;
  }
}

function SectionLoading() {
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground py-1">
      <Loader2 className="h-3 w-3 animate-spin" />
      Loading…
    </div>
  );
}

function SectionError({ message }: { message: string }) {
  return <EmptyState title={`Failed to load: ${message}`} />;
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
  const { synthesis } = call;
  const hasSentiment = synthesis?.executive_tone || synthesis?.analyst_sentiment;

  return (
    <div className="space-y-4">
      {hasSentiment && (
        <dl className="space-y-3">
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

      {!hasSentiment && (
        <EmptyState title="No room dynamics data available." />
      )}
    </div>
  );
}

function UnderstandTheNarrativeStep({ ticker, isOpen }: { ticker: string; isOpen: boolean }) {
  const { data, loading, error, trigger } = useLazySection<TopicsResponse>(() =>
    api.get(`/api/calls/${ticker}/topics`)
  );

  useEffect(() => {
    if (isOpen) trigger();
  }, [isOpen, trigger]);

  if (loading) return <SectionLoading />;
  if (error) return <SectionError message={error} />;
  if (!data) return null;

  const { topics, themes } = data;

  if (topics.length === 0 && themes.length === 0) {
    return <EmptyState title="No themes extracted." />;
  }

  if (topics.length > 0) {
    return (
      <div className="space-y-3">
        {topics.map((topic, i) => (
          <ThemeCard key={i} label={topic.label || `Topic ${i + 1}`} summary={topic.summary} />
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {themes.map((theme, i) => (
        <ThemeCard key={i} label={theme} summary="" />
      ))}
    </div>
  );
}

function NoticeWhatWasAvoidedStep({
  ticker,
  isOpen,
  signal_strip,
}: {
  ticker: string;
  isOpen: boolean;
  signal_strip: CallDetail["signal_strip"];
}) {
  const { data, loading, error, trigger } = useLazySection<EvasionResponse>(() =>
    api.get(`/api/calls/${ticker}/evasion`)
  );

  useEffect(() => {
    if (isOpen) trigger();
  }, [isOpen, trigger]);

  if (loading) return <SectionLoading />;
  if (error) return <SectionError message={error} />;
  if (!data) return null;

  const { evasion_analyses } = data;

  if (evasion_analyses.length === 0) {
    return <EmptyState title="No evasion patterns detected." />;
  }

  // Use evasion_level from the loaded data; fall back to signal_strip if data not yet enriched
  const evasionLevel = data.evasion_level ?? signal_strip?.evasion_level ?? null;
  const qaItems = evasion_analyses.filter((item) => item.analyst_name !== null);
  const prepItems = evasion_analyses.filter((item) => item.analyst_name === null);

  return (
    <div className="space-y-4">
      {/* Overall evasion index */}
      {evasionLevel && (() => {
        const style = getEvasionStyle(evasionLevel);
        return (
          <div className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ${style.bg} ${style.text}`}>
            {style.emoji} Evasion index: {evasionLevel}
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
              <EvasionCard key={i} item={item} ticker={ticker} />
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
              <EvasionCard key={i} item={item} ticker={ticker} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TrackWhatChangedStep({ ticker, isOpen }: { ticker: string; isOpen: boolean }) {
  const { data, loading, error, trigger } = useLazySection<StrategicShiftsResponse>(() =>
    api.get(`/api/calls/${ticker}/strategic-shifts`)
  );

  useEffect(() => {
    if (isOpen) trigger();
  }, [isOpen, trigger]);

  if (loading) return <SectionLoading />;
  if (error) return <SectionError message={error} />;
  if (!data) return null;

  if (data.strategic_shifts.length === 0) {
    return <EmptyState title="No strategic shifts identified." />;
  }

  return (
    <div className="space-y-3">
      {data.strategic_shifts.map((shift, i) => (
        <StrategicShiftCard key={i} shift={shift} />
      ))}
    </div>
  );
}

function SituateInContextStep({ ticker, isOpen }: { ticker: string; isOpen: boolean }) {
  const news = useLazySection<NewsResponse>(() =>
    api.get(`/api/calls/${ticker}/news`)
  );
  const competitors = useLazySection<CompetitorsResponse>(() =>
    api.get(`/api/calls/${ticker}/competitors`)
  );

  useEffect(() => {
    if (isOpen) {
      news.trigger();
      competitors.trigger();
    }
  }, [isOpen, news.trigger, competitors.trigger]);

  const newsItems = news.data?.news_items ?? [];
  const competitorList = competitors.data?.competitors ?? [];

  return (
    <div className="space-y-5">
      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
          Recent News
        </h3>
        {news.loading ? (
          <SectionLoading />
        ) : news.error ? (
          <SectionError message={news.error} />
        ) : news.data ? (
          newsItems.length > 0 ? (
            <div className="space-y-2">
              {newsItems.map((item) => (
                <NewsCard key={item.headline} item={item} ticker={ticker} />
              ))}
            </div>
          ) : (
            <EmptyState title="No recent news found." />
          )
        ) : null}
      </section>

      <section>
        <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">
          Competitors
        </h3>
        {competitors.loading ? (
          <SectionLoading />
        ) : competitors.error ? (
          <SectionError message={competitors.error} />
        ) : competitors.data ? (
          competitorList.length > 0 ? (
            <CompetitorList competitors={competitorList} />
          ) : (
            <EmptyState title="No competitor data found." />
          )
        ) : null}
      </section>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { MessageCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { api } from "@/lib/api";
import { useFlag } from "@/lib/useFlag";
import { findEvasionSpanIndex } from "@/lib/highlight";
import { useAnnotations } from "@/hooks/useAnnotations";
import { AnnotatedSpanBlock } from "@/components/learn/AnnotatedSpanBlock";
import { ChatPanel } from "@/components/learn/ChatPanel";
import { EvasionCard } from "@/components/learn/EvasionCard";
import { LayerToggle } from "@/components/learn/LayerToggle";
import { SectionCheckpoint } from "@/components/learn/SectionCheckpoint";
import { SentimentBar } from "@/components/learn/SentimentBar";
import { CallBriefPanel } from "@/components/transcript/CallBriefPanel";
import { MetadataPanel } from "@/components/transcript/MetadataPanel";
import {
  DEFAULT_LAYERS,
  type AnnotationLayer,
  type AnnotationLayers,
  type ChatContext,
} from "@/components/learn/types";
import type {
  CallDetail,
  QAEvasionItem,
  SpansResponse,
} from "@/components/transcript/types";

const PAGE_SIZE = 50;

interface AdjacentCallInfo {
  ticker: string;
  fiscal_quarter?: string | null;
  company_name?: string | null;
  call_date?: string | null;
}

interface AdjacentCalls {
  prev: AdjacentCallInfo | null;
  next: AdjacentCallInfo | null;
}

interface GuidedAnalysisViewProps {
  call: CallDetail;
  adjacent: AdjacentCalls;
  initialTopic?: string;
}

/** Guided analysis experience: annotated transcript + analyst-framework aside + Feynman chat. */
export function GuidedAnalysisView({ call, adjacent, initialTopic }: GuidedAnalysisViewProps) {
  const ticker = call.ticker;
  const upperTicker = ticker.toUpperCase();
  const chatEnabled = useFlag("chat_enabled", true);

  const [layers, setLayers] = useState<AnnotationLayers>(DEFAULT_LAYERS);
  const [chatContext, setChatContext] = useState<ChatContext | null>(
    initialTopic ? { type: "term", text: initialTopic } : null,
  );
  const [chatOpen, setChatOpen] = useState<boolean>(Boolean(initialTopic));
  const [frameworkOpen, setFrameworkOpen] = useState<boolean>(false);

  const [spans, setSpans] = useState<SpansResponse | null>(null);
  const [page, setPage] = useState<number>(1);
  const [spansError, setSpansError] = useState<string | null>(null);

  const {
    annotations,
    termMap,
    termRegex,
    loading: annotationsLoading,
    error: annotationsError,
  } = useAnnotations(ticker);

  useEffect(() => {
    setSpansError(null);
    api
      .get<SpansResponse>(
        `/api/calls/${ticker}/spans?section=all&page=${page}&page_size=${PAGE_SIZE}`,
      )
      .then(setSpans)
      .catch((err: unknown) => {
        setSpans(null);
        setSpansError(err instanceof Error ? err.message : "Failed to load transcript");
      });
  }, [ticker, page]);

  const evasionBySpanIndex = useMemo(() => {
    const map = new Map<number, QAEvasionItem>();
    if (!annotations || !spans) return map;
    for (const item of annotations.evasion) {
      if (!item.answer_text) continue;
      const idx = findEvasionSpanIndex(item.answer_text, spans.spans);
      if (idx !== null && !map.has(idx)) {
        map.set(idx, item);
      }
    }
    return map;
  }, [annotations, spans]);

  const preparedToQaBoundary = useMemo(() => {
    if (!spans) return -1;
    for (let i = 0; i < spans.spans.length; i += 1) {
      if (spans.spans[i].section === "qa") return i;
    }
    return -1;
  }, [spans]);

  const toggleLayer = useCallback((layer: AnnotationLayer) => {
    setLayers((prev) => ({ ...prev, [layer]: !prev[layer] }));
  }, []);

  const handleChatClick = useCallback((context: ChatContext) => {
    setChatContext(context);
    setChatOpen(true);
  }, []);

  const handleOpenChat = useCallback(() => {
    setChatContext(null);
    setChatOpen(true);
  }, []);

  const handleCloseChat = useCallback(() => {
    setChatOpen(false);
  }, []);

  const handleExploreWithFeynman = useCallback(
    (topic: string) => {
      setChatContext({ type: "term", text: topic });
      setChatOpen(true);
      setFrameworkOpen(false);
    },
    [],
  );

  const totalPages = spans ? Math.max(1, Math.ceil(spans.total / spans.page_size)) : 1;

  return (
    <div className="flex h-[calc(100dvh-var(--nav-height))] w-full overflow-hidden">
      <section
        className={
          chatOpen
            ? "hidden min-w-0 flex-1 lg:flex lg:flex-col"
            : "flex min-w-0 flex-1 flex-col"
        }
        aria-label="Guided transcript analysis"
      >
        {/* Header */}
        <header className="flex shrink-0 flex-wrap items-center justify-between gap-3 border-b px-4 py-3">
          <div>
            <h1 className="text-xl font-semibold text-foreground">
              <span className="uppercase">{upperTicker}</span>
              <span className="text-muted-foreground"> · Guided Analysis</span>
            </h1>
            <div className="mt-0.5 flex items-center gap-3 text-xs text-muted-foreground">
              {call.company_name ? <span>{call.company_name}</span> : null}
              {call.call_date ? <span>{call.call_date}</span> : null}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {adjacent.prev ? (
              <Link
                href={`/calls/${adjacent.prev.ticker}`}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                ← {adjacent.prev.ticker}
              </Link>
            ) : null}
            {adjacent.next ? (
              <Link
                href={`/calls/${adjacent.next.ticker}`}
                className="text-xs text-muted-foreground hover:text-foreground"
              >
                {adjacent.next.ticker} →
              </Link>
            ) : null}
            <Button
              variant="outline"
              size="sm"
              onClick={() => setFrameworkOpen(true)}
            >
              Framework
            </Button>
            {chatEnabled ? (
              <Button variant="outline" size="sm" onClick={handleOpenChat}>
                <MessageCircle className="mr-1 h-4 w-4" aria-hidden />
                Explore with Feynman
              </Button>
            ) : null}
          </div>
        </header>

        {/* Layer toggle + sentiment bar */}
        <LayerToggle layers={layers} onChange={toggleLayer} />
        {layers.sentiment ? (
          <SentimentBar synthesis={annotations?.synthesis ?? null} />
        ) : null}

        {/* Scrollable content area */}
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-3xl px-4 py-6">
            {/* Brief */}
            {call.brief ? (
              <CallBriefPanel
                brief={call.brief}
                takeaways={call.takeaways}
                misconceptions={call.misconceptions}
                signal_strip={call.signal_strip ?? null}
              />
            ) : null}

            {/* Errors */}
            {spansError ? (
              <div
                role="alert"
                className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive"
              >
                {spansError}
              </div>
            ) : null}
            {annotationsError ? (
              <div
                role="alert"
                className="mb-4 rounded-lg border border-warning/30 bg-warning/10 px-4 py-3 text-sm text-warning-foreground"
              >
                Some annotations could not load. The transcript is still readable.
              </div>
            ) : null}

            {/* Transcript */}
            {spans ? (
              <div className="divide-y rounded-lg border bg-background">
                {spans.spans.map((span, index) => {
                  const elements: React.ReactNode[] = [];

                  if (
                    layers.guidance &&
                    index === preparedToQaBoundary &&
                    call.misconceptions?.length
                  ) {
                    elements.push(
                      <SectionCheckpoint
                        key={`checkpoint-${span.sequence_order}`}
                        misconceptions={call.misconceptions}
                      />,
                    );
                  }

                  elements.push(
                    <AnnotatedSpanBlock
                      key={`span-${span.sequence_order}`}
                      span={span}
                      layers={layers}
                      termRegex={layers.terms ? termRegex : null}
                      termMap={termMap}
                      evasionContext={
                        layers.evasion && evasionBySpanIndex.has(index)
                          ? {
                              type: "evasion",
                              text: span.text,
                              metadata:
                                evasionBySpanIndex.get(index)?.analyst_concern,
                            }
                          : undefined
                      }
                      onChatClick={handleChatClick}
                    />,
                  );

                  if (layers.evasion && evasionBySpanIndex.has(index)) {
                    elements.push(
                      <EvasionCard
                        key={`evasion-${span.sequence_order}`}
                        item={evasionBySpanIndex.get(index)!}
                        onChatClick={handleChatClick}
                      />,
                    );
                  }

                  return <div key={span.sequence_order}>{elements}</div>;
                })}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                {annotationsLoading ? "Loading transcript…" : "No transcript spans found."}
              </p>
            )}

            {/* Pagination */}
            {spans && totalPages > 1 ? (
              <nav
                aria-label="Transcript pagination"
                className="mt-6 flex items-center justify-between gap-3"
              >
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  Previous
                </Button>
                <span className="text-xs text-muted-foreground">
                  Page {page} of {totalPages}
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= totalPages}
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                >
                  Next
                </Button>
              </nav>
            ) : null}
          </div>
        </div>
      </section>

      {chatEnabled && chatOpen ? (
        <div className="fixed inset-0 z-40 flex lg:static lg:z-auto lg:inset-auto">
          <button
            type="button"
            aria-label="Close chat overlay"
            onClick={handleCloseChat}
            className="flex-1 bg-black/30 lg:hidden"
          />
          <div className="h-full w-full bg-background lg:w-[400px] lg:border-l">
            <ChatPanel ticker={ticker} context={chatContext} onClose={handleCloseChat} />
          </div>
        </div>
      ) : null}

      {/* Analyst Framework aside */}
      <Sheet open={frameworkOpen} onOpenChange={setFrameworkOpen}>
        <SheetContent
          side="right"
          className="flex w-full flex-col gap-0 overflow-y-auto p-0 sm:max-w-md"
        >
          <div className="px-4 pt-4 pb-2">
            <p className="text-base font-semibold">Analyst Framework</p>
            <p className="text-xs text-muted-foreground">
              Six questions to guide your reading. Click Explore with Feynman in any step to
              discuss it in chat.
            </p>
          </div>
          <div className="flex-1 px-4 pb-6">
            <MetadataPanel call={call} onExploreTopic={handleExploreWithFeynman} />
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}

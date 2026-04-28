"use client";

import { useCallback, useMemo, useState } from "react";
import { ChatPanel } from "@/components/learn/ChatPanel";
import { useFlag } from "@/lib/useFlag";
import type { ChatContext } from "@/components/learn/types";
import type {
  QAForensicsExchange,
  QAForensicsResponse,
} from "@/components/transcript/types";
import { QAForensicsIndex } from "./QAForensicsIndex";
import { QAExchangeDetail } from "./QAExchangeDetail";
import { evasionTypeLabel } from "./types";

interface QAForensicsClientProps {
  ticker: string;
  data: QAForensicsResponse;
}

type View =
  | { type: "index" }
  | { type: "detail"; exchangeId: string };

/** Stateful shell for Q&A Forensics. Two views (index ↔ detail), client-state
 *  only — view changes don't update the URL. From the detail view, picking a
 *  chip OR submitting freetext opens the Feynman ChatPanel and auto-sends the
 *  composed seed message as the first user turn. */
export function QAForensicsClient({ ticker, data }: QAForensicsClientProps) {
  const chatEnabled = useFlag("chat_enabled", true);

  const [view, setView] = useState<View>({ type: "index" });
  const [discussedSet, setDiscussedSet] = useState<Set<string>>(new Set());
  const [chatContext, setChatContext] = useState<ChatContext | null>(null);
  const [chatLearningContext, setChatLearningContext] = useState<string | undefined>(
    undefined,
  );
  const [chatOpen, setChatOpen] = useState(false);
  const [chatSessionId, setChatSessionId] = useState(0);

  const exchangeById = useMemo(() => {
    const map = new Map<string, QAForensicsExchange>();
    for (const e of data.exchanges) map.set(e.id, e);
    return map;
  }, [data.exchanges]);

  const currentExchange =
    view.type === "detail" ? exchangeById.get(view.exchangeId) ?? null : null;

  const handleSelectExchange = useCallback((id: string) => {
    setView({ type: "detail", exchangeId: id });
    setChatOpen(false);
    setChatContext(null);
    setChatLearningContext(undefined);
  }, []);

  const handleBackToIndex = useCallback(() => {
    setView({ type: "index" });
    setChatOpen(false);
    setChatContext(null);
    setChatLearningContext(undefined);
  }, []);

  const handleStartChat = useCallback(
    (firstMessage: string) => {
      if (!currentExchange) return;
      // The user's actual chat message is just their question/chip text.
      // The Q+A+system-flag context goes to the backend as learning_context,
      // which gets injected into the system prompt — invisible to the chat
      // thread but available to the tutor.
      setChatContext({ type: "qa-forensics", text: firstMessage });
      setChatLearningContext(buildLearningContext(currentExchange));
      setChatOpen(true);
      setChatSessionId((n) => n + 1);
      setDiscussedSet((prev) => {
        if (prev.has(currentExchange.id)) return prev;
        const next = new Set(prev);
        next.add(currentExchange.id);
        return next;
      });
    },
    [currentExchange],
  );

  const handleCloseChat = useCallback(() => {
    setChatOpen(false);
    setChatContext(null);
    setChatLearningContext(undefined);
  }, []);

  const mainContent =
    view.type === "index" || !currentExchange ? (
      <QAForensicsIndex
        ticker={ticker}
        exchanges={data.exchanges}
        dominantEvasionType={data.dominant_evasion_type}
        discussedSet={discussedSet}
        onSelectExchange={handleSelectExchange}
      />
    ) : (
      <QAExchangeDetail
        exchange={currentExchange}
        onBack={handleBackToIndex}
        onStartChat={handleStartChat}
      />
    );

  return (
    <div className="flex h-full w-full overflow-hidden">
      <section
        className={
          chatOpen
            ? "hidden min-w-0 flex-1 lg:flex lg:flex-col"
            : "flex min-w-0 flex-1 flex-col"
        }
        aria-label="Q&A Forensics"
      >
        <div className="flex-1 overflow-y-auto">{mainContent}</div>
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
            <ChatPanel
              key={`${currentExchange?.id ?? "no-exchange"}-${chatSessionId}`}
              ticker={ticker}
              context={chatContext}
              onClose={handleCloseChat}
              autoSend
              learningContext={chatLearningContext}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}

function buildLearningContext(exchange: QAForensicsExchange): string {
  // Pre-formatted background paragraph for the tutor's system prompt. The
  // student doesn't see this — their chat message is just their question.
  // Frame as third-person ("the student is studying...") so the tutor knows
  // its job is to discuss this specific exchange with the learner.
  const analyst = exchange.analyst_name ?? "an analyst";
  const topic = exchange.question_topic ?? "an unspecified topic";
  const executive = exchange.executive_name ?? "the executive";
  const typeLabel = exchange.evasion_type
    ? evasionTypeLabel(exchange.evasion_type)
    : "uncategorized";

  const lines = [
    `The student is studying a specific Q&A exchange from this earnings call.`,
    `Anchor your response to this exchange — analogies and follow-up questions should reference it directly.`,
    "",
    `Topic: ${topic}`,
    `Analyst: ${analyst}`,
    `Analyst's underlying concern: ${exchange.analyst_concern}`,
    "",
    `Question (verbatim):`,
    exchange.question_text ?? "(question text not available)",
    "",
    `${executive}'s response (verbatim):`,
    exchange.answer_text ?? "(answer text not available)",
    "",
    `System assessment of the response: ${typeLabel} pattern, defensiveness ${exchange.defensiveness_score}/10. ${exchange.evasion_explanation}`,
  ];
  return lines.join("\n");
}

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
  }, []);

  const handleBackToIndex = useCallback(() => {
    setView({ type: "index" });
    setChatOpen(false);
    setChatContext(null);
  }, []);

  const handleStartChat = useCallback(
    (firstMessage: string) => {
      if (!currentExchange) return;
      setChatContext({
        type: "qa-forensics",
        text: buildSeedMessage(currentExchange, firstMessage),
      });
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
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}

function buildSeedMessage(
  exchange: QAForensicsExchange,
  userQuestion: string,
): string {
  const topic = exchange.question_topic ? ` about ${exchange.question_topic}` : "";
  const typeLabel = exchange.evasion_type
    ? evasionTypeLabel(exchange.evasion_type)
    : "uncategorized";

  const lines = [
    `I just read this Q&A exchange${topic}:`,
    "",
    `Q: ${exchange.question_text ?? "(question text not available)"}`,
    "",
    `A: ${exchange.answer_text ?? "(answer text not available)"}`,
    "",
    `The system flagged this as: ${typeLabel} (defensiveness ${exchange.defensiveness_score}/10).`,
    "",
    `My question: ${userQuestion}`,
  ];
  return lines.join("\n");
}

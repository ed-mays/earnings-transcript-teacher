"use client";

import { useCallback, useMemo, useState } from "react";
import Link from "next/link";
import { ChatPanel } from "@/components/learn/ChatPanel";
import { Card } from "@/components/ui/card";
import { useFlag } from "@/lib/useFlag";
import type { ChatContext } from "@/components/learn/types";
import type { QAForensicsResponse } from "@/components/transcript/types";
import { QAExchangeCard } from "./QAExchangeCard";
import { QAJudgmentPrompt } from "./QAJudgmentPrompt";
import { QARevealPanel } from "./QARevealPanel";
import { QAForensicsWrapUp } from "./QAForensicsWrapUp";
import {
  evasionTypeLabel,
  JUDGMENT_LABELS,
  type Judgment,
  type QAForensicsExchange,
} from "./types";

interface QAForensicsClientProps {
  ticker: string;
  data: QAForensicsResponse;
}

const EMPTY_JUDGMENT: Judgment = { choice: null, text: "", revealed: false };

/** Stateful shell for the Q&A Forensics learning mode. Walks the user through
 *  each exchange one at a time, gating reveal behind a judgment commitment,
 *  then hands off to the existing Feynman chat seeded with the user's reasoning. */
export function QAForensicsClient({ ticker, data }: QAForensicsClientProps) {
  const chatEnabled = useFlag("chat_enabled", true);

  const [currentIndex, setCurrentIndex] = useState(0);
  const [judgments, setJudgments] = useState<Record<string, Judgment>>({});
  const [chatContext, setChatContext] = useState<ChatContext | null>(null);
  const [chatOpen, setChatOpen] = useState(false);

  const exchanges = data.exchanges;
  const total = data.total;
  const isComplete = total > 0 && currentIndex >= total;
  const currentExchange = !isComplete ? exchanges[currentIndex] : null;
  const currentJudgment = currentExchange
    ? judgments[currentExchange.id] ?? EMPTY_JUDGMENT
    : EMPTY_JUDGMENT;

  const updateJudgment = useCallback(
    (exchangeId: string, next: Judgment) => {
      setJudgments((prev) => ({ ...prev, [exchangeId]: next }));
    },
    [],
  );

  const handleReveal = useCallback(() => {
    if (!currentExchange) return;
    updateJudgment(currentExchange.id, { ...currentJudgment, revealed: true });
  }, [currentExchange, currentJudgment, updateJudgment]);

  const handleNext = useCallback(() => {
    // Close chat when moving on so the previous exchange's discussion doesn't
    // bleed into the next one. The `key` on <ChatPanel /> below resets internal
    // state on remount as a belt-and-suspenders.
    setChatOpen(false);
    setChatContext(null);
    setCurrentIndex((i) => i + 1);
  }, []);

  const handleRestart = useCallback(() => {
    setCurrentIndex(0);
    setJudgments({});
  }, []);

  const handleDiscuss = useCallback(() => {
    if (!currentExchange) return;
    setChatContext({
      type: "qa-forensics",
      text: buildSeedMessage(currentExchange, currentJudgment),
    });
    setChatOpen(true);
  }, [currentExchange, currentJudgment]);

  const handleCloseChat = useCallback(() => {
    setChatOpen(false);
  }, []);

  const wrapUp = useMemo(
    () =>
      isComplete ? (
        <QAForensicsWrapUp
          total={total}
          dominantEvasionType={data.dominant_evasion_type}
          ticker={ticker}
          onRestart={handleRestart}
        />
      ) : null,
    [isComplete, total, data.dominant_evasion_type, ticker, handleRestart],
  );

  if (total === 0) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-8">
        <Card className="space-y-3 px-6 py-6">
          <h2 className="text-lg font-semibold text-foreground">No forensics-ready exchanges</h2>
          <p className="text-sm text-muted-foreground">
            This call has no Q&amp;A exchanges meeting the defensiveness threshold yet.
            Either the executives answered analysts directly, or this call hasn&apos;t
            been re-ingested with the new evasion taxonomy.
          </p>
          <Link
            href={`/calls/${ticker}`}
            className="inline-flex w-fit text-sm text-primary hover:underline"
          >
            ← Back to transcript
          </Link>
        </Card>
      </div>
    );
  }

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
        <div className="flex-1 overflow-y-auto">
          <div className="mx-auto w-full max-w-3xl space-y-5 px-4 py-6">
            {currentExchange ? (
              <>
                <QAExchangeCard
                  exchange={currentExchange}
                  index={currentIndex}
                  total={total}
                />
                {currentJudgment.revealed ? (
                  <QARevealPanel
                    exchange={currentExchange}
                    judgment={currentJudgment}
                    onDiscuss={handleDiscuss}
                    onNext={handleNext}
                    isLast={currentIndex === total - 1}
                  />
                ) : (
                  <QAJudgmentPrompt
                    judgment={currentJudgment}
                    onChange={(next) => updateJudgment(currentExchange.id, next)}
                    onReveal={handleReveal}
                  />
                )}
              </>
            ) : (
              wrapUp
            )}
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
            <ChatPanel
              key={currentExchange?.id ?? "no-exchange"}
              ticker={ticker}
              context={chatContext}
              onClose={handleCloseChat}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}

function buildSeedMessage(
  exchange: QAForensicsExchange,
  judgment: Judgment,
): string {
  const choiceLabel = judgment.choice ? JUDGMENT_LABELS[judgment.choice] : "—";
  const typeLabel = evasionTypeLabel(exchange.evasion_type);
  const topic = exchange.question_topic ? ` about ${exchange.question_topic}` : "";

  const lines = [
    `I just read this Q&A exchange${topic}:`,
    "",
    `Q: ${exchange.question_text ?? "(question text not available)"}`,
    "",
    `A: ${exchange.answer_text ?? "(answer text not available)"}`,
    "",
    `My judgment: "${choiceLabel}" — ${judgment.text || "(no reasoning provided)"}`,
    "",
    `The system flagged this as: ${typeLabel}.`,
    "",
    `Help me understand the gap between what I noticed and what was actually happening here.`,
  ];
  return lines.join("\n");
}

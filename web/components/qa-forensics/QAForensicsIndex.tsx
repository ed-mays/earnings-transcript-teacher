"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { evasionScoreToLevel, getEvasionStyle } from "@/lib/signal-colors";
import type { QAForensicsExchange } from "@/components/transcript/types";
import { evasionTypeLabel } from "./types";

interface QAForensicsIndexProps {
  ticker: string;
  exchanges: QAForensicsExchange[];
  dominantEvasionType: string | null;
  discussedSet: Set<string>;
  onSelectExchange: (id: string) => void;
}

/** Index/menu view of all forensics-ready exchanges in a call. The user
 *  picks which exchange to study; click-order is up to them. Mirrors the
 *  CallList grid pattern from web/components/CallList.tsx. */
export function QAForensicsIndex({
  ticker,
  exchanges,
  dominantEvasionType,
  discussedSet,
  onSelectExchange,
}: QAForensicsIndexProps) {
  if (!exchanges.length) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-8">
        <Card className="space-y-3 px-6 py-6">
          <h2 className="text-lg font-semibold text-foreground">
            No forensics-ready exchanges
          </h2>
          <p className="text-sm text-muted-foreground">
            This call has no Q&amp;A exchanges meeting the defensiveness
            threshold yet. Either the executives answered analysts directly,
            or this call hasn&apos;t been re-ingested with the new evasion
            taxonomy.
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
    <div className="mx-auto w-full max-w-5xl px-4 py-6">
      <header className="mb-6">
        <h1 className="text-xl font-semibold text-foreground">
          Q&amp;A Forensics — <span className="uppercase">{ticker}</span>
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {exchanges.length} {exchanges.length === 1 ? "exchange" : "exchanges"} worth
          studying. Pick whichever interests you — there&apos;s no required order.
          {dominantEvasionType ? (
            <>
              {" "}Dominant pattern in this call:{" "}
              <span className="font-medium text-foreground">
                {evasionTypeLabel(dominantEvasionType)}
              </span>
              .
            </>
          ) : null}
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {exchanges.map((exchange) => (
          <ExchangeIndexCard
            key={exchange.id}
            exchange={exchange}
            discussed={discussedSet.has(exchange.id)}
            onClick={() => onSelectExchange(exchange.id)}
          />
        ))}
      </div>
    </div>
  );
}

interface ExchangeIndexCardProps {
  exchange: QAForensicsExchange;
  discussed: boolean;
  onClick: () => void;
}

function ExchangeIndexCard({ exchange, discussed, onClick }: ExchangeIndexCardProps) {
  const level = evasionScoreToLevel(exchange.defensiveness_score);
  const evasionStyle = getEvasionStyle(level);
  const analystLabel = exchange.analyst_name ?? "Analyst";
  const topicLabel = exchange.question_topic ?? "Q&A exchange";

  return (
    <button
      type="button"
      onClick={onClick}
      className="text-left transition-shadow hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded-xl"
    >
      <Card className="h-full cursor-pointer gap-2 p-5 shadow-sm">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <p className="text-sm font-semibold text-foreground">{analystLabel}</p>
            <p className="text-xs text-muted-foreground">on {topicLabel}</p>
          </div>
          {discussed ? (
            <span
              aria-label="Already discussed"
              className="shrink-0 text-xs font-medium text-muted-foreground"
            >
              ✓ Discussed
            </span>
          ) : null}
        </div>

        <div className="flex flex-wrap gap-1.5">
          <Badge
            className={`rounded-md whitespace-normal h-auto w-auto shrink ${evasionStyle.bg} ${evasionStyle.text}`}
          >
            Defensiveness {exchange.defensiveness_score}/10
          </Badge>
          {exchange.evasion_type && exchange.evasion_type !== "none" ? (
            <Badge variant="secondary" className="rounded-md whitespace-normal h-auto">
              {evasionTypeLabel(exchange.evasion_type)}
            </Badge>
          ) : null}
        </div>

        {exchange.analyst_concern ? (
          <p className="line-clamp-2 text-xs text-muted-foreground">
            {exchange.analyst_concern}
          </p>
        ) : null}
      </Card>
    </button>
  );
}

import { Card } from "@/components/ui/card";
import type { QAForensicsExchange } from "./types";

interface QAExchangeCardProps {
  exchange: QAForensicsExchange;
}

/** STAKES → QUESTION → ANSWER blocks. The exchange itself, no verdict shown.
 *  Used inside the Q&A Forensics detail view. The detail view supplies its own
 *  back-nav and verdict strip — this component is just the raw exchange. */
export function QAExchangeCard({ exchange }: QAExchangeCardProps) {
  const analystLabel = [exchange.analyst_name, exchange.question_topic]
    .filter(Boolean)
    .join(" · ");

  return (
    <Card className="space-y-5 px-5 py-5">
      <section aria-label="Stakes">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          Stakes
        </p>
        <p className="mt-1 text-sm text-foreground">
          {analystLabel ? <span className="font-medium">{analystLabel}.</span> : null}{" "}
          {exchange.analyst_concern}
        </p>
      </section>

      {exchange.question_text ? (
        <section aria-label="The question">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            The question
          </p>
          <blockquote className="mt-1 border-l-2 border-border pl-3 text-sm text-foreground">
            {exchange.question_text}
          </blockquote>
        </section>
      ) : null}

      {exchange.answer_text ? (
        <section aria-label="The answer">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            The answer
          </p>
          <blockquote className="mt-1 border-l-2 border-border pl-3 text-sm text-foreground">
            {exchange.answer_text}
          </blockquote>
        </section>
      ) : null}
    </Card>
  );
}

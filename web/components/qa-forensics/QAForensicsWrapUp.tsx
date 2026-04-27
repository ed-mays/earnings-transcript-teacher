"use client";

import Link from "next/link";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { evasionTypeLabel } from "./types";

interface QAForensicsWrapUpProps {
  total: number;
  dominantEvasionType: string | null;
  ticker: string;
  onRestart: () => void;
}

/** End-of-mode summary: count, dominant pattern (when known), and a transferable
 *  pattern-recognition cue for the next call the user reads. */
export function QAForensicsWrapUp({
  total,
  dominantEvasionType,
  ticker,
  onRestart,
}: QAForensicsWrapUpProps) {
  const dominantLabel = dominantEvasionType ? evasionTypeLabel(dominantEvasionType) : null;

  return (
    <Card className="space-y-5 px-6 py-6">
      <div>
        <p className="text-xs uppercase tracking-wide text-muted-foreground">
          Q&amp;A Forensics complete
        </p>
        <h2 className="mt-1 text-xl font-semibold text-foreground">
          You worked through {total} {total === 1 ? "exchange" : "exchanges"}.
        </h2>
      </div>

      {dominantLabel ? (
        <section className="space-y-1">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Dominant pattern
          </p>
          <p className="text-sm text-foreground">
            The most common evasion pattern in this call was{" "}
            <span className="font-semibold">{dominantLabel}</span>.
          </p>
        </section>
      ) : (
        <p className="text-sm text-muted-foreground">
          The exchanges in this call weren&apos;t classified into a clear dominant
          pattern. (Older calls may not have evasion type tags yet.)
        </p>
      )}

      <section className="space-y-1">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          For your next call
        </p>
        <p className="text-sm text-foreground">
          {dominantLabel
            ? `Watch for "${dominantLabel}" specifically. The pattern repeats across companies — once you can name it, you can spot it unaided.`
            : "Keep practicing the judgment hinge: read the question, read the answer, decide for yourself before reading any analysis."}
        </p>
      </section>

      <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
        <Button variant="outline" onClick={onRestart}>
          Restart this call
        </Button>
        <Link href={`/calls/${ticker}`} className={buttonVariants({ variant: "default" })}>
          Back to transcript
        </Link>
      </div>
    </Card>
  );
}

"use client";

import { MisconceptionCard } from "@/components/transcript/MisconceptionCard";
import type { MisconceptionItem } from "@/components/transcript/types";

interface SectionCheckpointProps {
  misconceptions: MisconceptionItem[];
  title?: string;
  subtitle?: string;
}

/** Checkpoint card rendered at the prepared→Q&A section boundary. Surfaces misconceptions. */
export function SectionCheckpoint({
  misconceptions,
  title = "Check your understanding",
  subtitle = "Before the Q&A begins, make sure these don't trip you up.",
}: SectionCheckpointProps) {
  if (misconceptions.length === 0) return null;

  return (
    <section className="my-6 rounded-xl border bg-muted/30 p-4">
      <header className="mb-3">
        <h3 className="text-base font-semibold text-foreground">{title}</h3>
        <p className="text-sm text-muted-foreground">{subtitle}</p>
      </header>
      <div className="space-y-2">
        {misconceptions.map((item, index) => (
          <MisconceptionCard key={index} item={item} />
        ))}
      </div>
    </section>
  );
}

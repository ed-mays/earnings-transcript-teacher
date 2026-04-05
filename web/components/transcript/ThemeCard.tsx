"use client";

/** Renders a topic cluster as a card with a label, narrative summary, and signals button. */

import { useRef, useState } from "react";
import { streamThemeSignals } from "@/lib/signals";
import { Card } from "@/components/ui/card";
import { SignalsSection } from "./SignalsSection";

interface ThemeCardProps {
  /** The theme label (topic name). */
  label: string;
  /** One-sentence narrative summary for this theme. */
  summary: string;
  /** Ticker symbol, required for the signals endpoint. */
  ticker: string;
}

export function ThemeCard({ label, summary, ticker }: ThemeCardProps) {
  const [signals, setSignals] = useState<string | null>(null);
  const [loadingSignals, setLoadingSignals] = useState(false);
  const [signalsError, setSignalsError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  async function handleSignalsClick() {
    if (signals) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoadingSignals(true);
    setSignalsError(null);
    let accumulated = "";

    await streamThemeSignals(
      ticker,
      { label, summary },
      {
        onToken(token) {
          accumulated += token;
          setSignals(accumulated);
        },
        onDone() {
          setLoadingSignals(false);
        },
        onError(message) {
          if (controller.signal.aborted) return;
          setSignalsError(message);
          setLoadingSignals(false);
        },
      },
      controller.signal
    );
  }

  return (
    <Card className="p-4 gap-2">
      <p className="text-sm font-semibold text-foreground">{label}</p>
      {summary && (
        <p className="text-sm text-muted-foreground leading-snug">{summary}</p>
      )}

      <SignalsSection
        signals={signals}
        loading={loadingSignals}
        error={signalsError}
        onFetch={handleSignalsClick}
      />
    </Card>
  );
}

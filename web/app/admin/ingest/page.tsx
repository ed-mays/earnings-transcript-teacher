"use client";

/** Admin page for triggering transcript ingestion. Client component (form state). */

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";

type Status = "idle" | "submitting" | "accepted" | "error";

export default function AdminIngestPage() {
  const [ticker, setTicker] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const dismissTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (dismissTimerRef.current) clearTimeout(dismissTimerRef.current);
    };
  }, []);

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!ticker.trim()) return;

    setStatus("submitting");
    setErrorMessage(null);

    try {
      const resp = await fetch("/api/admin/ingest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: ticker.trim().toUpperCase() }),
      });

      if (resp.status === 202) {
        setStatus("accepted");
        setTicker("");
        dismissTimerRef.current = setTimeout(() => setStatus("idle"), 4000);
        return;
      }

      const data = (await resp.json()) as { error?: string; detail?: string };

      if (resp.status === 403) {
        setErrorMessage("You do not have permission to trigger ingestion.");
      } else if (resp.status === 422) {
        setErrorMessage(data.detail ?? data.error ?? "Invalid ticker symbol.");
      } else {
        setErrorMessage(data.error ?? `Unexpected error (${resp.status}).`);
      }
      setStatus("error");
    } catch {
      setErrorMessage("Network error — could not reach the server.");
      setStatus("error");
    }
  }

  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-12">
      <div className="mb-6 flex gap-4 text-sm">
        <a href="/admin" className="text-primary hover:underline">
          Analytics
        </a>
        <a href="/admin/health" className="text-primary hover:underline">
          System Health
        </a>
      </div>
      <h1 className="mb-2 text-3xl font-semibold text-foreground">Admin — Ingest</h1>
      <p className="mb-8 text-muted-foreground">
        Dispatch a ticker to the ingestion pipeline. Returns immediately — processing runs
        asynchronously.
      </p>

      <Card className="max-w-sm">
        <CardContent>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label
              htmlFor="ticker"
              className="mb-1.5 block text-sm font-medium text-foreground"
            >
              Ticker symbol
            </label>
            <Input
              id="ticker"
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder="e.g. AAPL"
              disabled={status === "submitting"}
              className="font-mono uppercase placeholder:normal-case"
            />
          </div>

          <Button
            type="submit"
            disabled={status === "submitting" || !ticker.trim()}
            className="w-full"
          >
            {status === "submitting" ? "Submitting…" : "Ingest transcript"}
          </Button>
        </form>

        {status === "accepted" && (
          <p className="mt-4 text-sm text-success">
            Accepted — ingestion dispatched successfully.
          </p>
        )}
        {status === "error" && errorMessage && (
          <p className="mt-4 text-sm text-destructive">{errorMessage}</p>
        )}
        </CardContent>
      </Card>
    </div>
  );
}

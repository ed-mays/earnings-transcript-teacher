"use client";

/** Admin page for triggering transcript ingestion. Client component (form state). */

import { useState } from "react";

type Status = "idle" | "submitting" | "accepted" | "error";

export default function AdminIngestPage() {
  const [ticker, setTicker] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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
        <a href="/admin" className="text-blue-600 hover:underline">
          Analytics
        </a>
        <a href="/admin/health" className="text-blue-600 hover:underline">
          System Health
        </a>
      </div>
      <h1 className="mb-2 text-3xl font-semibold text-zinc-900">Admin — Ingest</h1>
      <p className="mb-8 text-zinc-500">
        Dispatch a ticker to the ingestion pipeline. Returns immediately — processing runs
        asynchronously.
      </p>

      <div className="max-w-sm rounded-lg border border-zinc-200 bg-white p-6">
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label
              htmlFor="ticker"
              className="mb-1.5 block text-sm font-medium text-zinc-700"
            >
              Ticker symbol
            </label>
            <input
              id="ticker"
              type="text"
              value={ticker}
              onChange={(e) => {
                setTicker(e.target.value);
                if (status !== "submitting") setStatus("idle");
              }}
              placeholder="e.g. AAPL"
              disabled={status === "submitting"}
              className="w-full rounded-md border border-zinc-300 px-3 py-2 font-mono text-sm uppercase text-zinc-900 placeholder:normal-case placeholder:text-zinc-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-zinc-50 disabled:text-zinc-400"
            />
          </div>

          <button
            type="submit"
            disabled={status === "submitting" || !ticker.trim()}
            className="rounded-md bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-700 disabled:cursor-not-allowed disabled:bg-zinc-300"
          >
            {status === "submitting" ? "Submitting…" : "Ingest transcript"}
          </button>
        </form>

        {status === "accepted" && (
          <p className="mt-4 text-sm text-green-700">
            Accepted — ingestion dispatched successfully.
          </p>
        )}
        {status === "error" && errorMessage && (
          <p className="mt-4 text-sm text-red-600">{errorMessage}</p>
        )}
      </div>
    </div>
  );
}

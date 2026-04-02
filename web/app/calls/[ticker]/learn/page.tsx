"use client";

import { use, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ChatThread } from "@/components/chat/ChatThread";
import { ChatInput } from "@/components/chat/ChatInput";
import { streamChat } from "@/lib/chat";
import { api } from "@/lib/api";
import { buildSuggestions } from "@/lib/suggestions";
import type { ChatMessage } from "@/lib/chat";
import type { CallDetail } from "@/components/transcript/types";

/** Feynman-style learning chat for a given ticker's transcript. */
export default function LearnPage({
  params,
  searchParams,
}: {
  params: Promise<{ ticker: string }>;
  searchParams: Promise<{ topic?: string }>;
}) {
  const { ticker } = use(params);
  const { topic } = use(searchParams);
  const upperTicker = ticker.toUpperCase();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(true);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Cancel any in-flight stream when the component unmounts (navigation away)
  useEffect(() => {
    return () => { abortControllerRef.current?.abort(); };
  }, []);

  useEffect(() => {
    api
      .get<CallDetail>(`/api/calls/${ticker}`)
      .then((detail) => setSuggestions(buildSuggestions(detail.themes, detail.keywords)))
      .catch(() => {
        // Silent degradation — suggestions are a progressive enhancement
      })
      .finally(() => setLoadingSuggestions(false));
  }, [ticker]);

  async function handleSend(message: string) {
    abortControllerRef.current?.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setError(null);
    setIsStreaming(true);
    setStreamingContent("");
    setMessages((prev) => [...prev, { role: "user", content: message }]);

    let accumulated = "";

    await streamChat(ticker, message, sessionId, {
      onToken(token) {
        accumulated += token;
        setStreamingContent(accumulated);
      },
      onDone(newSessionId) {
        setSessionId(newSessionId);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: accumulated },
        ]);
        setStreamingContent("");
        setIsStreaming(false);
      },
      onError(msg) {
        if (controller.signal.aborted) return;
        setError(msg);
        setStreamingContent("");
        setIsStreaming(false);
      },
    }, controller.signal);
  }

  function handleNewSession() {
    setMessages([]);
    setStreamingContent("");
    setSessionId(null);
    setError(null);
  }

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col px-6 py-8" style={{ height: "calc(100vh - 64px)" }}>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">
              Learn:{" "}
              <span className="uppercase">{upperTicker}</span>
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Explain what you&apos;ve learned in your own words — the AI will probe your understanding
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleNewSession}
            disabled={isStreaming}
            className="text-sm text-muted-foreground underline-offset-2 hover:text-foreground hover:underline disabled:opacity-40"
          >
            New session
          </button>
          <Link
            href={`/calls/${upperTicker}`}
            className="text-sm text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
          >
            View transcript
          </Link>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-4 flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          <span className="flex-1">{error}</span>
          <button
            onClick={() => setError(null)}
            aria-label="Dismiss error"
            className="shrink-0 text-red-400 hover:text-red-600"
          >
            ✕
          </button>
        </div>
      )}

      {/* Chat thread */}
      <ChatThread
        messages={messages}
        streamingContent={streamingContent}
        suggestions={suggestions}
        loadingSuggestions={loadingSuggestions}
        onSuggestionClick={handleSend}
      />

      {/* Input */}
      <div className="mt-4">
        <ChatInput onSend={handleSend} isStreaming={isStreaming} initialValue={topic ?? ""} />
      </div>
    </div>
  );
}

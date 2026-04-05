"use client";

import { use, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Button, buttonVariants } from "@/components/ui/button";
import { ChatThread } from "@/components/chat/ChatThread";
import { ChatInput } from "@/components/chat/ChatInput";
import { streamChat } from "@/lib/chat";
import { api } from "@/lib/api";
import { buildSuggestions } from "@/lib/suggestions";
import type { ChatMessage } from "@/lib/chat";
import type { TopicsResponse, KeywordsResponse } from "@/components/transcript/types";

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
    Promise.all([
      api.get<TopicsResponse>(`/api/calls/${ticker}/topics`),
      api.get<KeywordsResponse>(`/api/calls/${ticker}/keywords`),
    ])
      .then(([topics, kw]) => setSuggestions(buildSuggestions(topics.themes, kw.keywords)))
      .catch(() => {
        // Silent degradation — suggestions are a progressive enhancement
      })
      .finally(() => setLoadingSuggestions(false));
  }, [ticker]);

  function handleAbort() {
    abortControllerRef.current?.abort();
    setStreamingContent("");
    setIsStreaming(false);
  }

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
    <div className="mx-auto flex w-full max-w-3xl flex-1 min-h-0 flex-col px-6 py-8">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-baseline gap-3">
          <div>
            <h1 className="text-3xl font-semibold text-foreground">
              Learn:{" "}
              <span className="uppercase">{upperTicker}</span>
            </h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Explain what you&apos;ve learned in your own words — the AI will probe your understanding
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleNewSession}
            disabled={isStreaming}
          >
            New session
          </Button>
          <Link
            href={`/calls/${upperTicker}`}
            className={buttonVariants({ variant: "outline", size: "sm" })}
          >
            View transcript
          </Link>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-4 flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          <span className="flex-1">{error}</span>
          <button
            onClick={() => setError(null)}
            aria-label="Dismiss error"
            className="shrink-0 text-destructive/60 hover:text-destructive"
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
        <ChatInput onSend={handleSend} onAbort={handleAbort} isStreaming={isStreaming} initialValue={topic ?? ""} />
      </div>
    </div>
  );
}

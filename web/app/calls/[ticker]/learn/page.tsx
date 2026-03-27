"use client";

import { use, useEffect, useState } from "react";
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
}: {
  params: Promise<{ ticker: string }>;
}) {
  const { ticker } = use(params);
  const upperTicker = ticker.toUpperCase();

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [streamingContent, setStreamingContent] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(true);

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
        setError(msg);
        setStreamingContent("");
        setIsStreaming(false);
      },
    });
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
          <h1 className="text-2xl font-bold tracking-tight text-zinc-900">
            Learn:{" "}
            <span className="uppercase">{upperTicker}</span>
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleNewSession}
            disabled={isStreaming}
            className="text-sm text-zinc-500 underline-offset-2 hover:text-zinc-700 hover:underline disabled:opacity-40"
          >
            New session
          </button>
          <Link
            href={`/calls/${upperTicker}`}
            className="text-sm text-zinc-500 underline-offset-2 hover:text-zinc-700 hover:underline"
          >
            ← Back
          </Link>
        </div>
      </div>

      {/* Error banner */}
      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
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
        <ChatInput onSend={handleSend} isStreaming={isStreaming} />
      </div>
    </div>
  );
}

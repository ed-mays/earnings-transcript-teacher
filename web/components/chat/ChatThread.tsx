"use client";

import { useEffect, useRef } from "react";
import type { ChatMessage } from "@/lib/chat";

interface ChatThreadProps {
  messages: ChatMessage[];
  streamingContent: string;
}

/** Renders the full conversation history plus any in-progress streamed assistant response. */
export function ChatThread({ messages, streamingContent }: ChatThreadProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  if (messages.length === 0 && !streamingContent) {
    return (
      <div className="flex flex-1 items-center justify-center text-sm text-zinc-400">
        Ask a question about this earnings call to get started.
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-1 py-2">
      {messages.map((msg, i) => (
        <MessageBubble key={i} role={msg.role} content={msg.content} />
      ))}
      {streamingContent && (
        <MessageBubble role="assistant" content={streamingContent} streaming />
      )}
      <div ref={bottomRef} />
    </div>
  );
}

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
}

function MessageBubble({ role, content, streaming = false }: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? "bg-zinc-900 text-white"
            : "bg-zinc-100 text-zinc-900"
        }`}
      >
        {content}
        {streaming && (
          <span className="ml-1 inline-block h-3 w-0.5 animate-pulse bg-current" />
        )}
      </div>
    </div>
  );
}
